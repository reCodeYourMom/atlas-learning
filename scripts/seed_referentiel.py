"""Seed du référentiel fractions (T1.3).

Porte d'entrée SÛRE : valide le graphe (DAG, arêtes cohérentes) AVANT tout insert.
Idempotent : relancer ne duplique pas (upsert sur code / PK composite).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# rendre le package `src` importable quand le script est lancé directement
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.graph.validator import find_orphans, has_cycle
from src.models.base import (
    CognitiveLevel,
    CompetencyStatus,
    EdgeType,
    Subject,
    WeightSource,
)
from src.models.competency import Competency, CompetencyPrerequisite

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "referentiel_fractions.json"


class SeedValidationError(Exception):
    pass


def load_referentiel(path: Path = DATA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_referentiel(data: dict) -> None:
    """Rejette tout graphe invalide AVANT insertion. Lève SeedValidationError."""
    nodes = data["nodes"]
    edges = data["edges"]
    codes = {n["code"] for n in nodes}

    # 1. codes uniques
    if len(codes) != len(nodes):
        raise SeedValidationError("Codes de compétences dupliqués.")

    # 2. arêtes vers nœuds existants
    bad = [(s, t) for s, t, *_ in edges if s not in codes or t not in codes]
    if bad:
        raise SeedValidationError(f"Arêtes vers nœud inexistant : {bad}")

    # 3. pas d'auto-boucle
    loops = [(s, t) for s, t, *_ in edges if s == t]
    if loops:
        raise SeedValidationError(f"Auto-boucles interdites : {loops}")

    # 4. DAG (aucun cycle)
    if has_cycle(edges):
        raise SeedValidationError("Le graphe contient un cycle (DAG requis).")

    # 5. nœuds non-racines ont au moins un parent (orphelins suspects -> juste un warning)
    orphans = find_orphans(edges, codes)
    # racines légitimes attendues : EQUAL_SHARES, MULT_FACTS
    print(f"  Racines (sans prérequis) : {sorted(orphans)}")


def seed(session: Session, data: dict | None = None) -> dict:
    """Insère/met à jour le référentiel. Idempotent. Retourne un compte-rendu."""
    data = data or load_referentiel()
    validate_referentiel(data)  # porte sûre : rejette avant insert

    # --- upsert compétences (clé = code) ---
    existing = {c.code: c for c in session.execute(select(Competency)).scalars()}
    n_created = 0
    for node in data["nodes"]:
        if node["code"] in existing:
            continue  # idempotent
        session.add(
            Competency(
                code=node["code"],
                label_en=node["label_en"],
                label_ar=node["label_ar"],
                subject=Subject.MATH,
                grade=node["grade"],
                cognitive_level=CognitiveLevel(node["cognitive_level"]),
                difficulty_prior=float(node["difficulty_prior"]),
                status=CompetencyStatus.ACTIVE,
            )
        )
        n_created += 1
    session.flush()

    # --- upsert arêtes (clé = (source_id, target_id)) ---
    code_to_id = {c.code: c.id for c in session.execute(select(Competency)).scalars()}
    existing_edges = {
        (e.source_id, e.target_id)
        for e in session.execute(select(CompetencyPrerequisite)).scalars()
    }
    e_created = 0
    for s_code, t_code, etype, weight in data["edges"]:
        key = (code_to_id[s_code], code_to_id[t_code])
        if key in existing_edges:
            continue
        session.add(
            CompetencyPrerequisite(
                source_id=key[0],
                target_id=key[1],
                edge_type=EdgeType(etype),
                correlation_strength=float(weight),
                weight_source=WeightSource.EXPERT,
                weight_version=1,
            )
        )
        e_created += 1
    session.commit()

    return {
        "competencies_total": len(data["nodes"]),
        "competencies_created": n_created,
        "edges_total": len(data["edges"]),
        "edges_created": e_created,
    }


def main() -> None:
    """CLI : seed la DB pointée par DATABASE_URL (SQLite dev par défaut).

    Pré-requis : `alembic upgrade head` (les tables doivent exister).
    """
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from src.db import SessionLocal, make_engine

    engine = make_engine()
    with SessionLocal(bind=engine) as session:
        report = seed(session)
    print("Seed terminé :", report)


if __name__ == "__main__":
    main()
