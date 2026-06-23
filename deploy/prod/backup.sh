#!/usr/bin/env bash
# =====================================================================
# Atlas — sauvegarde des 2 Postgres (app GCC + Keycloak).
# - pg_dump via `docker compose exec` (socket local = pas de mot de passe)
# - gzip + horodatage UTC
# - rotation locale (BACKUP_KEEP, défaut 14)
# - upload OFF-BOX optionnel vers OCI Object Storage (instance principal,
#   AUCUNE clé sur le disque) si BACKUP_OS_BUCKET est défini.
#
# Usage :  ./backup.sh
# Cron   :  voir backup.cron (quotidien 02:30).
# =====================================================================
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.yml"
TS="$(date -u +%Y%m%d-%H%M%SZ)"
OUT_DIR="${BACKUP_DIR:-./backups}"
KEEP="${BACKUP_KEEP:-14}"
mkdir -p "$OUT_DIR"

# Identifiants (depuis .env si présent), avec valeurs par défaut du compose.
APP_DB_USER="${APP_DB_USER:-atlas}"
[ -f .env ] && APP_DB_USER="$(grep -E '^APP_DB_USER=' .env | tail -n1 | cut -d= -f2- || true)"
APP_DB_USER="${APP_DB_USER:-atlas}"

dump() {  # <service> <db_user> <db_name> <label>
  local svc="$1" user="$2" db="$3" label="$4"
  local file="$OUT_DIR/${label}-${TS}.sql.gz"
  echo "[backup] dump $label ($svc/$db)…"
  $COMPOSE exec -T "$svc" pg_dump -U "$user" -d "$db" --clean --if-exists \
    | gzip -9 > "$file"
  echo "[backup]   → $file ($(du -h "$file" | cut -f1))"
  upload "$file"
}

upload() {  # <file> — off-box vers Object Storage si configuré
  local file="$1"
  [ -n "${BACKUP_OS_BUCKET:-}" ] || return 0
  if ! command -v oci >/dev/null 2>&1; then
    echo "[backup]   ⚠ oci CLI absent, upload off-box ignoré" >&2; return 0
  fi
  local ns_arg=()
  [ -n "${BACKUP_OS_NAMESPACE:-}" ] && ns_arg=(--namespace "$BACKUP_OS_NAMESPACE")
  echo "[backup]   upload → os://${BACKUP_OS_BUCKET}/$(basename "$file")"
  oci os object put --auth instance_principal \
    --bucket-name "$BACKUP_OS_BUCKET" "${ns_arg[@]}" \
    --file "$file" --name "atlas/$(basename "$file")" \
    --force >/dev/null
}

dump app-db "$APP_DB_USER" atlas    app
dump kc-db  keycloak      keycloak  keycloak

# Rotation locale : ne garder que les KEEP plus récents par label.
for label in app keycloak; do
  ls -1t "$OUT_DIR/${label}-"*.sql.gz 2>/dev/null | tail -n +$((KEEP+1)) | xargs -r rm -f
done

echo "[backup] OK — $(ls -1 "$OUT_DIR"/*.sql.gz 2>/dev/null | wc -l | tr -d ' ') fichiers locaux conservés."
