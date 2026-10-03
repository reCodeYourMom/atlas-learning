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


# --- revue 2026-09-20 : le seed est un UPSERT, le statut vient du JSON ---

def test_seed_propagates_corrections_after_expert_review():
    # Le seed était insert-only : corriger un prior/label/poids après revue n'avait aucun
    # effet. Désormais la correction est propagée et le poids d'arête est versionné.
    s = _fresh_session()
    data = load_referentiel()
    seed(s, data)
    code = data["nodes"][0]["code"]
    data["nodes"][0]["difficulty_prior"] += 40
    data["nodes"][0]["label_en"] = "Corrigé après double lecture"
    src, tgt, etype, w = data["edges"][0]
    data["edges"][0] = [src, tgt, etype, round(w - 0.05, 2)]
    r = seed(s, data)
    assert r["competencies_created"] == 0 and r["competencies_updated"] == 1
    assert r["edges_created"] == 0 and r["edges_updated"] == 1
    comp = s.execute(select(Competency).where(Competency.code == code)).scalar_one()
    assert comp.label_en == "Corrigé après double lecture"
    edge = s.execute(select(CompetencyPrerequisite)).scalars().first()
    ids = {c.code: c.id for c in s.execute(select(Competency)).scalars()}
    edge = s.get(CompetencyPrerequisite, (ids[src], ids[tgt]))
    assert edge.weight_version == 2 and abs(edge.correlation_strength - (w - 0.05)) < 1e-9
    # rejouer sans changement : rien ne bouge, la version reste à 2
    r2 = seed(s, data)
    assert r2["competencies_updated"] == 0 and r2["edges_updated"] == 0
    assert s.get(CompetencyPrerequisite, (ids[src], ids[tgt])).weight_version == 2


def test_seed_never_activates_without_declaration():
    # Un référentiel sans `meta.status: active` (ex. brouillon décimaux) est seedé en DRAFT :
    # aucun nœud ne passe `active` sans passer par le gate A1.8.
    from src.models.base import CompetencyStatus
    s = _fresh_session()
    data = load_referentiel()
    draft = {"nodes": data["nodes"], "edges": data["edges"]}   # pas de meta
    seed(s, draft)
    statuses = {c.status for c in s.execute(select(Competency)).scalars()}
    assert statuses == {CompetencyStatus.DRAFT}
    # …et le fichier fractions, lui, déclare `active` : le seed l'écrit (et ne rétrograde jamais)
    r = seed(s, data)
    assert r["competencies_activated"] == len(data["nodes"])
    statuses = {c.status for c in s.execute(select(Competency)).scalars()}
    assert statuses == {CompetencyStatus.ACTIVE}
    seed(s, draft)   # re-seeder le brouillon ne rétrograde pas
    assert {c.status for c in s.execute(select(Competency)).scalars()} == {CompetencyStatus.ACTIVE}


def test_seed_rejects_weight_out_of_bounds():
    data = load_referentiel()
    bad = {"nodes": data["nodes"],
           "edges": data["edges"] + [["MATH.G2.NS.EQUAL_SHARES", "MATH.G5.NF.ADD_MIXED", "HARD", 0.5]]}
    try:
        validate_referentiel(bad, quiet=True)
        assert False, "HARD 0.5 est sous le plancher méthodologique (E4)"
    except SeedValidationError as exc:
        assert "E-WEIGHT" in str(exc)


def test_both_json_copies_are_identical():
    # 03_referentiel/ (lu par les humains) et 04_code/data/ (lu par le code) : aucun test
    # ne vérifiait l'égalité → drift silencieux garanti à la première correction.
    import json
    root = Path(__file__).resolve().parents[2]
    a = json.loads((root / "03_referentiel" / "referentiel_fractions.json").read_text(encoding="utf-8"))
    b = json.loads((root / "04_code" / "data" / "referentiel_fractions.json").read_text(encoding="utf-8"))
    assert a == b


def test_decimals_draft_passes_structural_checks_with_fractions():
    # Le brouillon décimaux a 5 ponts vers les fractions : validé sur le graphe COMBINÉ.
    import json
    from src.graph.validator import check_referentiel, has_cycle
    root = Path(__file__).resolve().parents[2]
    fr = load_referentiel()
    dec = json.loads((root / "03_referentiel" / "referentiel_decimals_draft.json").read_text(encoding="utf-8"))
    rep = check_referentiel(dec, external_codes={n["code"] for n in fr["nodes"]})
    assert rep.ok, rep.errors
    assert rep.stats["n_bridges"] == 5 and rep.stats["density_intra"] == 1.5
    assert not has_cycle(fr["edges"] + dec["edges"])
    # le brouillon n'est PAS déclaré actif : le seeder le laisserait en draft
    assert (dec.get("meta") or {}).get("status", "draft") == "draft"


def test_check_referentiel_reports_fractions_known_exceptions():
    # Les écarts méthodologiques connus du référentiel fractions sont des AVERTISSEMENTS
    # (à documenter dans le dossier de revue), pas des erreurs — dont l'arête inversée en
    # grade IMPROPER_TO_MIXED → ADD_SAME_IMPROPER (Methodologie-Referentiel, exception E4).
    from src.graph.validator import check_referentiel
    rep = check_referentiel(load_referentiel())
    assert rep.ok
    assert any("IMPROPER_TO_MIXED" in w and "W-PRIOR-MONOTONIC" in w for w in rep.warnings)
    assert rep.stats["density_intra"] == 1.438
    assert len(rep.stats["longest_hard_chain"]) == 11
    assert rep.stats["cognitive"] == {"RECALL": 2, "APPLY": 18, "REASON": 12}
