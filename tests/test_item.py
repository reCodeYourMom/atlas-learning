"""Tests T2.1 — modèle Item. 1 test = 1 AC du backlog.

SQLite fichier mémoire avec FK activées (src.db.make_engine).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db import make_engine
from src.models.base import AnswerFormat, Base, CompetencyStatus, Subject
from src.models.competency import Competency
from src.models.item import Item, ItemContent  # noqa: F401

VALID_CONTENT = {"stem": "1/2 + 1/4 = ?", "options": ["3/4", "1/2"], "answer": "3/4"}


def _fresh_session() -> Session:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def _competency(s: Session) -> Competency:
    c = Competency(
        code="MATH.G4.NF.ADD_LIKE", label_en="x", label_ar="س",
        subject=Subject.MATH, grade=4, difficulty_prior=1200.0,
        status=CompetencyStatus.ACTIVE,
    )
    s.add(c)
    s.commit()
    return c


def _item(competency_id, **over) -> Item:
    kw = dict(
        competency_id=competency_id,
        content_en=dict(VALID_CONTENT),
        content_ar={"stem": "؟", "options": ["٣/٤", "١/٢"], "answer": "٣/٤"},
        answer_format=AnswerFormat.MCQ,
        difficulty_prior=1180.0,
    )
    kw.update(over)
    return Item(**kw)


def test_ac1_table_created():
    # AC1 : la table item existe (créée par metadata / migration)
    from sqlalchemy import inspect
    s = _fresh_session()
    assert "item" in inspect(s.get_bind()).get_table_names()


def test_ac2_invalid_content_rejected():
    # AC2 : content_en non conforme à ItemContent → rejet Pydantic
    s = _fresh_session()
    c = _competency(s)
    try:
        _item(c.id, content_en={"options": ["a", "b"]})  # ni stem ni answer
        assert False, "le contenu invalide aurait dû être rejeté"
    except ValidationError:
        pass


def test_ac3_elo_defaults_to_prior():
    # AC3 : difficulty_elo par défaut = difficulty_prior à la création
    s = _fresh_session()
    c = _competency(s)
    it = _item(c.id, difficulty_prior=1337.0)  # pas de difficulty_elo fourni
    s.add(it)
    s.commit()
    assert it.difficulty_elo == 1337.0


def test_ac4_restrict_blocks_competency_delete():
    # AC4 : supprimer une compétence ayant un item vivant → bloqué (RESTRICT)
    s = _fresh_session()
    c = _competency(s)
    s.add(_item(c.id))
    s.commit()
    s.delete(c)
    try:
        s.commit()
        assert False, "la suppression aurait dû être bloquée par RESTRICT"
    except IntegrityError:
        s.rollback()


def test_ac5_context_tags_roundtrip():
    # AC5 : context_tags accepte un dict arbitraire et le relit sans perte
    s = _fresh_session()
    c = _competency(s)
    tags = {"simplify": False, "result_type": "improper",
            "denominator_max": 8, "nested": {"reps": [1, 2, 3]}}
    it = _item(c.id, context_tags=tags)
    s.add(it)
    s.commit()
    item_id = it.id
    s.expire_all()
    reloaded = s.get(Item, item_id)
    assert reloaded.context_tags == tags


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
