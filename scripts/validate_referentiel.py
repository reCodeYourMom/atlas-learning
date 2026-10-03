"""Contrôles A1.7 d'un ou plusieurs référentiels — rejouables par un tiers, sans base.

Jusqu'ici la méthodologie annonçait un « scan
automatique du JSON », mais densité, chaîne HARD, monotonie des priors, bornes de poids et
répartition cognitive étaient calculés à la main et recopiés dans les dossiers de revue.
Ce script les calcule. Il est fait pour la CI et pour le dossier de revue A1.8.

Usage :
  python scripts/validate_referentiel.py                                  # fractions (défaut)
  python scripts/validate_referentiel.py --referentiel data/referentiel_fractions.json \\
      --referentiel data/referentiel_decimals_draft.json       # graphe combiné
  python scripts/validate_referentiel.py --strict                          # avertissements = erreurs
  python scripts/validate_referentiel.py --json                            # sortie machine

Chaque fichier est contrôlé avec les codes des AUTRES fichiers comme codes externes (les
ponts inter-domaines sont légitimes et comptés à part, E5), puis le graphe COMBINÉ est
testé sans cycle. Code de sortie ≠ 0 = build fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graph.validator import check_referentiel, has_cycle

DEFAULT = Path(__file__).resolve().parents[1] / "data" / "referentiel_fractions.json"


def run(paths, *, strict: bool = False) -> dict:
    loaded = {str(p): json.loads(Path(p).read_text(encoding="utf-8")) for p in paths}
    codes_of = {k: {n["code"] for n in v.get("nodes", [])} for k, v in loaded.items()}
    out = {"files": {}, "combined": {}, "ok": True}
    for k, data in loaded.items():
        external = set().union(*(c for kk, c in codes_of.items() if kk != k)) if len(loaded) > 1 else set()
        rep = check_referentiel(data, external_codes=frozenset(external), strict=strict)
        out["files"][k] = rep.as_dict()
        out["ok"] = out["ok"] and rep.ok
    all_edges = [e for d in loaded.values() for e in d.get("edges", [])]
    all_codes = set().union(*codes_of.values()) if codes_of else set()
    # S5 : chaque domaine doit être relié aux autres par au moins un pont (dans un sens ou
    # l'autre — les ponts sont déclarés dans le fichier du domaine aval). Vérifié sur le
    # graphe combiné, car un fichier seul ne voit pas les ponts entrants.
    if len(loaded) > 1:
        for k, mine in codes_of.items():
            touche = any((e[0] in mine) != (e[1] in mine) for e in all_edges
                         if e[0] in all_codes and e[1] in all_codes)
            if not touche:
                out["files"][k]["warnings"].append(
                    "W-BRIDGE : aucun pont avec les autres domaines (S5) — "
                    "la propagation ne circulera pas entre domaines")
                if strict:
                    out["files"][k]["errors"].append("(strict) W-BRIDGE")
                    out["files"][k]["ok"] = False
                    out["ok"] = False
    unresolved = sorted({c for e in all_edges for c in e[:2] if c not in all_codes})
    cyclic = has_cycle([e for e in all_edges if e[0] in all_codes and e[1] in all_codes])
    out["combined"] = {"n_nodes": len(all_codes), "n_edges": len(all_edges),
                       "unresolved_codes": unresolved, "has_cycle": cyclic}
    if cyclic or unresolved:
        out["ok"] = False
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--referentiel", action="append", type=Path,
                    help="JSON {nodes, edges[, meta]} — répétable (graphe combiné)")
    ap.add_argument("--strict", action="store_true", help="avertissements traités en erreurs")
    ap.add_argument("--json", action="store_true", help="sortie JSON (CI)")
    args = ap.parse_args()
    paths = args.referentiel or [DEFAULT]
    out = run(paths, strict=args.strict)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for k, rep in out["files"].items():
            st = rep["stats"]
            print(f"\n{k}")
            print(f"  {st['n_nodes']} nœuds · {st['n_edges']} arêtes "
                  f"({st['n_intra']} intra, {st['n_bridges']} ponts) · "
                  f"densité intra {st['density_intra']} / totale {st['density_total']}")
            print(f"  cognitif {st['cognitive']} · médianes de prior {st['prior_median_by_grade']}")
            print(f"  racines {st['roots']}")
            print(f"  plus longue chaîne HARD ({len(st['longest_hard_chain'])} nœuds) : "
                  + " → ".join(c.split('.')[-1] for c in st['longest_hard_chain']))
            for w in rep["warnings"]:
                print(f"  ! {w}")
            for e in rep["errors"]:
                print(f"  ✗ {e}")
        c = out["combined"]
        print(f"\nGraphe combiné : {c['n_nodes']} nœuds, {c['n_edges']} arêtes, "
              f"cycle={c['has_cycle']}, codes non résolus={c['unresolved_codes']}")
        print("\nOK" if out["ok"] else "\nÉCHEC")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
