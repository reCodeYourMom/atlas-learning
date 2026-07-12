"""CLI minimale de revue d'items (T2.3).

Sous-commandes :
  list                          liste les items à revoir (ai_generated)
  generate --code CODE [-n N]   génère via Groq + insère en ai_generated
  approve  ID  --reviewer NAME  ai_generated → human_reviewed
  reject   ID  --reviewer NAME --reason "..."   soft delete + raison
  review       --reviewer NAME  boucle interactive (a/r/s/q)

Cible = DATABASE_URL (SQLite dev par défaut). Pré-requis : alembic upgrade head.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.items.review import approve, insert_generated_items, list_pending, reject
from src.models.competency import Competency
from src.models.item import Item


def _fmt(item: Item) -> str:
    c = item.content_en
    return (f"{item.id}  [{item.context_tags}]\n"
            f"    Q: {c.get('stem')}\n"
            f"    options: {c.get('options')}\n"
            f"    answer: {c.get('answer')}")


def cmd_list(s, _args) -> None:
    pending = list_pending(s)
    if not pending:
        print("Aucun item à revoir.")
        return
    print(f"{len(pending)} item(s) à revoir :\n")
    for it in pending:
        print(_fmt(it), "\n")


def cmd_generate(s, args) -> None:
    from src.items.generation import generate_items
    from src.llm.client import GroqClient
    from src.models.base import AnswerFormat

    comp = s.execute(select(Competency).where(Competency.code == args.code)).scalar_one_or_none()
    if comp is None:
        print(f"Compétence '{args.code}' introuvable."); sys.exit(1)
    targets = [{"simplify": False}, {"simplify": True}][: max(1, args.n)]
    gen = generate_items(comp, targets, GroqClient(), answer_format=AnswerFormat.MCQ)
    items = insert_generated_items(s, gen)
    print(f"{len(items)} item(s) générés et insérés (ai_generated) pour {comp.code}.")


def _get(s, item_id: str) -> Item:
    item = s.get(Item, uuid.UUID(item_id))
    if item is None:
        print(f"Item {item_id} introuvable."); sys.exit(1)
    return item


def cmd_approve(s, args) -> None:
    approve(s, _get(s, args.id), reviewer=args.reviewer)
    print("Approuvé → human_reviewed.")


def cmd_reject(s, args) -> None:
    reject(s, _get(s, args.id), reviewer=args.reviewer, reason=args.reason)
    print("Rejeté (soft delete).")


def cmd_translate(s, args) -> None:
    from src.items.arabic import ALLAM_MODEL, translate_to_arabic
    from src.items.review import set_arabic
    from src.llm.client import GroqClient
    from src.models.base import AnswerFormat

    item = _get(s, args.id)
    ar = translate_to_arabic(item.content_en, GroqClient(model=ALLAM_MODEL),
                             answer_format=AnswerFormat.MCQ)
    set_arabic(s, item, ar, by=args.by)
    print(f"AR proposé (ALLaM) pour {item.id} :")
    import json as _j
    print(_j.dumps(ar, indent=2, ensure_ascii=False))


def cmd_validate_ar(s, args) -> None:
    from src.audit import log_action
    from src.items.review import validate_arabic
    item = _get(s, args.id)
    validate_arabic(s, item, linguist=args.linguist)
    log_action(s, action="item.ar_validated", resource_type="item", resource_id=item.id,
               details={"linguist": args.linguist})
    s.commit()
    print("AR validé → linguist_validated (éligible à active).")


def cmd_ar_pending(s, args) -> None:
    from src.items.arabic import ar_math_preserved
    from sqlalchemy import select as _select
    items = s.execute(
        _select(Item).where(Item.deleted_at.is_(None), Item.ar_validated.is_(False))
    ).scalars().all()
    pending = [it for it in items if it.content_ar]
    print(f"{len(pending)} item(s) AR en attente de validation linguiste :\n")
    for it in pending[: args.limit]:
        flag = "" if ar_math_preserved(it.content_en, it.content_ar) else "  ⚠️ MATH ALTÉRÉE"
        print(f"{it.id}{flag}\n    EN: {it.content_en.get('stem')}\n    AR: {it.content_ar.get('stem')}\n")


def cmd_review(s, args) -> None:
    pending = list_pending(s)
    if not pending:
        print("Aucun item à revoir."); return
    for it in pending:
        print("\n" + _fmt(it))
        choice = input("  [a]pprouver / [r]ejeter / [s]auter / [q]uitter ? ").strip().lower()
        if choice == "q":
            break
        if choice == "a":
            approve(s, it, reviewer=args.reviewer); print("  → human_reviewed")
        elif choice == "r":
            reason = input("  Raison du rejet : ").strip()
            reject(s, it, reviewer=args.reviewer, reason=reason); print("  → rejeté")
        else:
            print("  (sauté)")


def main() -> None:
    p = argparse.ArgumentParser(description="Revue d'items Atlas (T2.3)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(fn=cmd_list)

    g = sub.add_parser("generate"); g.add_argument("--code", required=True)
    g.add_argument("-n", type=int, default=2); g.set_defaults(fn=cmd_generate)

    a = sub.add_parser("approve"); a.add_argument("id"); a.add_argument("--reviewer", required=True)
    a.set_defaults(fn=cmd_approve)

    r = sub.add_parser("reject"); r.add_argument("id"); r.add_argument("--reviewer", required=True)
    r.add_argument("--reason", required=True); r.set_defaults(fn=cmd_reject)

    rv = sub.add_parser("review"); rv.add_argument("--reviewer", required=True)
    rv.set_defaults(fn=cmd_review)

    t = sub.add_parser("translate"); t.add_argument("id"); t.add_argument("--by", required=True)
    t.set_defaults(fn=cmd_translate)

    va = sub.add_parser("validate-ar"); va.add_argument("id"); va.add_argument("--linguist", required=True)
    va.set_defaults(fn=cmd_validate_ar)

    ap = sub.add_parser("ar-pending"); ap.add_argument("--limit", type=int, default=20)
    ap.set_defaults(fn=cmd_ar_pending)

    args = p.parse_args()
    with SessionLocal(bind=make_engine()) as s:
        args.fn(s, args)


if __name__ == "__main__":
    main()
