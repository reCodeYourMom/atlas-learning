"""Tests T1.3 — seed du référentiel. Chaque test = un AC du backlog.

Tourne sur SQLite en mémoire (modèles portables). En prod : Postgres Oracle UAE.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from scripts.seed_referentiel import (
    SeedValidationError,
    load_referentiel,
    seed,
    validate_referentiel,
)
from src.models.base import Base
from src.models.competency import Competency, CompetencyPrerequisite


def _fresh_session() -> Session:
    engine = create_engine("sqlite://")  # mémoire
    Base.metadata.create_all(engine)
    return Session(engine)


def test_ac1_count_in_range():
    # AC1 : après seed, nb compétences dans [30, 40]
    s = _fresh_session()
    seed(s)
    n = s.execute(select(func.count()).select_from(Competency)).scalar_one()
    assert 30 <= n <= 40, f"attendu 30-40, obtenu {n}"


def test_ac2_dag_valid():
    # AC2 : le graphe complet passe la validation (aucun cycle)
    data = load_referentiel()
    validate_referentiel(data)  # ne lève pas


def test_ac3_code_format():
    # AC3 : chaque code au format MATH.G{n}.{STRAND}.{SKILL}
    data = load_referentiel()
    for node in data["nodes"]:
        parts = node["code"].split(".")
        assert len(parts) == 4, f"format invalide : {node['code']}"
        assert parts[0] == "MATH"
        assert parts[1].startswith("G") and parts[1][1:].isdigit()


def test_ac4_idempotent():
    # AC4 : relancer le seed ne change pas le count
    s = _fresh_session()
    r1 = seed(s)
    n1 = s.execute(select(func.count()).select_from(Competency)).scalar_one()
    r2 = seed(s)  # relance
    n2 = s.execute(select(func.count()).select_from(Competency)).scalar_one()
    assert n1 == n2, "le seed n'est pas idempotent"
    assert r2["competencies_created"] == 0
    assert r2["edges_created"] == 0


def test_ac5_non_root_has_parent():
    # AC5 : tout nœud non-racine a au moins une arête entrante
    data = load_referentiel()
    codes = {n["code"] for n in data["nodes"]}
    has_parent = {t for _, t, *_ in data["edges"]}
    roots = codes - has_parent
    # racines légitimes attendues uniquement
    assert roots == {"MATH.G2.NS.EQUAL_SHARES", "MATH.G3.NS.MULT_FACTS"}, roots


def test_validation_rejects_cycle():
    # garde-fou : un graphe avec cycle est rejeté AVANT insert
    data = load_referentiel()
    data = {
        "nodes": data["nodes"],
        "edges": data["edges"] + [
            ("MATH.G5.NF.ADD_MIXED", "MATH.G2.NS.EQUAL_SHARES", "HARD", 0.5)
        ],  # crée un cycle remontant
    }
    try:
        validate_referentiel(data)
        assert False, "le cycle aurait dû être rejeté"
    except SeedValidationError:
        pass


def test_edges_seeded():
    s = _fresh_session()
    r = seed(s)
    n_edges = s.execute(
        select(func.count()).select_from(CompetencyPrerequisite)
    ).scalar_one()
    assert n_edges == r["edges_total"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
