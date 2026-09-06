"""La session renvoie le déplacement de l'estimation de maîtrise — et ne se bloque plus.

Deux régressions que ces tests interdisent, toutes deux constatées en rejouant le parcours
de démo de bout en bout :

  1. `POST /sessions/{id}/responses` ne renvoyait QUE `was_correct` et l'item suivant.
     L'adaptativité — le seul argument que des « outils actuels » n'ont pas — restait
     invisible : rien à montrer à l'écran.
  2. La sélection re-servait un item déjà répondu dès qu'une compétence était épuisée,
     alors que la soumission refuse un doublon (contrainte d'unicité). La session mourait
     sur un 409 au 2e item.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from src.api.session_service import (
    AlreadyAnswered,
    next_item,
    start_session,
    submit_response,
)
from src.db import make_engine
from src.models.base import (
    AnswerFormat, Base, CompetencyStatus, ItemStatus, Subject,
)
from src.models.competency import Competency
from src.models.item import Item
from src.models.measurement import School, Student

CONTENT = {"stem": "q", "options": ["1/4", "3/4"], "answer": "3/4"}


def _setup(n_items: int = 4):
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = Session(engine)
    school = School(name="Demo School")
    s.add(school); s.flush()
    student = Student(school_id=school.id, display_name="Maryam Al Zaabi")
    s.add(student)
    comp = Competency(code="MATH.G4.NF.X", label_en="Simplify a fraction",
                      label_ar="تبسيط الكسر", subject=Subject.MATH, grade=4,
                      difficulty_prior=1500.0, status=CompetencyStatus.ACTIVE)
    s.add(comp); s.flush()
    for _ in range(n_items):
        s.add(Item(competency_id=comp.id, answer_format=AnswerFormat.MCQ,
                   difficulty_prior=1500.0, status=ItemStatus.ACTIVE, content_en=CONTENT))
    s.commit()
    return s, school, student, comp


def test_la_reponse_porte_la_maitrise_avant_et_apres():
    s, school, student, comp = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)
    item_id = uuid.UUID(next_item(s, sess)["item_id"])

    out = submit_response(s, sess, item_id=item_id, is_correct=True)

    m = out["mastery"]
    assert m["competency_id"] == str(comp.id)
    assert m["label_en"] == "Simplify a fraction"
    assert m["label_ar"] == "تبسيط الكسر"          # la bascule AR a de quoi s'alimenter
    assert m["before"]["elo"] == 1500.0            # jamais mesuré → valeur d'entrée du moteur
    assert m["after"]["elo"] > m["before"]["elo"]  # bonne réponse → l'estimation monte
    assert m["delta_elo"] > 0
    assert m["after"]["n_direct"] == 1


def test_une_mauvaise_reponse_fait_baisser_l_estimation():
    s, school, student, _ = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)
    item_id = uuid.UUID(next_item(s, sess)["item_id"])

    m = submit_response(s, sess, item_id=item_id, is_correct=False)["mastery"]

    assert m["delta_elo"] < 0
    # Le seuil n'est PAS annoncé franchi quand on recule : `crossed_mastery` compare les
    # Elo, pas le drapeau `mastered` (qui bascule à la 1re mesure, même sur un échec).
    assert m["crossed_mastery"] is False


def test_le_franchissement_du_seuil_est_signale_une_fois():
    s, school, student, _ = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)
    # 1re réponse fausse : on passe sous le seuil.
    first = uuid.UUID(next_item(s, sess)["item_id"])
    out = submit_response(s, sess, item_id=first, is_correct=False)
    assert out["mastery"]["after"]["elo"] < 1500.0

    # Réponses justes ensuite : à un moment l'estimation repasse au-dessus, une seule fois.
    franchissements = 0
    while not out.get("done"):
        out = submit_response(s, sess, item_id=uuid.UUID(out["item_id"]), is_correct=True)
        if out.get("mastery", {}).get("crossed_mastery"):
            franchissements += 1
    assert franchissements == 1


def test_aucun_item_n_est_servi_deux_fois_dans_une_session():
    """Le cœur du bug 409 : on consomme toute la banque sans jamais rejouer un item."""
    s, school, student, _ = _setup(n_items=4)
    sess = start_session(s, student_id=student.id, school_id=school.id)

    servis = []
    out = next_item(s, sess)
    while not out.get("done"):
        assert out["item_id"] not in servis, "un item déjà répondu a été re-servi"
        servis.append(out["item_id"])
        out = submit_response(s, sess, item_id=uuid.UUID(out["item_id"]), is_correct=True)

    assert len(servis) == 4                 # les 4 items, chacun une fois
    assert out["reason"] == "no_items"      # puis fin propre, sans erreur


def test_le_double_submit_reste_refuse():
    """Le contrat d'idempotence n'est pas affaibli par le correctif de sélection."""
    s, school, student, _ = _setup()
    sess = start_session(s, student_id=student.id, school_id=school.id)
    item_id = uuid.UUID(next_item(s, sess)["item_id"])
    submit_response(s, sess, item_id=item_id, is_correct=True)
    try:
        submit_response(s, sess, item_id=item_id, is_correct=True)
        assert False, "le double submit aurait dû être refusé"
    except AlreadyAnswered:
        pass
