#!/usr/bin/env bash
# Entrypoint backend : migrations à la volée, provision optionnelle, puis uvicorn.
# Idempotent : `alembic upgrade head` ne rejoue pas les migrations déjà appliquées,
# et le provision est sans effet si le tenant existe déjà.
set -euo pipefail

echo "[entrypoint] alembic upgrade head…"
alembic upgrade head

if [ "${PROVISION_ON_BOOT:-0}" = "1" ]; then
  echo "[entrypoint] provision tenant + données démo (PROVISION_ON_BOOT=1)…"
  python scripts/provision_prod_tenant.py || echo "[entrypoint] provision: déjà en place ou non bloquant"
fi

echo "[entrypoint] démarrage uvicorn :8000"
exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
