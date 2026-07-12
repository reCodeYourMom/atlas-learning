"""DIF EN/AR par item — Mantel-Haenszel (livrable C4.1, Cadrage-LotC §3/C4).

Pour chaque item, compare la réussite des élèves servis en ANGLAIS (groupe de
référence) et en ARABE (groupe focal) À ABILITY COMPARABLE : les répondants sont
stratifiés en déciles d'ability (StudentCompetencyAbility sur la compétence de
l'item), puis on calcule l'odds ratio commun de Mantel-Haenszel sur les tables
2×2 par strate, converti en delta ETS (ΔMH = −2.35·ln(α_MH)) et classé A/B/C :

  A (négligeable)  |ΔMH| < 1.0 OU non significatif (χ² MH < 3.841)   → aucune action
  B (modéré)       1.0 ≤ |ΔMH| < 1.5 significatif                    → revue linguiste
  C (sévère)       |ΔMH| ≥ 1.5 ET significativement > 1.0 (RBG)      → retrait + régénération

Significativité sans scipy : χ² MH avec correction de continuité comparé à la
valeur critique 3.841 (χ², 1 ddl, 5 %) ; variance de ln(α_MH) par l'estimateur
Robins-Breslow-Greenland (RBG), en pur stdlib.

DÉPENDANCE C-0 (Cadrage-LotC §3/C-0) : la colonne `response.language` ('en'/'ar')
est ajoutée par un chantier séparé (migration Alembic + locale de session). Ce
script y accède DÉFENSIVEMENT à DEUX niveaux, car le modèle ORM et la base
interrogée peuvent être désynchronisés (modèle déjà fusionné, base pas encore
migrée) :
  1. modèle : getattr sur l'attribut `language` (absent → inconnu) ;
  2. base : inspection du schéma réel avant de SELECTionner la colonne (un
     SELECT du modèle complet planterait en OperationalError sur une base
     pré-migration).
Tant que la colonne n'existe pas ou n'est pas peuplée, les réponses sont
comptées `language_unknown` et le rapport sort un avertissement au lieu de
planter. AUCUNE analyse DIF n'est possible sans C-0 — pas de backfill sur un
journal append-only.

Usage  : DATABASE_URL=... python scripts/analysis/dif_en_ar.py
                          [--strata N] [--min-per-group N]
Sortie : JSON sur stdout (aucune écriture en base — lecture seule).
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import inspect as sa_inspect, select
from sqlalchemy.orm import Session

from src.db import SessionLocal, make_engine
from src.engine.service import ELO_START
from src.models.measurement import Response, StudentCompetencyAbility

# Seuils ETS (échelle delta) et valeurs critiques (stdlib : pas de scipy).
ETS_MODERATE = 1.0          # |ΔMH| en dessous → A
ETS_LARGE = 1.5             # |ΔMH| au-dessus (et signif. > 1.0) → C
CHI2_CRIT_5PCT_1DF = 3.841  # χ²(1 ddl) à 5 %
Z_ONE_SIDED_5PCT = 1.645    # test unilatéral |ΔMH| > 1.0 pour la classe C

DEFAULT_STRATA = 10         # déciles d'ability
DEFAULT_MIN_PER_GROUP = 10  # réponses minimales par langue avant de juger un item

ACTIONS = {
    "A": "aucune",
    "B": "revue linguiste (comparaison EN/AR, correction du wording)",
    "C": "retrait du pool (quarantaine) + régénération",
}


def _normalize_language(raw: object) -> Optional[str]:
    """'en'/'ar' ou None — tolère Enum SQLAlchemy, str, NULL, valeur inattendue."""
    if raw is None:
        return None
    raw = getattr(raw, "value", raw)  # Enum → sa valeur ; str inchangée
    val = str(raw).strip().lower()
    return val if val in ("en", "ar") else None


def _language_column_in_db(s: Session) -> bool:
    """La colonne `language` existe-t-elle dans la table response de la BASE réelle ?

    DÉFENSIF C-0 : le modèle ORM peut déclarer `language` alors que la base
    interrogée n'est pas migrée — il faut inspecter le schéma réel, pas le modèle.
    """
    try:
        cols = sa_inspect(s.get_bind()).get_columns(Response.__tablename__)
        return any(c.get("name") == "language" for c in cols)
    except Exception:
        return False


def _decile_boundaries(values: List[float], strata: int) -> List[float]:
    """Bornes internes de strates équi-peuplées (len = strata-1, croissantes)."""
    ordered = sorted(values)
    n = len(ordered)
    return [ordered[(k * n) // strata] for k in range(1, strata)]


def mantel_haenszel(tables: List[Tuple[int, int, int, int]]) -> Optional[dict]:
    """MH sur des tables 2×2 (a=EN correct, b=EN incorrect, c=AR correct, d=AR incorrect).

    Retourne alpha_mh, delta_mh (ETS), se_delta (RBG), chi2 (correction de
    continuité) — ou None si l'odds ratio commun est indéfini (R ou S nul).
    """
    R = S = 0.0                 # numérateur / dénominateur de α_MH
    sum_a = sum_e = sum_v = 0.0  # χ² MH : Σa, ΣE[a], ΣVar(a)
    for a, b, c, d in tables:
        n = a + b + c + d
        if n == 0:
            continue
        R += a * d / n
        S += b * c / n
        n_en, n_ar = a + b, c + d
        m_ok, m_ko = a + c, b + d
        sum_a += a
        sum_e += n_en * m_ok / n
        if n > 1:
            sum_v += (n_en * n_ar * m_ok * m_ko) / (n * n * (n - 1))
    if R <= 0.0 or S <= 0.0:
        return None
    alpha = R / S
    # Variance RBG de ln(α_MH).
    t1 = t2 = t3 = 0.0
    for a, b, c, d in tables:
        n = a + b + c + d
        if n == 0:
            continue
        p, q = (a + d) / n, (b + c) / n
        rk, sk = a * d / n, b * c / n
        t1 += p * rk
        t2 += p * sk + q * rk
        t3 += q * sk
    var_ln = t1 / (2 * R * R) + t2 / (2 * R * S) + t3 / (2 * S * S)
    chi2 = ((abs(sum_a - sum_e) - 0.5) ** 2 / sum_v) if sum_v > 0 else 0.0
    delta = -2.35 * math.log(alpha)
    se_delta = 2.35 * math.sqrt(var_ln) if var_ln > 0 else float("inf")
    return {"alpha_mh": alpha, "delta_mh": delta, "se_delta": se_delta, "chi2": chi2}


def classify_ets(delta: float, se_delta: float, chi2: float) -> str:
    """Règle ETS A/B/C sur l'échelle delta."""
    magnitude = abs(delta)
    if magnitude < ETS_MODERATE or chi2 < CHI2_CRIT_5PCT_1DF:
        return "A"
    if (magnitude >= ETS_LARGE and math.isfinite(se_delta) and se_delta > 0
            and (magnitude - ETS_MODERATE) / se_delta > Z_ONE_SIDED_5PCT):
        return "C"
    return "B"


def run(s: Session, *, strata: int, min_per_group: int) -> dict:
    # Colonnes EXPLICITES (jamais select(Response) entier) : sur une base non
    # migrée C-0, le modèle complet référencerait une colonne inexistante.
    language_attr = getattr(Response, "language", None)  # défensif niveau modèle
    db_has_language = language_attr is not None and _language_column_in_db(s)
    cols = [Response.student_id, Response.competency_id,
            Response.item_id, Response.is_correct]
    if db_has_language:
        cols.append(language_attr)
    rows_raw = s.execute(select(*cols)).all()

    ability: Dict[tuple, float] = {
        (row.student_id, row.competency_id): row.ability_elo
        for row in s.execute(
            select(StudentCompetencyAbility.student_id,
                   StudentCompetencyAbility.competency_id,
                   StudentCompetencyAbility.ability_elo)
        )
    }

    # Réponses par item : (ability du répondant, langue, is_correct).
    by_item: Dict[object, list] = {}
    comp_of: Dict[object, object] = {}
    n_unknown = 0
    for row in rows_raw:
        lang = _normalize_language(row[4]) if db_has_language else None
        if lang is None:
            n_unknown += 1
            continue
        ab = ability.get((row.student_id, row.competency_id), ELO_START)
        by_item.setdefault(row.item_id, []).append((ab, lang, bool(row.is_correct)))
        comp_of[row.item_id] = row.competency_id

    items_out = []
    for item_id, rows in sorted(by_item.items(), key=lambda kv: str(kv[0])):
        n_en = sum(1 for _, lang, _ in rows if lang == "en")
        n_ar = len(rows) - n_en
        entry = {"item_id": str(item_id), "competency_id": str(comp_of[item_id]),
                 "n_en": n_en, "n_ar": n_ar}
        if n_en < min_per_group or n_ar < min_per_group:
            entry.update({"status": "insufficient",
                          "note": f"moins de {min_per_group} réponses dans une langue"})
            items_out.append(entry)
            continue
        bounds = _decile_boundaries([ab for ab, _, _ in rows], strata)
        tables = [[0, 0, 0, 0] for _ in range(strata)]  # a, b, c, d par strate
        for ab, lang, ok in rows:
            k = bisect.bisect_right(bounds, ab)
            idx = (0 if ok else 1) if lang == "en" else (2 if ok else 3)
            tables[k][idx] += 1
        mh = mantel_haenszel([tuple(t) for t in tables])
        if mh is None:
            entry.update({"status": "degenerate",
                          "note": "odds ratio commun indéfini (strates sans contraste)"})
            items_out.append(entry)
            continue
        ets = classify_ets(mh["delta_mh"], mh["se_delta"], mh["chi2"])
        entry.update({
            "status": "ok",
            "alpha_mh": round(mh["alpha_mh"], 4),
            "delta_mh": round(mh["delta_mh"], 3),
            "se_delta": round(mh["se_delta"], 3) if math.isfinite(mh["se_delta"]) else None,
            "chi2_mh": round(mh["chi2"], 3),
            "significant_5pct": mh["chi2"] >= CHI2_CRIT_5PCT_1DF,
            "favors": "en" if mh["delta_mh"] < 0 else "ar",  # signe ETS : Δ<0 défavorise le focal (AR)
            "ets_class": ets,
            "action": ACTIONS[ets],
        })
        items_out.append(entry)

    report = {
        "analysis": "dif_en_ar",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {"strata": strata, "min_per_group": min_per_group,
                   "ets_moderate": ETS_MODERATE, "ets_large": ETS_LARGE},
        "language_column_in_model": language_attr is not None,
        "language_column_present": db_has_language,  # présence dans la BASE interrogée
        "n_responses_total": len(rows_raw),
        "n_language_unknown": n_unknown,
        "n_items_analyzed": sum(1 for e in items_out if e.get("status") == "ok"),
        "counts_by_class": {
            c: sum(1 for e in items_out if e.get("ets_class") == c) for c in ("A", "B", "C")
        },
        "items": items_out,
    }
    if not db_has_language or (rows_raw and n_unknown == len(rows_raw)):
        report["warning"] = (
            "response.language absente (modèle ou base) ou vide — migration C-0 "
            "(Cadrage-LotC §3/C-0) non appliquée/alimentée sur la base interrogée : "
            "aucune analyse DIF possible sur ces données."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DIF EN/AR par item (Mantel-Haenszel, classification ETS A/B/C).")
    parser.add_argument("--strata", type=int, default=DEFAULT_STRATA,
                        help=f"nb de strates d'ability (défaut {DEFAULT_STRATA} = déciles)")
    parser.add_argument("--min-per-group", type=int, default=DEFAULT_MIN_PER_GROUP,
                        help=f"réponses minimales par langue et par item (défaut {DEFAULT_MIN_PER_GROUP})")
    args = parser.parse_args()

    with SessionLocal(bind=make_engine()) as s:
        report = run(s, strata=args.strata, min_per_group=args.min_per_group)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
