"""Mouvement 02 (bench Alef→Atlas) — faire descendre l'arabe dans le contenu.

Le pipeline AR (items/arabic.py + review.py) existait mais n'était exposé nulle part :
ici on couvre la console linguiste HTTP (propose via Groq/ALLaM → valide) + la mesure de
couverture AR, en gardant le gate `ar_validated` comme seule porte vers le pool servi.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app, get_db, get_llm_client
from src.items.arabic import ar_coverage
from src.items.review import list_pending_arabic
from src.llm.client import FakeLLMClient
from src.models import competency, item, measurement, org, session as _se  # noqa: F401
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, Role, Subject,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import School
from src.models.org import AppUser, Membership
from src.rbac.auth import make_token

# Réponse AR du faux LLM : stem traduit, mais chiffres/options identiques (fidélité math OK).
_AR_JSON = '{"stem": "ما هو ١/٢ + ١/٤؟", "options": ["3/4", "2/6"], "answer": "3/4"}'


def _item(comp_id, status=ItemStatus.HUMAN_REVIEWED, with_ar=False):
    it = Item(competency_id=comp_id, answer_format=AnswerFormat.MCQ, difficulty_prior=1400.0,
              status=status,
              content_en={"stem": "What is 1/2 + 1/4?", "options": ["3/4", "2/6"], "answer": "3/4"})
    if with_ar:
        it.content_ar = {"stem": "س", "options": ["3/4", "2/6"], "answer": "3/4"}
        it.ar_validated = True
    return it


def _setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda c, r: c.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    sa_ = School(name="A"); s.add(sa_); s.flush()
    comp = Competency(code="M.A", label_en="Add fractions", label_ar="جمع الكسور",
                      subject=Subject.MATH, grade=4, difficulty_prior=1500.0,
                      status=CompetencyStatus.ACTIVE)
    s.add(comp); s.flush()
    pending = _item(comp.id)                                   # à traduire (human_reviewed, sans AR)
    done = _item(comp.id, status=ItemStatus.ACTIVE, with_ar=True)  # déjà servi (AR validé)
    s.add_all([pending, done]); s.flush()

    ped = AppUser(email="ped@a.io"); teacher = AppUser(email="t@a.io")
    s.add_all([ped, teacher]); s.flush()
    s.add_all([
        Membership(user_id=ped.id, role=Role.PED_ADMIN, school_id=sa_.id),
        Membership(user_id=teacher.id, role=Role.TEACHER, school_id=sa_.id),
    ])
    s.commit()
    ids = dict(ped=ped.id, teacher=teacher.id, pending=pending.id, done=done.id)
    app.dependency_overrides[get_db] = lambda: s
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient([_AR_JSON])
    return TestClient(app), ids, s


def _auth(uid):
    return {"Authorization": f"Bearer {make_token(str(uid))}"}


def test_coverage_is_measurable():
    client, ids, s = _setup()
    cov = ar_coverage(s)
    assert cov["total_items"] == 2
    assert cov["with_ar"] == 1            # seul `done` a de l'AR
    assert cov["ar_validated"] == 1
    assert cov["active"] == 1
    assert cov["math_preserved"] == 1     # done : options/réponse identiques
    assert 0.0 < cov["pct_validated"] <= 1.0
    app.dependency_overrides.clear()


def test_pending_worklist_excludes_validated():
    client, ids, s = _setup()
    pend = list_pending_arabic(s)
    assert [str(it.id) for it in pend] == [str(ids["pending"])]  # `done` exclu (déjà validé)
    app.dependency_overrides.clear()


def test_propose_then_validate_flow():
    client, ids, s = _setup()
    # 1) PROPOSE : la machine (Groq/ALLaM) propose l'AR, ar_validated reste False
    r = client.post(f"/admin/arabic/{ids['pending']}/propose", headers=_auth(ids["ped"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["content_ar"]["stem"].startswith("ما")  # AR proposé
    assert body["ar_validated"] is False
    assert body["math_preserved"] is True               # chiffres préservés EN↔AR

    # 2) VALIDATE : le linguiste valide → ar_validated + statut linguist_validated
    r2 = client.post(f"/admin/arabic/{ids['pending']}/validate", headers=_auth(ids["ped"]))
    assert r2.status_code == 200, r2.text
    assert r2.json()["ar_validated"] is True
    assert r2.json()["status"] == ItemStatus.LINGUIST_VALIDATED.value

    # la couverture validée a progressé
    cov = client.get("/admin/arabic/coverage", headers=_auth(ids["ped"])).json()
    assert cov["ar_validated"] == 2
    app.dependency_overrides.clear()


def test_validate_blocked_without_arabic():
    client, ids, s = _setup()
    # pas de content_ar proposé → validation refusée (gate)
    r = client.post(f"/admin/arabic/{ids['pending']}/validate", headers=_auth(ids["ped"]))
    assert r.status_code == 400
    app.dependency_overrides.clear()


def test_rbac_linguist_only():
    client, ids, s = _setup()
    assert client.get("/admin/arabic/coverage", headers=_auth(ids["teacher"])).status_code == 403
    assert client.get("/admin/arabic/coverage").status_code == 401
    assert client.post(f"/admin/arabic/{ids['pending']}/propose",
                       headers=_auth(ids["teacher"])).status_code == 403
    app.dependency_overrides.clear()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
