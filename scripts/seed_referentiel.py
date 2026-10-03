"""Seed du référentiel (T1.3) — UPSERT, statut piloté par le JSON.

Porte d'entrée SÛRE : valide le graphe (contrôles A1.7 : DAG, nommage, bornes de poids,
arêtes cohérentes) AVANT tout insert. Les avertissements méthodologiques (densité,
monotonie des priors, contextes, REASON/grade) sont imprimés, pas bloquants — ils vont
dans le dossier de revue A1.8.

Idempotent ET correctif (revue 2026-09-20) : jusqu'ici le seed était insert-only, donc
corriger un prior, un label ou un poids après revue experte n'avait AUCUN effet sur une
base déjà seedée — la boucle « revue → correction → re-seed » était cassée. Désormais :
  · nœud existant  → labels, grade, niveau cognitif, prior mis à jour s'ils diffèrent ;
  · arête existante → type/poids mis à jour s'ils diffèrent, `weight_version += 1`
    (traçabilité, comme sur le crosswalk) ;
  · nœud soft-deleted → jamais ressuscité ni modifié (dépréciation respectée) ;
  · le STATUT n'est jamais rétrogradé par le seed (active → draft ne se fait pas ici).

Statut : `meta.status` du JSON (défaut `draft`), surchargeable nœud par nœud (`status`).
Aucun nœud ne passe `active` sans que le référentiel le déclare — c'est le gate A1.8
(double validation experte) qui autorise à écrire `"status": "active"` dans le fichier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# rendre le package `src` importable quand le script est lancé directement
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.graph.validator import check_referentiel
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


def validate_referentiel(data: dict, *, external_codes=frozenset(), quiet: bool = False) -> None:
    """Rejette tout graphe invalide AVANT insertion. Lève SeedValidationError.

    `external_codes` : codes d'autres domaines déjà en base (les ponts vers eux sont légitimes).
    """
    rep = check_referentiel(data, external_codes=external_codes)
    if not rep.ok:
        raise SeedValidationError("Référentiel invalide :\n  - " + "\n  - ".join(rep.errors))
    if not quiet:
        print(f"  Racines (sans prérequis) : {rep.stats['roots']}")
        for w in rep.warnings:
            print(f"  ! {w}")


def _node_status(node: dict, data: dict) -> CompetencyStatus:
    raw = node.get("status", (data.get("meta") or {}).get("status", "draft"))
    return CompetencyStatus(raw)


def seed(session: Session, data: Optional[dict] = None, *, quiet: bool = False) -> dict:
    """Insère/met à jour le référentiel. Idempotent. Retourne un compte-rendu."""
    data = data or load_referentiel()
    # Les codes déjà en base (autres domaines) rendent les ponts légitimes.
    existing = {c.code: c for c in session.execute(select(Competency)).scalars()}
    validate_referentiel(data, external_codes=frozenset(existing), quiet=quiet)

    # --- upsert compétences (clé = code) ---
    n_created = n_updated = n_activated = 0
    for node in data["nodes"]:
        status = _node_status(node, data)
        comp = existing.get(node["code"])
        if comp is None:
            session.add(Competency(
                code=node["code"],
                label_en=node["label_en"],
                label_ar=node["label_ar"],
                subject=Subject.MATH,
                grade=node["grade"],
                cognitive_level=CognitiveLevel(node["cognitive_level"]),
                difficulty_prior=float(node["difficulty_prior"]),
                status=status,
            ))
            n_created += 1
            continue
        if comp.deleted_at is not None:
            continue  # déprécié : on ne ressuscite pas, on ne modifie pas
        changed = False
        for attr, val in (("label_en", node["label_en"]), ("label_ar", node["label_ar"]),
                          ("grade", node["grade"]),
                          ("cognitive_level", CognitiveLevel(node["cognitive_level"])),
                          ("difficulty_prior", float(node["difficulty_prior"]))):
            if getattr(comp, attr) != val:
                setattr(comp, attr, val); changed = True
        # Promotion draft → active si le JSON le déclare ; jamais l'inverse ici.
        if status == CompetencyStatus.ACTIVE and comp.status != CompetencyStatus.ACTIVE:
            comp.status = CompetencyStatus.ACTIVE; n_activated += 1; changed = True
        if changed:
            n_updated += 1
    session.flush()

    # --- upsert arêtes (clé = (source_id, target_id)) ---
    code_to_id = {c.code: c.id for c in session.execute(select(Competency)).scalars()}
    existing_edges = {
        (e.source_id, e.target_id): e
        for e in session.execute(select(CompetencyPrerequisite)).scalars()
    }
    e_created = e_updated = 0
    for s_code, t_code, etype, weight in data["edges"]:
        key = (code_to_id[s_code], code_to_id[t_code])
        edge = existing_edges.get(key)
        if edge is None:
            session.add(CompetencyPrerequisite(
                source_id=key[0], target_id=key[1],
                edge_type=EdgeType(etype), correlation_strength=float(weight),
                weight_source=WeightSource.EXPERT, weight_version=1,
            ))
            e_created += 1
            continue
        if edge.edge_type != EdgeType(etype) or abs(edge.correlation_strength - float(weight)) > 1e-9:
            edge.edge_type = EdgeType(etype)
            edge.correlation_strength = float(weight)
            edge.weight_source = WeightSource.EXPERT   # un poids re-fixé par l'expert redevient expert
            edge.weight_version = (edge.weight_version or 1) + 1
            e_updated += 1
    session.commit()

    return {
        "competencies_total": len(data["nodes"]),
        "competencies_created": n_created,
        "competencies_updated": n_updated,
        "competencies_activated": n_activated,
        "edges_total": len(data["edges"]),
        "edges_created": e_created,
        "edges_updated": e_updated,
    }


def main() -> None:
    """CLI : seed la DB pointée par DATABASE_URL (SQLite dev par défaut).

    Pré-requis : `alembic upgrade head` (les tables doivent exister).
    """
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from src.db import SessionLocal, make_engine

    import argparse
    ap = argparse.ArgumentParser(description="Seed (upsert) d'un référentiel de compétences.")
    ap.add_argument("--referentiel", type=_Path, default=DATA_PATH,
                    help="JSON {nodes, edges, meta} (défaut : data/referentiel_fractions.json)")
    args = ap.parse_args()

    engine = make_engine()
    with SessionLocal(bind=engine) as session:
        report = seed(session, load_referentiel(args.referentiel))
    print("Seed terminé :", report)


if __name__ == "__main__":
    main()
