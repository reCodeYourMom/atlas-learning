"""Synchronise le rostering de tous les tenants connectés (cible cron nocturne).

Usage   : DATABASE_URL=... GOOGLE_SA_KEY_FILE=... python scripts/roster_sync.py
Cron ex.: 0 2 * * *  cd /app/04_code && python scripts/roster_sync.py >> /var/log/roster.log 2>&1

Pré-requis prod : google-auth installé + clé service account + app Marketplace installée
par chaque IT admin (délégation domain-wide).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import SessionLocal, make_engine
from src.rostering import google as gdir
from src.rostering.scheduler import sync_all


def _google_factory(integ):
    return gdir.build_from_env(integ.admin_email, integ.customer_id)


def main():
    with SessionLocal(bind=make_engine()) as s:
        results = sync_all(s, _google_factory)
    if not results:
        print("Aucun tenant connecté à synchroniser.")
        return
    for r in results:
        print(f"[{r.status:5s}] org={r.organization_id}  {r.summary}")


if __name__ == "__main__":
    main()
