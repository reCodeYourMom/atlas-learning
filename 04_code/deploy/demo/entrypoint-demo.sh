#!/usr/bin/env bash
# Entrypoint backend de la stack DÉMO : migrations, puis semis au premier boot.
#
# Le semis est conditionné à une base VIDE (aucune école de démo). Un redémarrage de la VM
# ou un `docker compose up` de routine ne doit RIEN réécrire : si l'école est là, on démarre
# directement. Pour repartir de zéro entre deux rendez-vous, c'est ./reset.sh qui décide.
set -euo pipefail

echo "[demo] alembic upgrade head…"
alembic upgrade head

deja_seede() {
  python - <<'PY'
import sys
from sqlalchemy import select
from src.db import SessionLocal, make_engine
from src.models.measurement import School
with SessionLocal(bind=make_engine()) as s:
    existe = s.execute(
        select(School).where(School.name == "Al Noor International School")
    ).scalar_one_or_none() is not None
sys.exit(0 if existe else 1)
PY
}

if [ "${DEMO_SEED_ON_BOOT:-1}" = "1" ] && ! deja_seede; then
  echo "[demo] base vide → semis complet (aucun appel réseau, ~40 s)"
  python scripts/seed_referentiel.py
  python scripts/generate_bank_deterministic.py
  python scripts/translate_bank_ar_deterministic.py
  python scripts/provision_demo.py --bank-only
  python scripts/seed_demo_school.py
  echo "[demo] semis terminé."
else
  echo "[demo] école de démo déjà présente — aucun semis."
fi

echo "[demo] démarrage uvicorn :8000"
exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
