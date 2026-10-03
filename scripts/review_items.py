"""CLI de revue d'items (T2.3) — AUTHENTIFIÉE et AUDITÉE (revue 2026-09-20).

Sous-commandes :
  list                                  items à revoir (ai_generated)
  generate --code CODE [-n N]           génère via Groq + insère en ai_generated
  approve  ID  --reviewer EMAIL         ai_generated → human_reviewed
  reject   ID  --reviewer EMAIL --reason "..."   soft delete + raison
  review       --reviewer EMAIL         boucle interactive (a/r/s/q)
  translate ID --by EMAIL               propose l'AR (ALLaM) — repose ar_validated=False
  validate-ar ID --linguist EMAIL       human_reviewed → linguist_validated (gate G3)
  ar-pending [--limit N]                file AR en attente
  activate  ID|--all-validated --reviewer EMAIL   linguist_validated → active (pool servi)
  release   ID --reviewer EMAIL --reason "..."    quarantined → active (réhabilitation)

Identité : `--reviewer` / `--linguist` / `--by` sont l'EMAIL d'un compte existant portant
le rôle requis (content_reviewer ou super_admin pour la revue EN et l'activation ;
linguist ou super_admin pour l'arabe). Un texte libre est refusé : la trace en
`provenance` ET dans `audit_log` (user_id) pointe vers une personne identifiée.
Onboarding : `scripts/onboard_linguist.py --email ... [--role content_reviewer]`.

Cible = DATABASE_URL (SQLite dev par défaut). Pré-requis : alembic upgrade head.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.audit import log_action
from src.db import SessionLocal, make_engine
from src.items.review import (
    approve, insert_generated_items, list_pending, promote, promote_to_active, reject,
)
from src.models.base import ItemStatus, Role
from src.models.competency import Competency
from src.models.item import Item
from src.models.org import AppUser, Membership

CONTENT_ROLES = (Role.CONTENT_REVIEWER, Role.SUPER_ADMIN)
ARABIC_ROLES = (Role.LINGUIST, Role.SUPER_ADMIN)


def resolve_actor(s, email: str, roles) -> AppUser:
    """Email → compte ACTIF portant l'un des rôles. Sort en erreur sinon (pas de texte libre)."""
    email = (email or "").strip().lower()
    if "@" not in email:
        print(f"Identité requise : un EMAIL de compte (reçu {email!r}). "
              f"Rôles acceptés : {', '.join(r.value for r in roles)}.")
        sys.exit(2)
    user = s.execute(select(AppUser).where(AppUser.email == email)).scalar_one_or_none()
    if user is None or user.deleted_at is not None or not user.is_active:
        print(f"Compte {email} inconnu ou inactif."); sys.exit(2)
    ok = s.execute(select(Membership).where(Membership.user_id == user.id,
                                            Membership.role.in_(list(roles)))).first()
    if ok is None:
        print(f"{email} n'a aucun des rôles requis ({', '.join(r.value for r in roles)}). "
              "Onboarding : scripts/onboard_linguist.py --email ... --role <rôle>")
        sys.exit(2)
    return user


def _audit(s, action: str, actor: AppUser, item: Item, **details) -> None:
    log_action(s, action=action, user_id=actor.id, resource_type="item", resource_id=item.id,
               details={"actor": actor.email, "status": item.status.value, **details})


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
    actor = resolve_actor(s, args.reviewer, CONTENT_ROLES)
    item = approve(s, _get(s, args.id), reviewer=actor.email)
    _audit(s, "item.approve", actor, item); s.commit()
    print("Approuvé → human_reviewed.")


def cmd_reject(s, args) -> None:
    actor = resolve_actor(s, args.reviewer, CONTENT_ROLES)
    item = reject(s, _get(s, args.id), reviewer=actor.email, reason=args.reason)
    _audit(s, "item.reject", actor, item, reason=args.reason); s.commit()
    print("Rejeté (soft delete).")


def cmd_activate(s, args) -> None:
    """linguist_validated → active. Le SEUL point d'entrée de production vers le pool servi."""
    actor = resolve_actor(s, args.reviewer, CONTENT_ROLES)
    if args.all_validated:
        items = s.execute(select(Item).where(Item.status == ItemStatus.LINGUIST_VALIDATED,
                                             Item.deleted_at.is_(None))).scalars().all()
    elif args.id:
        items = [_get(s, args.id)]
    else:
        print("Préciser un ID ou --all-validated."); sys.exit(2)
    n = 0
    for it in items:
        promote_to_active(s, it, reviewer=actor.email)
        _audit(s, "item.activate", actor, it); n += 1
    s.commit()
    print(f"{n} item(s) activé(s) → pool servi.")


def cmd_release(s, args) -> None:
    """quarantined → active, avec raison. Réhabilitation tracée (jusqu'ici sans procédure)."""
    actor = resolve_actor(s, args.reviewer, CONTENT_ROLES)
    item = _get(s, args.id)
    if item.status != ItemStatus.QUARANTINED:
        print(f"L'item est {item.status.value}, pas quarantined."); sys.exit(1)
    promote(s, item, ItemStatus.ACTIVE, reviewer=actor.email)
    prov = dict(item.provenance or {}); prov.update(released=True, release_reason=args.reason)
    item.provenance = prov
    _audit(s, "item.release", actor, item, reason=args.reason); s.commit()
    print("Réhabilité → active.")


def cmd_translate(s, args) -> None:
    from src.items.arabic import ALLAM_MODEL, translate_to_arabic
    from src.items.review import set_arabic
    from src.llm.client import GroqClient
    from src.models.base import AnswerFormat

    actor = resolve_actor(s, args.by, ARABIC_ROLES)
    item = _get(s, args.id)
    ar = translate_to_arabic(item.content_en, GroqClient(model=ALLAM_MODEL),
                             answer_format=AnswerFormat.MCQ)
    set_arabic(s, item, ar, by=actor.email)
    _audit(s, "item.ar_proposed", actor, item); s.commit()
    print(f"AR proposé (ALLaM) pour {item.id} :")
    import json as _j
    print(_j.dumps(ar, indent=2, ensure_ascii=False))


def cmd_validate_ar(s, args) -> None:
    from src.items.review import validate_arabic
    actor = resolve_actor(s, args.linguist, ARABIC_ROLES)
    item = _get(s, args.id)
    validate_arabic(s, item, linguist=actor.email)
    _audit(s, "item.ar_validated", actor, item)
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
    actor = resolve_actor(s, args.reviewer, CONTENT_ROLES)
    pending = list_pending(s)
    if not pending:
        print("Aucun item à revoir."); return
    for it in pending:
        print("\n" + _fmt(it))
        choice = input("  [a]pprouver / [r]ejeter / [s]auter / [q]uitter ? ").strip().lower()
        if choice == "q":
            break
        if choice == "a":
            approve(s, it, reviewer=actor.email); _audit(s, "item.approve", actor, it); s.commit()
            print("  → human_reviewed")
        elif choice == "r":
            reason = input("  Raison du rejet : ").strip()
            reject(s, it, reviewer=actor.email, reason=reason)
            _audit(s, "item.reject", actor, it, reason=reason); s.commit()
            print("  → rejeté")
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

    ac = sub.add_parser("activate"); ac.add_argument("id", nargs="?")
    ac.add_argument("--all-validated", action="store_true")
    ac.add_argument("--reviewer", required=True); ac.set_defaults(fn=cmd_activate)

    rl = sub.add_parser("release"); rl.add_argument("id"); rl.add_argument("--reviewer", required=True)
    rl.add_argument("--reason", required=True); rl.set_defaults(fn=cmd_release)

    args = p.parse_args()
    with SessionLocal(bind=make_engine()) as s:
        args.fn(s, args)


if __name__ == "__main__":
    main()
