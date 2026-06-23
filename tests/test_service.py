"""Tests T3.4 — orchestrateur on_response. 1 test = 1 AC."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import src.engine.service as service
from src.db import make_engine
from src.engine.service import on_response
from src.models.base import AnswerFormat, Base, CompetencyStatus, EdgeType, Subject, WeightSource
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility

CONTENT = {"stem": "q", "options": ["1/4", "3/4"], "answer": "3/4"}


def _setup() -> tuple:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = Session(engine)
    school = School(name="Test School")
    s.add(school); s.flush()
    student = Student(school_id=school.id)
    s.add(student)
    # A (prérequis) → B (dépendant) ; item sur B, voisin A
    a = Competency(code="MATH.G4.NF.A", label_en="a", label_ar="ا", subject=Subject.MATH,
                   grade=4, difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    b = Competency(code="MATH.G4.NF.B", label_en="b", label_ar="ب", subject=Subject.MATH,
                   grade=4, difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add_all([a, b]); s.flush()
    s.add(CompetencyPrerequisite(source_id=a.id, target_id=b.id, edge_type=EdgeType.HARD,
                                 correlation_strength=0.8, weight_source=WeightSource.EXPERT))
    item = Item(competency_id=b.id, content_en=dict(CONTENT), content_ar=None,
                answer_format=AnswerFormat.MCQ, difficulty_prior=1500.0, difficulty_elo=1500.0)
    s.add(item); s.commit()
    return s, school, student, a, b, item


def test_ac1_response_updates_ability_and_item():
    s, school, student, a, b, item = _setup()
    on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id)
    n_resp = s.execute(select(func.count()).select_from(Response)).scalar_one()
    assert n_resp == 1
    ab = s.get(StudentCompetencyAbility, (student.id, b.id))
    assert ab.ability_elo > 1500.0 and ab.n_direct == 1          # ability directe màj
    assert s.get(Item, item.id).difficulty_elo < 1500.0          # item màj (sens inverse)
    assert s.get(Item, item.id).n_responses == 1


def test_ac2_rollback_if_propagation_fails():
    s, school, student, a, b, item = _setup()

    def boom(*args, **kwargs):
        raise RuntimeError("propagation KO")

    orig = service.propagate
    service.propagate = boom
    try:
        try:
            on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id)
            assert False, "aurait dû lever"
        except RuntimeError:
            pass
    finally:
        service.propagate = orig
    # rollback complet : aucune response, item inchangé
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 0
    assert s.get(Item, item.id).difficulty_elo == 1500.0
    assert s.get(StudentCompetencyAbility, (student.id, b.id)) is None


def test_ac3_eligible_neighbor_updated_same_transaction():
    s, school, student, a, b, item = _setup()
    on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id)
    neighbor = s.get(StudentCompetencyAbility, (student.id, a.id))  # A = prérequis
    assert neighbor is not None and neighbor.ability_elo != 1500.0   # reçu de la propagation
    assert neighbor.n_direct == 0                                    # inféré, pas mesuré


def test_ac4_all_rows_carry_school_id():
    s, school, student, a, b, item = _setup()
    on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id)
    resp = s.execute(select(Response)).scalar_one()
    assert resp.school_id == school.id
    for ab in s.execute(select(StudentCompetencyAbility)).scalars():
        assert ab.school_id == school.id


def test_ac5_no_network_call():
    # zéro appel réseau sortant : on coupe les sockets et on vérifie que ça marche
    import socket
    s, school, student, a, b, item = _setup()
    orig_connect = socket.socket.connect

    def no_net(self, *a, **k):
        raise AssertionError("appel réseau interdit dans le moteur")

    socket.socket.connect = no_net
    try:
        resp = on_response(s, student_id=student.id, item_id=item.id, is_correct=False, school_id=school.id)
        assert resp is not None
    finally:
        socket.socket.connect = orig_connect


def test_idempotent_replay():
    s, school, student, a, b, item = _setup()
    rid = uuid.uuid4()
    on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id, response_id=rid)
    ab1 = s.get(StudentCompetencyAbility, (student.id, b.id)).ability_elo
    on_response(s, student_id=student.id, item_id=item.id, is_correct=True, school_id=school.id, response_id=rid)
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == 1
    assert s.get(StudentCompetencyAbility, (student.id, b.id)).ability_elo == ab1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
