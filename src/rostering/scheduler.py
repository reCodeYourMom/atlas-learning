"""Planification du rostering (Phase D) — fonction pure, déclenchable par cron.

Pas de scheduler en process (fragile en serverless) : un cron nocturne appelle
`scripts/roster_sync.py`, qui appelle `sync_all`. Idempotent — relancer est sans risque.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.base import ensure_utc
from src.models.org import Organization, TenantIntegration

_SYNCABLE = ("connected", "pending")  # on (re)tente aussi les pending (1re sync post-install)


@dataclass
class TenantSyncResult:
    organization_id: str
    status: str        # ok | error
    summary: str


def sync_all(
    s: Session,
    directory_factory: Callable,
    *,
    now: Optional[datetime] = None,
    due_before: Optional[datetime] = None,
) -> List[TenantSyncResult]:
    """Synchronise tous les tenants connectés. `due_before` : ignore ceux déjà syncés après.

    Une erreur sur un tenant est isolée (tracée sur son intégration) et n'arrête pas les autres.
    """
    from src.rostering.sync import sync_directory  # import local : évite tout cycle

    due_before = ensure_utc(due_before)  # naïf accepté (tests) → réinterprété UTC

    integs = s.execute(
        select(TenantIntegration).where(TenantIntegration.status.in_(_SYNCABLE))
    ).scalars().all()

    results: List[TenantSyncResult] = []
    for integ in integs:
        # ensure_utc : last_sync_at relu de SQLite est naïf (convention UTC).
        if due_before and integ.last_sync_at and ensure_utc(integ.last_sync_at) >= due_before:
            continue  # déjà à jour sur cette fenêtre
        org = s.get(Organization, integ.organization_id)
        if org is None or org.deleted_at is not None:
            continue
        try:
            run = sync_directory(s, org, directory_factory(integ).snapshot(), now=now)
            s.commit()
            results.append(TenantSyncResult(str(org.id), run.status, run.summary))
        except Exception as exc:  # un tenant en échec n'interrompt pas la tournée
            s.rollback()
            integ.status, integ.last_error = "error", str(exc)[:500]
            s.commit()
            results.append(TenantSyncResult(str(org.id), "error", str(exc)[:200]))
    return results
