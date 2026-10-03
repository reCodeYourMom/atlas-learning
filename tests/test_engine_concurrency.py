"""Tests revue concurrence & robustesse du moteur Elo (2026-07-07).

Couvre les 5 correctifs :
  1. verrous ligne dans on_response (test de concurrence réelle, Postgres uniquement) ;
  2. idempotence bout-en-bout du double-submit (uuid5 déterministe + contrainte
     unique (session_id, item_id) + conversion IntegrityError → 409) ;
  3. clamp des Elo dans [0, 4000] (update direct ET propagation) ;
  4. burn-in : difficulté item gelée au prior sous ITEM_BURN_IN réponses ;
  5. job scripts/run_quarantine.py : référence = ability MOYENNE réelle des
     répondants (pas la constante 1200), item sain intact, AuditLog alimenté.
"""
import os
import sys
import threading
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import src.api.session_service as session_service
from scripts.run_quarantine import run_quarantine
from src.api.session_service import (
    RESPONSE_ID_NAMESPACE,
    AlreadyAnswered,
    start_session,
    submit_response,
)
from src.db import make_engine
from src.engine.elo import ELO_MAX, ELO_MIN, ITEM_BURN_IN, Neighbor, propagate, update_elo
from src.engine.service import on_response
from src.items.quarantine import DEFAULT_MIN_RESPONSES
from src.models.audit import AuditLog
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, EdgeType, ItemStatus, Subject, WeightSource,
)
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility

CONTENT = {"stem": "q", "options": ["1/4", "3/4"], "answer": "3/4"}

# Test de concurrence réelle : nécessite un Postgres dédié (FOR UPDATE ignoré par SQLite).
PG_URL = os.environ.get("ATLAS_TEST_PG_URL")


def _setup(item_status=ItemStatus.ACTIVE):
    """École + élève + compétences A→B + 1 item sur B (statut paramétrable)."""
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = Session(engine)
    school = School(name="Test School")
    s.add(school); s.flush()
    student = Student(school_id=school.id)
    s.add(student)
    a = Competency(code="MATH.G4.NF.A", label_en="a", label_ar="ا", subject=Subject.MATH,
                   grade=4, difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    b = Competency(code="MATH.G4.NF.B", label_en="b", label_ar="ب", subject=Subject.MATH,
                   grade=4, difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add_all([a, b]); s.flush()
    s.add(CompetencyPrerequisite(source_id=a.id, target_id=b.id, edge_type=EdgeType.HARD,
                                 correlation_strength=0.8, weight_source=WeightSource.EXPERT))
    item = Item(competency_id=b.id, content_en=dict(CONTENT), content_ar=None,
                answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0,
                difficulty_elo=1500.0, status=item_status)
    s.add(item); s.commit()
    return s, school, student, a, b, item


# ---------- 2. idempotence bout-en-bout du double-submit ----------

def test_response_id_deterministe():
    # même (session, item) → même response_id, quel que soit le moment de l'appel
    sid, iid = uuid.uuid4(), uuid.uuid4()
    assert (uuid.uuid5(RESPONSE_ID_NAMESPACE, f"{sid}:{iid}")
            == uuid.uuid5(RESPONSE_ID_NAMESPACE, f"{sid}:{iid}"))


def test_double_submit_un_seul_effet_et_409():
    # 2× submit_response sur le même item → 1 seul effet Elo + AlreadyAnswered (409 API)
    s, school, student, a, b, item = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)
    submit_response(s, sess, item_id=item.id, is_correct=True)
    ab1 = s.get(StudentCompetencyAbility, (student.id, b.id)).ability_elo
    try:
        submit_response(s, sess, item_id=item.id, is_correct=True)
        assert False, "double submit aurait dû lever AlreadyAnswered"
    except AlreadyAnswered:
        pass
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 1
    ab2 = s.get(StudentCompetencyAbility, (student.id, b.id))
    assert ab2.ability_elo == ab1 and ab2.n_direct == 1          # effet appliqué UNE fois


def test_rejeu_garde_contournee_reste_idempotent():
    # Même si la garde _seen_item_ids est contournée (course), le response_id
    # déterministe fait que le moteur reconnaît le rejeu : AUCUN second effet.
    # Depuis la revue 2026-07-08, ce rejeu répond en plus 409 UNIFORME
    # (AlreadyAnswered, comme le rejeu tardif) — sémantique déterministe,
    # zéro entrée AuditLog dupliquée (cf. session_service.submit_response).
    s, school, student, a, b, item = _setup()
    # Second item sur la même compétence : sans lui, la banque est épuisée après la
    # première réponse et la session se clôt légitimement (« no_items ») — le refus
    # « session terminée » masquerait alors le rejeu qu'on veut précisément observer.
    s.add(Item(competency_id=b.id, answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0,
               status=ItemStatus.ACTIVE, content_en=CONTENT))
    s.commit()
    sess = start_session(s, student_id=student.id, school_id=school.id)
    submit_response(s, sess, item_id=item.id, is_correct=True)
    ab1 = s.get(StudentCompetencyAbility, (student.id, b.id)).ability_elo
    audits_before = s.execute(select(func.count()).select_from(AuditLog)
                              .where(AuditLog.action == "response.submit")).scalar_one()
    orig = session_service._seen_item_ids
    session_service._seen_item_ids = lambda *_a, **_k: set()
    try:
        try:
            submit_response(s, sess, item_id=item.id, is_correct=True)
            assert False, "rejeu sous la garde aurait dû lever AlreadyAnswered (409 uniforme)"
        except AlreadyAnswered:
            pass                                                     # no-op moteur + 409
    finally:
        session_service._seen_item_ids = orig
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 1
    assert s.get(StudentCompetencyAbility, (student.id, b.id)).ability_elo == ab1
    audits_after = s.execute(select(func.count()).select_from(AuditLog)
                             .where(AuditLog.action == "response.submit")).scalar_one()
    assert audits_after == audits_before                             # zéro audit dupliqué


def test_integrity_error_convertie_en_already_answered():
    # Course perdue au flush (doublon simultané) : la tx gagnante a COMMITÉ la Response
    # (response_id déterministe) → IntegrityError chez le perdant → AlreadyAnswered (409).
    s, school, student, a, b, item = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)
    # simule le commit de la transaction gagnante (même response_id déterministe)
    rid = uuid.uuid5(RESPONSE_ID_NAMESPACE, f"{sess.id}:{item.id}")
    s.add(Response(id=rid, session_id=sess.id, school_id=school.id, student_id=student.id,
                   item_id=item.id, competency_id=b.id, is_correct=True))
    s.commit()

    def boom(*args, **kwargs):
        raise IntegrityError("INSERT INTO response ...", {}, Exception("doublon"))

    orig = session_service.on_response
    session_service.on_response = boom
    try:
        try:
            submit_response(s, sess, item_id=item.id, is_correct=True)
            assert False, "aurait dû lever AlreadyAnswered"
        except AlreadyAnswered:
            pass
    finally:
        session_service.on_response = orig
    # la réponse de la tx gagnante est intacte, aucune autre créée
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 1


def test_integrity_error_creation_ability_concurrente_rejouee_pas_de_409():
    # Revue adversariale 2026-07-07 : une IntegrityError qui ne vient PAS d'un doublon
    # de Response (création concurrente d'une ligne ability, PK composite) NE doit PAS
    # devenir un 409 « déjà répondu » : la réponse serait perdue en silence. L'appelant
    # REJOUE on_response une fois — la ligne commitée par la tx adverse existe alors.
    s, school, student, a, b, item = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)

    calls = {"n": 0}
    orig = session_service.on_response

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # simule la PK composite (student_id, competency_id) violée par la tx adverse
            raise IntegrityError("INSERT INTO student_competency_ability ...", {},
                                 Exception("pk composite"))
        return orig(*args, **kwargs)

    session_service.on_response = flaky
    try:
        out = submit_response(s, sess, item_id=item.id, is_correct=True)  # ne lève PAS
    finally:
        session_service.on_response = orig
    assert calls["n"] == 2                                        # rejoué exactement une fois
    assert isinstance(out, dict)
    # la réponse est bien ENREGISTRÉE (elle était perdue avec l'ancien 409)
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 1
    ab = s.get(StudentCompetencyAbility, (student.id, b.id))
    assert ab is not None and ab.n_direct == 1                    # effet Elo appliqué


def test_integrity_error_persistante_sans_response_remonte():
    # Si le rejeu échoue AUSSI et qu'aucune Response n'existe, on ne ment pas avec un
    # 409 : l'IntegrityError remonte (500 honnête, le client peut rejouer).
    s, school, student, a, b, item = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)

    def boom(*args, **kwargs):
        raise IntegrityError("INSERT INTO student_competency_ability ...", {},
                             Exception("pk composite"))

    orig = session_service.on_response
    session_service.on_response = boom
    try:
        with pytest.raises(IntegrityError):
            submit_response(s, sess, item_id=item.id, is_correct=True)
    finally:
        session_service.on_response = orig
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 0


def test_contrainte_unique_session_item_en_base():
    # la contrainte uq_response_session_item rejette le doublon (session_id, item_id)…
    s, school, student, a, b, item = _setup()
    sid = uuid.uuid4()
    common = dict(school_id=school.id, student_id=student.id, item_id=item.id,
                  competency_id=b.id, is_correct=True)
    s.add(Response(session_id=sid, **common)); s.commit()
    s.add(Response(session_id=sid, **common))
    try:
        s.commit()
        assert False, "doublon (session_id, item_id) aurait dû être rejeté"
    except IntegrityError:
        s.rollback()
    # … mais laisse passer les NULL multiples (réponses hors session : seeds, moteur direct)
    s.add(Response(session_id=None, **common))
    s.add(Response(session_id=None, **common))
    s.commit()
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 3


# ---------- 3. clamp des Elo [0, 4000] ----------

def test_clamp_ability_saturation_haute_et_basse():
    na, _ = update_elo(3995.0, 3995.0, True, 0, ITEM_BURN_IN)    # +16 brut → 4011
    assert na == ELO_MAX
    na, _ = update_elo(5.0, 5.0, False, 0, ITEM_BURN_IN)         # -16 brut → -11
    assert na == ELO_MIN


def test_clamp_difficulte_item():
    _, ni = update_elo(5.0, 5.0, True, 0, ITEM_BURN_IN)          # item baisse sous 0 brut
    assert ni == ELO_MIN
    _, ni = update_elo(3995.0, 3995.0, False, 0, ITEM_BURN_IN)   # item monte au-dessus de 4000 brut
    assert ni == ELO_MAX


def test_clamp_propagation():
    nb = Neighbor("B", ability=3999.0, confidence=0.0, correlation_strength=1.0, edge_type="SOFT")
    [res] = propagate(100.0, source_confidence=0.9, neighbors=[nb])  # +40 brut → 4039
    assert res.new_ability == ELO_MAX
    nb = Neighbor("B", ability=1.0, confidence=0.0, correlation_strength=1.0, edge_type="SOFT")
    [res] = propagate(-100.0, source_confidence=0.9, neighbors=[nb])
    assert res.new_ability == ELO_MIN


# ---------- 4. burn-in de la difficulté item ----------

def test_burn_in_difficulte_gelee_avant_seuil():
    for n in range(ITEM_BURN_IN):
        _, ni = update_elo(1500.0, 1500.0, True, 0, n)
        assert ni == 1500.0                                       # gelée au prior
    na, _ = update_elo(1500.0, 1500.0, True, 0, 0)
    assert na > 1500.0                                            # l'ability élève bouge, elle


def test_burn_in_difficulte_mobile_apres_seuil():
    _, ni = update_elo(1500.0, 1500.0, True, 0, ITEM_BURN_IN)
    assert ni < 1500.0


def test_burn_in_bout_en_bout_via_on_response():
    s, school, student, a, b, item = _setup()
    on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id)
    assert s.get(Item, item.id).difficulty_elo == 1500.0          # burn-in : immobile
    assert s.get(Item, item.id).n_responses == 1
    item.n_responses = ITEM_BURN_IN
    s.commit()
    on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id)
    assert s.get(Item, item.id).difficulty_elo < 1500.0           # sorti du burn-in : mobile


# ---------- 5. job run_quarantine ----------

def _add_traffic(s, school, item, *, n_students, ability, success_rate):
    """n élèves répondent 1× à l'item : abilities réelles + réponses (hors session)."""
    n_ok = round(n_students * success_rate)
    for i in range(n_students):
        st = Student(school_id=school.id)
        s.add(st); s.flush()
        s.add(StudentCompetencyAbility(student_id=st.id, competency_id=item.competency_id,
                                       school_id=school.id, ability_elo=ability,
                                       n_direct=5, confidence=0.5))
        s.add(Response(school_id=school.id, student_id=st.id, item_id=item.id,
                       competency_id=item.competency_id, is_correct=(i < n_ok)))
    s.commit()


def test_run_quarantine_derive_quarantaine_et_sain_intact():
    s, school, student, a, b, item = _setup()
    # item DÉRIVANT : annoncé très dur (2000) mais 95 % de réussite chez des élèves
    # moyens (ability réelle 1200) → attendu ≈ 0.01, écart >> 0.40.
    item.difficulty_elo = 2000.0
    _add_traffic(s, school, item, n_students=DEFAULT_MIN_RESPONSES + 10,
                 ability=1200.0, success_rate=0.95)
    # item SAIN : dur (2000) répondu par des élèves FORTS (ability réelle 2000) à 50 % —
    # cohérent avec SA cohorte ; la constante 1200 l'aurait quarantainé à tort
    # (attendu ≈ 0.01 vs observé 0.50) → prouve que la référence est la moyenne réelle.
    sain = Item(competency_id=a.id, content_en=dict(CONTENT), content_ar=None,
                answer_format=AnswerFormat.MCQ, difficulty_prior=2000.0,
                difficulty_elo=2000.0, status=ItemStatus.ACTIVE)
    s.add(sain); s.commit()
    _add_traffic(s, school, sain, n_students=DEFAULT_MIN_RESPONSES + 10,
                 ability=2000.0, success_rate=0.50)

    report = run_quarantine(s, execute=True)
    assert report["dry_run"] is False and report["scanned"] == 2
    assert [e["item_id"] for e in report["quarantined"]] == [str(item.id)]
    assert s.get(Item, item.id).status == ItemStatus.QUARANTINED
    assert s.get(Item, sain.id).status == ItemStatus.ACTIVE       # sain : intact
    # référence utilisée = ability moyenne réelle des répondants, pas 1200
    assert abs(report["quarantined"][0]["reference_ability"] - 1200.0) < 1.0
    # journalisé dans AuditLog
    logs = s.execute(select(AuditLog).where(AuditLog.action == "item.quarantine")).scalars().all()
    assert len(logs) == 1 and logs[0].resource_id == item.id


def test_run_quarantine_dry_run_ne_change_rien():
    s, school, student, a, b, item = _setup()
    item.difficulty_elo = 2000.0
    _add_traffic(s, school, item, n_students=DEFAULT_MIN_RESPONSES + 10,
                 ability=1200.0, success_rate=0.95)
    report = run_quarantine(s)                                    # dry-run par défaut
    assert report["dry_run"] is True
    assert [e["item_id"] for e in report["quarantined"]] == [str(item.id)]
    assert s.get(Item, item.id).status == ItemStatus.ACTIVE       # rien changé
    assert s.execute(select(func.count()).select_from(AuditLog)
                     .where(AuditLog.action == "item.quarantine")).scalar_one() == 0


def test_run_quarantine_revalide_le_statut_sous_verrou():
    # TOCTOU (revue 2026-07-08) : un reviewer humain promeut/rejette l'item ENTRE le scan
    # (active_pool) et l'application. Le changement est simulé en SQL BRUT — il contourne
    # l'identity map, exactement comme une transaction concurrente : l'instance scannée
    # reste `active` en mémoire. Sans la re-lecture SOUS VERROU (SELECT ... FOR UPDATE
    # + populate_existing), apply_quarantine testait cet état périmé et écrasait la
    # décision du reviewer (last-write-wins sur status + dict provenance).
    import scripts.run_quarantine as rq

    s, school, student, a, b, item = _setup()
    item.difficulty_elo = 2000.0
    _add_traffic(s, school, item, n_students=DEFAULT_MIN_RESPONSES + 10,
                 ability=1200.0, success_rate=0.95)

    orig = rq._item_stats

    def stats_puis_course(sess, it):  # course injectée entre le scan et l'application
        out = orig(sess, it)
        sess.connection().execute(
            text("UPDATE item SET status = 'human_reviewed' WHERE id = :i"),
            {"i": it.id.hex},
        )
        return out

    rq._item_stats = stats_puis_course
    try:
        report = rq.run_quarantine(s, execute=True)
    finally:
        rq._item_stats = orig

    assert report["quarantined"] == []                            # rien appliqué
    s.expire_all()
    # la décision du reviewer concurrent est INTACTE (pas de last-write-wins)
    assert s.get(Item, item.id).status == ItemStatus.HUMAN_REVIEWED
    assert s.execute(select(func.count()).select_from(AuditLog)
                     .where(AuditLog.action == "item.quarantine")).scalar_one() == 0


# ---------- 1bis. ordre DÉTERMINISTE de création des lignes ability manquantes ----------

def test_creation_lignes_ability_manquantes_en_ordre_trie():
    # Revue adversariale 2026-07-07 : les INSERTs des lignes ability manquantes doivent
    # suivre le MÊME ordre trié que les verrous FOR UPDATE — l'ancien ordre (source
    # d'abord, puis voisins dans l'ordre DB des edges) créait une attente croisée sur
    # la PK composite entre deux transactions Postgres → deadlock (500).
    from sqlalchemy import event

    s, school, student, a, b, item = _setup()
    # 2 voisins supplémentaires de B pour rendre l'ordre discriminant (4 lignes créées)
    extra = []
    for code in ("MATH.G4.NF.C", "MATH.G4.NF.D"):
        comp = Competency(code=code, label_en=code, label_ar="ج", subject=Subject.MATH,
                          grade=4, difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
        s.add(comp); s.flush()
        s.add(CompetencyPrerequisite(source_id=comp.id, target_id=b.id,
                                     edge_type=EdgeType.SOFT, correlation_strength=0.5,
                                     weight_source=WeightSource.EXPERT))
        extra.append(comp)
    s.commit()

    created_order = []

    @event.listens_for(s, "after_flush")
    def _capture(session, _ctx):
        for obj in session.new:
            if isinstance(obj, StudentCompetencyAbility):
                created_order.append(obj.competency_id)

    try:
        on_response(s, student_id=student.id, item_id=item.id, is_correct=True,
                    school_id=school.id)
    finally:
        event.remove(s, "after_flush", _capture)

    expected = sorted([a.id, b.id, extra[0].id, extra[1].id], key=str)
    assert created_order == expected      # créées une par une, en ordre trié (= verrous)


# ---------- 1. concurrence réelle (Postgres uniquement) ----------

@pytest.mark.skipif(
    not PG_URL,
    reason="concurrence réelle : FOR UPDATE ignoré par SQLite — poser ATLAS_TEST_PG_URL "
           "(Postgres dédié) pour l'exécuter",
)
def test_concurrence_reelle_pas_de_perte_update_pg():
    """N threads répondent SIMULTANÉMENT au même item : sans verrou ligne, des updates
    se perdent (last-write-wins) ; avec FOR UPDATE, n_direct et n_responses == N."""
    n_threads = 8
    engine = make_engine(PG_URL)
    Base.metadata.create_all(engine)
    with Session(engine) as seed:
        school = School(name="PG concurrence")
        seed.add(school); seed.flush()
        student = Student(school_id=school.id)
        seed.add(student)
        comp = Competency(code=f"PG.{uuid.uuid4().hex[:8]}", label_en="c", label_ar="ج",
                          subject=Subject.MATH, grade=4, difficulty_prior=1500.0,
                          status=CompetencyStatus.ACTIVE)
        seed.add(comp); seed.flush()
        item = Item(competency_id=comp.id, content_en=dict(CONTENT), content_ar=None,
                    answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0,
                    difficulty_elo=1500.0, status=ItemStatus.ACTIVE)
        seed.add(item)
        # pré-crée la ligne ability : les threads ne font QUE du read-modify-write
        # (l'insert concurrent de la 1re réponse est couvert par la PK composite).
        seed.add(StudentCompetencyAbility(student_id=student.id, competency_id=comp.id,
                                          school_id=school.id, ability_elo=1500.0,
                                          n_direct=0, confidence=0.0))
        seed.commit()
        ids = dict(school=school.id, student=student.id, comp=comp.id, item=item.id)

    errors = []
    barrier = threading.Barrier(n_threads)

    def worker(i: int) -> None:
        try:
            with Session(engine) as s:
                barrier.wait()
                on_response(s, student_id=ids["student"], item_id=ids["item"],
                            is_correct=(i % 2 == 0), school_id=ids["school"])
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    with Session(engine) as s:
        assert s.get(Item, ids["item"]).n_responses == n_threads
        ab = s.get(StudentCompetencyAbility, (ids["student"], ids["comp"]))
        assert ab.n_direct == n_threads
        assert s.execute(select(func.count()).select_from(Response)
                         .where(Response.item_id == ids["item"])).scalar_one() == n_threads


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
