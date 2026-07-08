"""Pose / lève un LEGAL HOLD sur un élève ou une école (avis juridique 2026-07-08).

Un legal hold suspend la purge de rétention (scripts/purge_retention.py) : un élève sous
hold — propre, ou hérité d'une école sous hold tenant-large — n'est JAMAIS purgé, même
soft-deleted au-delà de RETENTION_DAYS. À utiliser sur instruction documentée du
controller (l'école) ou en cas de litige / obligation de conservation.

Chaque pose/levée est journalisée dans AuditLog (append-only). La `reason` est
obligatoire à la pose (traçabilité juridique).

Usage :
  DATABASE_URL=... python scripts/legal_hold.py set   --student <uuid> --reason "litige #123"
  DATABASE_URL=... python scripts/legal_hold.py set   --school  <uuid> --reason "instruction controller 2026-07"
  DATABASE_URL=... python scripts/legal_hold.py clear --student <uuid>
  DATABASE_URL=... python scripts/legal_hold.py list
"""
import argparse
import sys
import uuid
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.audit import log_action
from src.db import SessionLocal, make_engine
from src.models.base import utcnow
from src.models.measurement import School, Student


def _target(s: Session, args):
    """Retourne (model_name, obj, school_id_pour_audit) ou lève SystemExit."""
    if bool(args.student) == bool(args.school):
        raise SystemExit("Préciser EXACTEMENT un de --student / --school.")
    if args.student:
        obj = s.get(Student, uuid.UUID(args.student))
        if obj is None:
            raise SystemExit(f"élève {args.student} introuvable")
        return "student", obj, obj.school_id
    obj = s.get(School, uuid.UUID(args.school))
    if obj is None:
        raise SystemExit(f"école {args.school} introuvable")
    return "school", obj, obj.id


def set_hold(s: Session, args) -> None:
    kind, obj, school_id = _target(s, args)
    obj.legal_hold = utcnow()
    obj.legal_hold_reason = args.reason
    log_action(s, action="legal_hold.set", school_id=school_id,
               resource_type=kind, resource_id=obj.id,
               details={"reason": args.reason})
    s.commit()
    print(f"[posé] legal hold sur {kind} {obj.id} — « {args.reason} »")


def clear_hold(s: Session, args) -> None:
    kind, obj, school_id = _target(s, args)
    if obj.legal_hold is None:
        print(f"[no-op] {kind} {obj.id} n'était pas sous hold")
        return
    obj.legal_hold = None
    obj.legal_hold_reason = None
    log_action(s, action="legal_hold.clear", school_id=school_id,
               resource_type=kind, resource_id=obj.id, details={})
    s.commit()
    print(f"[levé] legal hold retiré de {kind} {obj.id}")


def list_holds(s: Session, _args) -> None:
    schools = s.execute(select(School).where(School.legal_hold.is_not(None))).scalars().all()
    students = s.execute(select(Student).where(Student.legal_hold.is_not(None))).scalars().all()
    for sc in schools:
        print(f"  école   {sc.id} depuis {sc.legal_hold.isoformat()} — « {sc.legal_hold_reason} »")
    for st in students:
        print(f"  élève   {st.id} depuis {st.legal_hold.isoformat()} — « {st.legal_hold_reason} »")
    if not schools and not students:
        print("  (aucun legal hold posé)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Legal hold (suspend la purge de rétention).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name, fn, needs_reason in (("set", set_hold, True), ("clear", clear_hold, False)):
        p = sub.add_parser(name)
        p.add_argument("--student", type=str, default=None)
        p.add_argument("--school", type=str, default=None)
        p.add_argument("--reason", type=str, default=None,
                       required=needs_reason, help="motif (obligatoire à la pose)")
        p.set_defaults(fn=fn)
    sub.add_parser("list").set_defaults(fn=list_holds)

    args = parser.parse_args()
    with SessionLocal(bind=make_engine()) as s:
        args.fn(s, args)


if __name__ == "__main__":
    main()
