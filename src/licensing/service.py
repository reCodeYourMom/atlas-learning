"""Sièges / licence (Phase F) — capture du quota + détection de dépassement. Logique pure.

Choix produit : **alerte** plutôt que refus dur. Un dépassement est rendu visible et
facturable (statut `over_capacity` + message), sans casser l'établissement en cours d'année.
Le quota (`Organization.seats`) est un terme contractuel posé par le vendeur (SUPER_ADMIN) ;
`None` = illimité (essai).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.measurement import School, Student
from src.models.org import Organization, TenantIntegration

_OVER = "over_capacity"


def seat_usage(s: Session, org: Organization) -> dict:
    """Sièges contractés vs élèves actifs ; `over_by` > 0 si dépassement."""
    used = s.execute(
        select(func.count()).select_from(Student).where(
            Student.deleted_at.is_(None),
            Student.school_id.in_(select(School.id).where(School.organization_id == org.id)),
        )
    ).scalar() or 0
    seats = org.seats
    over_by = used - seats if (seats is not None and used > seats) else 0
    return {"seats": seats, "used": used, "over_by": over_by, "over": over_by > 0}


def flag_overage(s: Session, org: Organization) -> dict:
    """Reflète l'état de licence sur l'intégration (appelé après une sync)."""
    usage = seat_usage(s, org)
    integ = s.execute(
        select(TenantIntegration).where(TenantIntegration.organization_id == org.id)
    ).scalar_one_or_none()
    if integ is not None:
        if usage["over"]:
            integ.status = _OVER
            integ.last_error = (f"Dépassement de licence : {usage['used']}/{usage['seats']} "
                                f"sièges (+{usage['over_by']})")
        elif integ.status == _OVER:
            # repassé sous le quota → on rétablit l'état nominal
            integ.status, integ.last_error = "connected", None
    return usage


def set_seats(s: Session, org: Organization, seats: Optional[int]) -> Organization:
    """Pose/lève le quota contractuel (réservé au vendeur). `None` = illimité."""
    if seats is not None and seats < 0:
        raise ValueError("seats doit être positif ou nul")
    org.seats = seats
    return org
