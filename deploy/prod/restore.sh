#!/usr/bin/env bash
# =====================================================================
# Atlas — restauration d'une base depuis un dump produit par backup.sh.
# Les dumps sont en `pg_dump --clean --if-exists` : ils suppriment puis
# recréent les objets, donc la restauration est rejouable.
#
# Usage :
#   ./restore.sh app       [chemin.sql.gz]   # défaut = dernier dump 'app'
#   ./restore.sh keycloak  [chemin.sql.gz]   # défaut = dernier dump 'keycloak'
#
# ⚠ Écrase les données de la base ciblée. À faire stack arrêtée côté lecteurs
#   (idéalement : couper backend/keycloak avant un restore en prod).
# =====================================================================
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.yml"
TARGET="${1:?usage: ./restore.sh <app|keycloak> [fichier.sql.gz]}"
OUT_DIR="${BACKUP_DIR:-./backups}"

case "$TARGET" in
  app)      SVC="app-db";  DB="atlas"
            USER="${APP_DB_USER:-atlas}"
            [ -f .env ] && USER="$(grep -E '^APP_DB_USER=' .env | tail -n1 | cut -d= -f2- || true)"
            USER="${USER:-atlas}" ;;
  keycloak) SVC="kc-db";   DB="keycloak"; USER="keycloak" ;;
  *) echo "cible inconnue: $TARGET (attendu: app|keycloak)" >&2; exit 2 ;;
esac

FILE="${2:-$(ls -1t "$OUT_DIR/${TARGET}-"*.sql.gz 2>/dev/null | head -n1 || true)}"
[ -n "$FILE" ] && [ -f "$FILE" ] || { echo "aucun dump trouvé pour '$TARGET'" >&2; exit 1; }

echo "[restore] $TARGET ← $FILE"
read -r -p "Confirmer l'écrasement de la base '$DB' ? [oui/N] " ans
[ "$ans" = "oui" ] || { echo "annulé."; exit 0; }

gunzip -c "$FILE" | $COMPOSE exec -T "$SVC" psql -U "$USER" -d "$DB"
echo "[restore] terminé."
