"""scripts/replay_measures.py — recalcul des estimations après un changement de graphe.

Les Response sont append-only « pour recalculer a posteriori » (DataModel §5.2) ; aucun
outil ne le faisait. Le rejeu doit (1) reproduire exactement l'état courant si rien n'a
changé, (2) refléter un nouveau poids d'arête, (3) ne jamais dupliquer une Response.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from scripts.replay_measures import replay
from src.engine.service import on_response
from src.models import audit, competency, item, measurement, org, session as _se  # noqa: F401
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, EdgeType, ItemStatus, Subject, WeightSource,
)
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility

CONTENT = {"stem": "?", "options": ["a", "b"], "answer": "a"}


def _setup():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = Session(bind=engine)
    school = School(name="S"); s.add(school); s.flush()
    st = Student(school_id=school.id); s.add(st); s.flush()
    a = Competency(code="X.A", label_en="a", label_ar="ا", subject=Subject.MATH, grade=4,
                   difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    b = Competency(code="X.B", label_en="b", label_ar="ب", subject=Subject.MATH, grade=4,
                   difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add_all([a, b]); s.flush()
    edge = CompetencyPrerequisite(source_id=a.id, target_id=b.id, edge_type=EdgeType.HARD,
                                  correlation_strength=0.8, weight_source=WeightSource.EXPERT)
    s.add(edge)
    items = [Item(competency_id=b.id, content_en=dict(CONTENT), answer_format=AnswerFormat.MCQ,
                  difficulty_prior=1500.0, difficulty_elo=1500.0, status=ItemStatus.ACTIVE)
             for _ in range(5)]
    s.add_all(items); s.commit()
    for i, it in enumerate(items):
        on_response(s, student_id=st.id, item_id=it.id, is_correct=(i % 3 != 0), school_id=school.id)
    return s, st, a, b, edge


def _abilities(s, st):
    return {row.competency_id: (round(row.ability_elo, 6), row.n_direct, round(row.confidence, 6))
            for row in s.execute(select(StudentCompetencyAbility)
                                 .where(StudentCompetencyAbility.student_id == st.id)).scalars()}


def test_dry_run_changes_nothing():
    s, st, a, b, edge = _setup()
    before = _abilities(s, st)
    r = replay(s, execute=False)
    assert r["executed"] is False and r["responses"] == 5
    assert _abilities(s, st) == before


def test_replay_reproduces_current_state_when_graph_unchanged():
    s, st, a, b, edge = _setup()
    before = _abilities(s, st)
    n_resp = s.execute(select(func.count()).select_from(Response)).scalar_one()
    r = replay(s, execute=True)
    assert r["executed"] and r["replayed"] == 5
    assert _abilities(s, st) == before
    assert s.execute(select(func.count()).select_from(Response)).scalar_one() == n_resp  # rien dupliqué
    # la difficulté des items est recalculée à l'identique
    for it in s.execute(select(Item)).scalars():
        assert it.n_responses == 1


def test_replay_reflects_new_edge_weight():
    s, st, a, b, edge = _setup()
    before = _abilities(s, st)
    propagated_before = before[a.id][0]
    assert before[a.id][1] == 0            # A n'est jamais mesurée directement : propagée
    edge.correlation_strength = 0.65        # ré-estimation experte du poids
    edge.weight_version = 2
    s.commit()
    replay(s, execute=True)
    after = _abilities(s, st)
    assert after[b.id] == before[b.id]      # la mesure DIRECTE de B ne dépend pas de l'arête
    assert after[a.id][0] != propagated_before   # la propagation vers A, si
    assert after[a.id][1] == 0
