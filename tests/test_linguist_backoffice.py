"""Back-office LINGUISTE (persona dédié, Mouvement 02).

Couvre le nouveau rôle RBAC `linguist` (staff Atlas GLOBAL, non tenant-scopé), son
authentification par lien magique single-use (anti-préchargement : GET ne consomme pas,
POST consomme, rejeu rejeté — même contrat que parent/super-admin), et l'API back-office
`/linguist/*` (file de validation AR, détail EN/AR, correction, validation, signalement).

La banque d'items ne contient AUCUNE PII élève (c'est du contenu) : l'audience est le staff.
"""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

import src.api.app as appmod
from src.db import make_engine
from src.models import competency as _c, item as _i, measurement as _m, org as _o, session as _se  # noqa: F401,E501
from src.models.audit import AuditLog
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, Role, Subject,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.org import AppUser, Membership, Organization
from src.models.token import ConsumedToken
from src.rbac.auth import make_token

FAKE_SENT = []


class _FakeSender:
    def send(self, *, to, subject, html, text):
        FAKE_SENT.append({"to": to, "subject": subject, "html": html, "text": text})


# content EN de référence (fidélité math = options/réponse identiques).
_EN = {"stem": "What is 1/2 + 1/4?", "options": ["3/4", "2/6"], "answer": "3/4"}
_AR_GOOD = {"stem": "ما هو ١/٢ + ١/٤؟", "options": ["3/4", "2/6"], "answer": "3/4"}
_AR_BROKEN = {"stem": "ما هو ١/٢ + ١/٤؟", "options": ["9/9", "2/6"], "answer": "9/9"}


def _make_item(comp_id, *, content_ar=None, ar_validated=False,
               status=ItemStatus.HUMAN_REVIEWED, provenance=None):
    it = Item(competency_id=comp_id, answer_format=AnswerFormat.MCQ, difficulty_prior=1400.0,
              status=status, content_en=dict(_EN),
              provenance=dict(provenance or {}))
    if content_ar is not None:
        it.content_ar = dict(content_ar)
    it.ar_validated = ar_validated
    return it


def _client():
    FAKE_SENT.clear()
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    engine = make_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    with Session(bind=engine) as s:
        org = Organization(name="Org"); s.add(org); s.flush()
        comp = Competency(code="M.A", label_en="Add fractions", label_ar="جمع الكسور",
                          subject=Subject.MATH, grade=4, difficulty_prior=1500.0,
                          status=CompetencyStatus.ACTIVE)
        s.add(comp); s.flush()

        # 3 items non validés : un flaggé math_broken, un « propre » avec AR, un sans AR ;
        # + 1 item déjà validé (doit être ABSENT de la file).
        broken = _make_item(comp.id, content_ar=_AR_BROKEN,
                            provenance={"ar_math_broken": True})
        clean = _make_item(comp.id, content_ar=_AR_GOOD)
        no_ar = _make_item(comp.id)
        validated = _make_item(comp.id, content_ar=_AR_GOOD, ar_validated=True,
                              status=ItemStatus.ACTIVE)
        s.add_all([broken, clean, no_ar, validated]); s.flush()

        ling = AppUser(email="ling@atlas.io"); s.add(ling); s.flush()
        s.add(Membership(user_id=ling.id, role=Role.LINGUIST))  # staff global, pas de school_id
        teacher = AppUser(email="teach@school.edu"); s.add(teacher); s.flush()
        s.add(Membership(user_id=teacher.id, role=Role.TEACHER, organization_id=org.id))
        ops = AppUser(email="ops@atlas.io"); s.add(ops); s.flush()
        s.add(Membership(user_id=ops.id, role=Role.SUPER_ADMIN))
        s.commit()
        ids = dict(ling=ling.id, teacher=teacher.id, ops=ops.id,
                   broken=broken.id, clean=clean.id, no_ar=no_ar.id, validated=validated.id)

    def _get_db():
        sess = Session(bind=engine)
        try:
            yield sess
        finally:
            sess.close()

    appmod.app.dependency_overrides[appmod.get_db] = _get_db
    appmod.app.dependency_overrides[appmod.get_email_sender] = lambda: _FakeSender()
    return TestClient(appmod.app), engine, ids


def _clear():
    appmod.app.dependency_overrides.clear()


def _auth(uid):
    return {"Authorization": f"Bearer {make_token(str(uid))}"}


def _link_token(pattern):
    return re.search(pattern, FAKE_SENT[-1]["html"]).group(1)


def _consumed_count(engine):
    with Session(bind=engine) as s:
        return len(s.execute(select(ConsumedToken)).scalars().all())


def _audit_actions(engine):
    with Session(bind=engine) as s:
        return [a.action for a in s.execute(select(AuditLog)).scalars().all()]


# ---------- RBAC : linguist / super_admin OUI ; teacher 403 ; sans token 401 ----------

def test_linguist_can_access_queue():
    client, _, ids = _client()
    r = client.get("/linguist/queue", headers=_auth(ids["ling"]))
    assert r.status_code == 200, r.text
    _clear()


def test_super_admin_can_access_queue():
    client, _, ids = _client()
    assert client.get("/linguist/queue", headers=_auth(ids["ops"])).status_code == 200
    _clear()


def test_teacher_forbidden():
    client, _, ids = _client()
    assert client.get("/linguist/queue", headers=_auth(ids["teacher"])).status_code == 403
    assert client.post(f"/linguist/items/{ids['clean']}/validate",
                       headers=_auth(ids["teacher"])).status_code == 403
    _clear()


def test_no_token_unauthorized():
    client, _, _ = _client()
    assert client.get("/linguist/queue").status_code == 401
    _clear()


# ---------- file : non validés, flaggés en tête, validé absent, compteur ----------

def test_queue_lists_unvalidated_flagged_first():
    client, _, ids = _client()
    r = client.get("/linguist/queue", headers=_auth(ids["ling"])).json()
    listed = [it["item_id"] for it in r["items"]]
    assert str(ids["validated"]) not in listed          # item validé absent de la file
    assert set(listed) == {str(ids["broken"]), str(ids["clean"]), str(ids["no_ar"])}
    assert listed[0] == str(ids["broken"])               # flaggé math_broken EN TÊTE
    assert r["remaining"] == 3
    # le flag est bien exposé pour l'UI (badge « math ⚠️ »)
    flags = {it["item_id"]: it["ar_math_broken"] for it in r["items"]}
    assert flags[str(ids["broken"])] is True
    assert flags[str(ids["clean"])] is False
    _clear()


def test_item_detail_side_by_side_and_math():
    client, _, ids = _client()
    r = client.get(f"/linguist/items/{ids['broken']}", headers=_auth(ids["ling"])).json()
    assert r["content_en"]["stem"] == _EN["stem"]        # EN
    assert r["content_ar"]["stem"] == _AR_BROKEN["stem"]  # AR côte à côte
    assert r["math_preserved"] is False                  # nombre altéré → fidélité KO
    _clear()


def test_item_detail_404():
    import uuid as _u
    client, _, ids = _client()
    assert client.get(f"/linguist/items/{_u.uuid4()}",
                      headers=_auth(ids["ling"])).status_code == 404
    _clear()


# ---------- validate : ar_validated + transition d'état ; content_en jamais altéré ----------

def test_validate_sets_flag_and_transitions_state():
    client, engine, ids = _client()
    r = client.post(f"/linguist/items/{ids['clean']}/validate", headers=_auth(ids["ling"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ar_validated"] is True
    assert body["status"] == ItemStatus.LINGUIST_VALIDATED.value
    # l'item quitte la file (n'est plus ar_validated=False)
    listed = [it["item_id"] for it in
              client.get("/linguist/queue", headers=_auth(ids["ling"])).json()["items"]]
    assert str(ids["clean"]) not in listed
    _clear()


def test_edit_arabic_does_not_alter_english():
    client, engine, ids = _client()
    new_ar = {"stem": "ترجمة مصحّحة", "options": ["3/4", "2/6"], "answer": "3/4"}
    r = client.post(f"/linguist/items/{ids['no_ar']}/arabic",
                    headers=_auth(ids["ling"]), json={"content_ar": new_ar})
    assert r.status_code == 200, r.text
    assert r.json()["content_ar"]["stem"] == "ترجمة مصحّحة"
    assert r.json()["ar_validated"] is False             # set_arabic repose la validation
    with Session(bind=engine) as s:
        it = s.get(Item, ids["no_ar"])
        assert it.content_en == _EN                       # content_en INTACT (AC3)
    _clear()


def test_validate_without_arabic_conflict():
    client, _, ids = _client()
    # no_ar n'a pas de content_ar → validate refusé (machine à états) → 409
    r = client.post(f"/linguist/items/{ids['no_ar']}/validate", headers=_auth(ids["ling"]))
    assert r.status_code == 409
    _clear()


def test_flag_reraises_and_prioritizes():
    client, engine, ids = _client()
    # on flague l'item « clean » : il doit repasser ar_validated=False (déjà le cas) et
    # remonter en tête de file avec le flag.
    r = client.post(f"/linguist/items/{ids['clean']}/flag",
                    headers=_auth(ids["ling"]), json={"reason": "traduction ambiguë"})
    assert r.status_code == 200, r.text
    assert r.json()["ar_math_broken"] is True
    assert r.json()["ar_validated"] is False
    detail = client.get(f"/linguist/items/{ids['clean']}", headers=_auth(ids["ling"])).json()
    assert detail["provenance"]["flag_reason"] == "traduction ambiguë"
    _clear()


# ---------- audit : edit / validate / flag journalisés ----------

def test_audit_written_for_edit_validate_flag():
    client, engine, ids = _client()
    good = {"stem": "س", "options": ["3/4", "2/6"], "answer": "3/4"}
    client.post(f"/linguist/items/{ids['no_ar']}/arabic",
                headers=_auth(ids["ling"]), json={"content_ar": good})
    client.post(f"/linguist/items/{ids['clean']}/validate", headers=_auth(ids["ling"]))
    client.post(f"/linguist/items/{ids['broken']}/flag",
                headers=_auth(ids["ling"]), json={"reason": "erreur"})
    actions = _audit_actions(engine)
    assert "linguist.edit_ar" in actions
    assert "linguist.validate_ar" in actions
    assert "linguist.flag_ar" in actions
    _clear()


# ---------- auth : lien magique single-use + anti-préchargement + rejeu ----------

def test_linguist_login_get_does_not_consume():
    client, engine, _ = _client()
    client.post("/linguist/request-link", json={"email": "ling@atlas.io"})
    tok = _link_token(r"/api/linguist/login\?token=([^\"\s]+)")
    for _ in range(2):                                    # scanner d'emails (2 GET)
        r = client.get(f"/linguist/login?token={tok}", follow_redirects=False)
        assert r.status_code == 302
        assert "/linguist/confirm#token=" in r.headers["location"]
    assert _consumed_count(engine) == 0                   # GET idempotent
    _clear()


def test_linguist_magic_link_replayed_is_rejected():
    client, engine, ids = _client()
    client.post("/linguist/request-link", json={"email": "ling@atlas.io"})
    tok = _link_token(r"/api/linguist/login\?token=([^\"\s]+)")
    first = client.post("/linguist/login/confirm", json={"token": tok})
    assert first.status_code == 200 and first.json()["token"]
    # le jeton de session ouvert donne bien accès à la console linguiste
    session_token = first.json()["token"]
    assert client.get("/linguist/queue",
                      headers={"Authorization": f"Bearer {session_token}"}).status_code == 200
    # REJEU → refus sans session
    replay = client.post("/linguist/login/confirm", json={"token": tok})
    assert replay.status_code == 401 and replay.json()["detail"] == "used"
    get_replay = client.get(f"/linguist/login?token={tok}", follow_redirects=False)
    assert get_replay.status_code == 302
    assert "linguist_error=used" in get_replay.headers["location"]
    assert "confirm" not in get_replay.headers["location"]
    _clear()


def test_linguist_request_link_non_linguist_sends_nothing():
    # anti-énumération : un email non-linguiste (teacher) ne déclenche AUCUN envoi.
    client, _, _ = _client()
    r = client.post("/linguist/request-link", json={"email": "teach@school.edu"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert FAKE_SENT == []
    _clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
