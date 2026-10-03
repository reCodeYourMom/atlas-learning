"""Validateur CI du crosswalk curriculaire (Lot B, B6).

Porte d'entrée SÛRE du pipeline crosswalk : les 5 règles du cadrage B6 sont
vérifiées AVANT tout seed (seed_crosswalk refuse de tourner si ce validateur
échoue) et en CI (mode --json). Échec = build fail, exit code ≠ 0.

Règles (Cadrage-LotB §3/B6) :
  R1 — toute compétence `active` (DB ou JSON référentiel) est mappée dans
       CHAQUE framework du pivot ;
  R2 — tout alignment_type est explicite par framework (aucun derivation
       "row" résiduel non confirmé) ;
  R3 — cognitif MoE ≡ cognitive_level de la compétence (ou override avec
       note non vide) ;
  R4 — les comptes de synthèse sont CALCULÉS : le recalcul depuis les lignes
       doit égaler `computed_synthesis` du fichier (jamais saisis à la main) ;
  R5 — codes syntaxiquement valides par framework (CCSS, UK years, MoE clé
       composée domaine+grade-band).

Usage : python scripts/validate_crosswalk.py [--pivot P] [--referentiel R]
                                             [--from-db] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PIVOT_PATH = (
    Path(__file__).resolve().parents[2] / "03_referentiel" / "crosswalk_fractions_draft.json"
)
REFERENTIEL_PATH = Path(__file__).resolve().parents[1] / "data" / "referentiel_fractions.json"

# clés du registre pivot -> clés des entrées de mapping
FRAMEWORK_KEYS = {"CCSS_M": "ccss_m", "UK_NC": "uk_nc", "MOE_UAE": "moe_uae"}
ALIGNMENT_TYPES = {"EXACT", "PARTIAL", "BROADER", "PREREQ", "ENRICH"}
CONFIDENCES = {"H", "M"}
# "row" = type de ligne non confirmé par framework (interdit post-réconciliation, R2)
DERIVATIONS_OK = {"note", "row-confirmed", "reconciled"}

# pont 1:1 enum Atlas <-> niveaux cognitifs TIMSS du MoE (R3)
COGNITIVE_TO_TIMSS = {"RECALL": "Knowing", "APPLY": "Applying", "REASON": "Reasoning"}

# R5 — syntaxe des codes par framework. CCSS : base ^\d\.[A-Z]+\.[A-Z]\.\d+$ avec
# tolérance pour les codes sans feuille ("3.OA") et les sous-feuilles ("4.NF.B.3a").
CCSS_RE = re.compile(r"^\d\.[A-Z]+(\.[A-Z]\.\d+[a-z]?)?$")
UK_RE = re.compile(r"^Y[1-6](-Y[1-6])?$")
MOE_BAND_RE = re.compile(r"^G\d(-G\d)?$")
MOE_KEY_RE = re.compile(r"^[A-Z_]+\.G\d(-G\d)?$")

# domaines MoE connus -> clé composée (jamais un pseudo-code inventé, ligne rouge B2)
MOE_DOMAIN_KEYS = {"Numbers & Operations": "NUM_OPS"}


def load_pivot(path: Path = PIVOT_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def active_competencies_from_json(path: Path = REFERENTIEL_PATH) -> Dict[str, str]:
    """code -> cognitive_level, depuis le JSON référentiel (les nœuds seedés sont actifs)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {n["code"]: n["cognitive_level"] for n in data["nodes"]}


def active_competencies_from_db(session) -> Dict[str, str]:  # noqa: ANN001
    """code -> cognitive_level, depuis la DB (compétences `active` non supprimées)."""
    from sqlalchemy import select

    from src.models.base import CompetencyStatus
    from src.models.competency import Competency

    rows = session.execute(
        select(Competency).where(
            Competency.status == CompetencyStatus.ACTIVE,
            Competency.deleted_at.is_(None),
        )
    ).scalars()
    return {c.code: (c.cognitive_level.value if c.cognitive_level else "") for c in rows}


def moe_composed_key(moe: dict) -> str:
    """Clé composée MoE 'NUM_OPS.{grade_band}' — le framework ne publie pas de codes."""
    domain_key = MOE_DOMAIN_KEYS.get(moe.get("domain", ""), "")
    return f"{domain_key}.{moe.get('grade_band', '')}"


def validate_crosswalk(pivot: dict, competencies: Dict[str, str]) -> List[str]:
    """Applique les 5 règles B6. Retourne la liste des erreurs (vide = 0 erreur)."""
    errors: List[str] = []
    mappings = pivot.get("mappings", [])
    mapped_codes = {m.get("competency_code") for m in mappings}

    # --- R1 : couverture — toute compétence active mappée dans chaque framework ---
    if not competencies:
        errors.append("R1: aucune compétence active trouvée (source DB/JSON vide).")
    for code in sorted(set(competencies) - mapped_codes):
        errors.append(f"R1: compétence active non mappée : {code}")
    for code in sorted(mapped_codes - set(competencies)):
        errors.append(f"R1: mapping vers une compétence inconnue/inactive : {code}")
    for m in mappings:
        code = m.get("competency_code", "?")
        for fw, key in FRAMEWORK_KEYS.items():
            if not m.get(key):
                errors.append(f"R1: {code} : framework {fw} absent du mapping.")

    for m in mappings:
        code = m.get("competency_code", "?")

        # --- R2 : type d'alignement explicite par framework (CCSS + UK ; le MoE
        # n'a pas de types — son grain est domaine+band, vérifié en R5) ---
        for fw in ("ccss_m", "uk_nc"):
            entry = m.get(fw) or {}
            align = entry.get("alignment")
            if align not in ALIGNMENT_TYPES:
                errors.append(f"R2: {code} [{fw}] : alignment_type manquant/invalide : {align!r}")
            if entry.get("confidence") not in CONFIDENCES:
                errors.append(f"R2: {code} [{fw}] : confidence invalide : {entry.get('confidence')!r}")
            deriv = entry.get("derivation")
            if deriv == "row":
                errors.append(f"R2: {code} [{fw}] : derivation 'row' résiduelle non confirmée.")
            elif deriv not in DERIVATIONS_OK:
                errors.append(f"R2: {code} [{fw}] : derivation inconnue : {deriv!r}")

        # --- R3 : cognitif MoE ≡ enum de la compétence, sauf override noté ---
        moe = m.get("moe_uae") or {}
        expected = COGNITIVE_TO_TIMSS.get(competencies.get(code, ""), None)
        got = moe.get("cognitive_level")
        if expected and got != expected and not (moe.get("cognitive_note") or "").strip():
            errors.append(
                f"R3: {code} : cognitif MoE '{got}' ≠ enum compétence '{expected}' sans note d'override."
            )

        # --- R5 : syntaxe des codes par framework ---
        ccss_standards = (m.get("ccss_m") or {}).get("standards") or []
        if not ccss_standards:
            errors.append(f"R5: {code} [ccss_m] : aucun standard cité.")
        for std in ccss_standards:
            if not CCSS_RE.match(std):
                errors.append(f"R5: {code} [ccss_m] : code CCSS invalide : {std!r}")
        years = (m.get("uk_nc") or {}).get("years") or ""
        if not UK_RE.match(years):
            errors.append(f"R5: {code} [uk_nc] : years invalide : {years!r}")
        if moe.get("domain") not in MOE_DOMAIN_KEYS:
            errors.append(f"R5: {code} [moe_uae] : domaine inconnu : {moe.get('domain')!r}")
        if not MOE_BAND_RE.match(moe.get("grade_band") or ""):
            errors.append(f"R5: {code} [moe_uae] : grade_band invalide : {moe.get('grade_band')!r}")
        elif moe.get("domain") in MOE_DOMAIN_KEYS and not MOE_KEY_RE.match(moe_composed_key(moe)):
            errors.append(f"R5: {code} [moe_uae] : clé composée invalide : {moe_composed_key(moe)!r}")

    # --- R4 : comptes de synthèse recalculés = ceux du fichier ---
    errors.extend(_check_synthesis(pivot, mappings))
    return errors


def compute_synthesis(mappings: List[dict]) -> dict:
    """Recalcule la synthèse depuis les lignes — la seule forme autorisée (R4)."""
    synth: dict = {
        "CCSS_M": {"covered": 0},
        "UK_NC": {"covered": 0},
        "MOE_UAE": {"covered": 0, "cognitive_levels": {}},
    }
    for m in mappings:
        for fw, key in (("CCSS_M", "ccss_m"), ("UK_NC", "uk_nc")):
            entry = m.get(key) or {}
            if entry:
                synth[fw]["covered"] += 1
                align = entry.get("alignment")
                if align:
                    synth[fw][align] = synth[fw].get(align, 0) + 1
        moe = m.get("moe_uae") or {}
        if moe:
            synth["MOE_UAE"]["covered"] += 1
            lvl = moe.get("cognitive_level")
            if lvl:
                levels = synth["MOE_UAE"]["cognitive_levels"]
                levels[lvl] = levels.get(lvl, 0) + 1
    return synth


def _check_synthesis(pivot: dict, mappings: List[dict]) -> List[str]:
    errors: List[str] = []
    declared = (pivot.get("reconciliation") or {}).get("computed_synthesis")
    if not declared:
        return ["R4: `reconciliation.computed_synthesis` absent du pivot."]
    computed = compute_synthesis(mappings)
    for fw in ("CCSS_M", "UK_NC"):
        decl = {k: v for k, v in (declared.get(fw) or {}).items() if k != "grain"}
        if decl != computed[fw]:
            errors.append(f"R4: synthèse {fw} : fichier {decl} ≠ recalcul {computed[fw]}")
    decl_moe = declared.get("MOE_UAE") or {}
    if decl_moe.get("covered") != computed["MOE_UAE"]["covered"]:
        errors.append(
            f"R4: synthèse MOE_UAE.covered : fichier {decl_moe.get('covered')} "
            f"≠ recalcul {computed['MOE_UAE']['covered']}"
        )
    if decl_moe.get("cognitive_levels") != computed["MOE_UAE"]["cognitive_levels"]:
        errors.append(
            f"R4: synthèse MOE_UAE.cognitive_levels : fichier {decl_moe.get('cognitive_levels')} "
            f"≠ recalcul {computed['MOE_UAE']['cognitive_levels']}"
        )
    return errors


def main() -> None:
    p = argparse.ArgumentParser(description="Validateur CI du crosswalk (B6).")
    p.add_argument("--pivot", type=Path, default=PIVOT_PATH)
    p.add_argument("--referentiel", type=Path, default=REFERENTIEL_PATH,
                   help="JSON référentiel donnant les compétences actives (défaut).")
    p.add_argument("--from-db", action="store_true",
                   help="Lire les compétences actives depuis la DB (DATABASE_URL) au lieu du JSON.")
    p.add_argument("--json", action="store_true", help="Sortie JSON machine-readable (CI).")
    args = p.parse_args()

    pivot = load_pivot(args.pivot)
    if args.from_db:
        from src.db import SessionLocal, make_engine

        with SessionLocal(bind=make_engine()) as session:
            competencies = active_competencies_from_db(session)
    else:
        competencies = active_competencies_from_json(args.referentiel)

    errors = validate_crosswalk(pivot, competencies)

    if args.json:
        print(json.dumps({
            "ok": not errors,
            "errors": errors,
            "competencies_active": len(competencies),
            "mappings": len(pivot.get("mappings", [])),
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Pivot : {args.pivot}")
        print(f"Compétences actives ({'DB' if args.from_db else 'JSON'}) : {len(competencies)}")
        print(f"Mappings : {len(pivot.get('mappings', []))}")
        if errors:
            print(f"\n{len(errors)} erreur(s) :")
            for e in errors:
                print(f"  ✗ {e}")
        else:
            print("\n0 erreur — crosswalk valide (règles B6 R1–R5).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
