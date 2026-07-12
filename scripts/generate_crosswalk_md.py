"""Génère la vue markdown du crosswalk depuis le pivot JSON (Lot B, B1/B-2).

Règle structurante B1 : le JSON est la source de vérité, le markdown une VUE
GÉNÉRÉE — fin du double entretien (risque n°3 du cadrage : dérive doc/produit).
Même structure que l'authored : légende, table 32 lignes, synthèse CALCULÉE
(jamais saisie), section MoE. Les types/confiances sont désormais PAR framework
(réconciliation B-0) : la table porte une colonne alignement par framework.

Usage : python scripts/generate_crosswalk_md.py [--pivot P] [--out O]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_crosswalk import (
    PIVOT_PATH,
    REFERENTIEL_PATH,
    active_competencies_from_json,
    compute_synthesis,
    load_pivot,
    validate_crosswalk,
)

OUT_PATH = (
    Path(__file__).resolve().parents[2] / "03_referentiel"
    / "Crosswalk-Curriculum-Fractions.generated.md"
)

HEADER = (
    "> **GÉNÉRÉ — ne pas éditer.** Vue produite par `04_code/scripts/generate_crosswalk_md.py`"
    " depuis `crosswalk_fractions_draft.json` (source de vérité) ; remplacera l'authored"
    " (`Crosswalk-Curriculum-Fractions.md`) après confirmation expert"
    " (`reconciliation.expert_confirmation_pending`). Toute correction se fait dans le"
    " pivot JSON, puis régénération.\n"
)


def _short(code: str) -> str:
    """MATH.G4.NF.ADD_UNLIKE_LCM -> NF.ADD_UNLIKE_LCM (convention de l'authored)."""
    return ".".join(code.split(".")[2:])


def _align(entry: dict) -> str:
    return f"{entry['alignment']} ({entry['confidence']})"


def _notes(m: dict) -> str:
    parts = []
    for label, key in (("CCSS", "ccss_m"), ("UK", "uk_nc")):
        entry = m[key]
        note = " ".join(p for p in (entry.get("note"), entry.get("reconciliation_note")) if p)
        if note:
            parts.append(f"{label} : {note}")
    return " · ".join(parts)


def generate(pivot: dict, referentiel_path: Path = REFERENTIEL_PATH) -> str:
    # labels/grades des compétences : le pivot ne les porte pas, le référentiel oui
    ref = json.loads(Path(referentiel_path).read_text(encoding="utf-8"))
    nodes = {n["code"]: n for n in ref["nodes"]}
    mappings = pivot["mappings"]
    synth = compute_synthesis(mappings)  # synthèse CALCULÉE, jamais lue du fichier

    fw = pivot["frameworks"]
    lines = [
        "# Crosswalk curriculaire — Fractions (CCSS-M ↔ UK NC ↔ MoE UAE) — vue générée",
        "",
        HEADER,
        f"**Statut pivot** : {pivot['version']} · **Généré depuis** : pivot du {pivot['generated']}"
        f" · **Périmètre** : {len(mappings)} compétences",
        f"**État** : {pivot['status']}",
        "",
        "**Frameworks mappés** :",
    ]
    for key, f in fw.items():
        lines.append(
            f"- **{key}** — *{f['name']}*, {f['publisher']}, édition {f['edition']}."
            f" Grain : {f['grain']}. Stabilité : {f['stability']}."
        )
    lines += [
        "",
        "---",
        "",
        "## Légende — types d'alignement",
        "",
        "| Type | Sens |",
        "|---|---|",
    ]
    for t, sense in pivot["alignment_types"].items():
        lines.append(f"| **{t}** | {sense} |")
    conf = pivot["confidence_levels"]
    lines += [
        "",
        "Confiance : " + " · ".join(f"**{k}** ({v})" for k, v in conf.items()) + ".",
        "",
        "---",
        "",
        f"## Table de correspondance — {len(mappings)} compétences",
        "",
        "Types et confiances **par framework** (réconciliation B-0 du 2026-07-11).",
        "",
        "| # | Code Atlas | Compétence | G | CCSS-M | Align. CCSS | UK NC (year) | Align. UK | Note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m in mappings:
        node = nodes[m["competency_code"]]
        ccss, uk = m["ccss_m"], m["uk_nc"]
        lines.append(
            f"| {m['n']} | `{_short(m['competency_code'])}` | {node['label_en']} "
            f"| {node['grade']} | {', '.join(ccss['standards'])} | {_align(ccss)} "
            f"| {uk['years']} {uk['descriptor']} | {_align(uk)} | {_notes(m)} |"
        )

    # --- synthèse calculée ---
    types = list(pivot["alignment_types"])  # EXACT, PARTIAL, BROADER, PREREQ, ENRICH
    lines += [
        "",
        "---",
        "",
        "## Synthèse de couverture (calculée depuis les lignes — jamais saisie)",
        "",
        "| Framework | Compétences couvertes | " + " | ".join(types) + " |",
        "|---|---|" + "---|" * len(types),
    ]
    for key in ("CCSS_M", "UK_NC"):
        s = synth[key]
        lines.append(
            f"| **{key}** | {s['covered']} / {len(mappings)} | "
            + " | ".join(str(s.get(t, 0)) for t in types) + " |"
        )
    moe_s = synth["MOE_UAE"]
    moe_cog = " · ".join(f"{k} {v}" for k, v in moe_s["cognitive_levels"].items())
    lines.append(
        f"| **MOE_UAE** | {moe_s['covered']} / {len(mappings)} | "
        + f"grain domaine + grade-band (pas de types — cognitif : {moe_cog}) "
        + "| " * (len(types) - 1) + "|"
    )

    # --- section MoE ---
    lines += [
        "",
        "---",
        "",
        "## MoE UAE — mapping par domaine + grade-band + niveau cognitif",
        "",
        "Le framework MoE **ne publie pas de standards codés** : le mapping se fait au"
        " grain réel `domaine → sous-strand → grade-band → niveau cognitif` (clé composée"
        " en base, ex. `NUM_OPS.G4-G5` — jamais un pseudo-code inventé). Le niveau"
        " cognitif est aligné 1:1 sur l'enum `CognitiveLevel` d'Atlas (RECALL→Knowing,"
        " APPLY→Applying, REASON→Reasoning) ; les propositions originales divergentes"
        " sont conservées en « authored » pour audit.",
        "",
        "| # | Code Atlas | Domaine MoE | Sous-strand | Grade-band (Cycle 1) "
        "| Niveau cognitif | Conf. | Cognitif authored |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in mappings:
        moe = m["moe_uae"]
        c = moe["confidence"]
        lines.append(
            f"| {m['n']} | `{_short(m['competency_code'])}` | {moe['domain']} "
            f"| {moe['strand']} | {moe['grade_band']} | {moe['cognitive_level']} "
            f"| {c['domain']}/{c['grade_band']} | {moe.get('authored_cognitive', '—')} |"
        )
    lines += [
        "",
        "> **Légende confiance** : `H/M` = domaine (H, certain) / grade-band (M, estimé — "
        "fiabilisation B7 en attente du document d'outcomes par grade du MoE).",
        "",
        "---",
        "",
        "## Provenance",
        "",
        f"- **Source** : `03_referentiel/crosswalk_fractions_draft.json` (pivot {pivot['version']},"
        f" généré le {pivot['generated']}) — lui-même issu de {pivot['source']}.",
        "- **weight_source** : `expert` (crosswalk auteur, citant les frameworks publiés).",
        "- **Validation** : 0 erreur au validateur CI B6 (`scripts/validate_crosswalk.py`).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Génère la vue markdown du crosswalk (B1).")
    p.add_argument("--pivot", type=Path, default=PIVOT_PATH)
    p.add_argument("--referentiel", type=Path, default=REFERENTIEL_PATH)
    p.add_argument("--out", type=Path, default=OUT_PATH)
    args = p.parse_args()

    pivot = load_pivot(args.pivot)
    # même porte que le seed : on ne génère pas une vue depuis un pivot invalide
    errors = validate_crosswalk(pivot, active_competencies_from_json(args.referentiel))
    if errors:
        print(f"Pivot invalide ({len(errors)} erreur(s)) — génération refusée :")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    args.out.write_text(generate(pivot, args.referentiel), encoding="utf-8")
    print(f"Vue générée : {args.out}")


if __name__ == "__main__":
    main()
