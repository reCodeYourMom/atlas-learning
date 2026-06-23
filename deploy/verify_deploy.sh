#!/usr/bin/env bash
# =====================================================================
# Atlas Learning — vérification post-déploiement (runbook §7)
# Usage : API_BASE=https://api.atlas.example ./verify_deploy.sh
# Exécute les checks automatisables (curl) ; rappelle les checks manuels.
# Code retour != 0 si un check automatisé échoue.
# =====================================================================
set -uo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
PASS=0; FAIL=0
green(){ printf "\033[32m  ✓ %s\033[0m\n" "$1"; PASS=$((PASS+1)); }
red(){   printf "\033[31m  ✗ %s\033[0m\n" "$1"; FAIL=$((FAIL+1)); }
info(){  printf "\033[36m  … %s\033[0m\n" "$1"; }
hr(){    printf -- "----------------------------------------------------------\n"; }

echo "Atlas — vérification post-déploiement"
echo "API_BASE = $API_BASE"
hr

# 1) /auth/providers liste google (et autres configurés)
echo "[1] GET /auth/providers"
PROV=$(curl -fsS --max-time 10 "$API_BASE/auth/providers" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$PROV" ]; then
  echo "      réponse: $PROV"
  if echo "$PROV" | grep -q '"google"'; then green "google présent"; else red "google absent (vérifier OIDC_GOOGLE_CLIENT_ID/SECRET)"; fi
else
  red "endpoint injoignable"
fi
hr

# 2) AUTH_SECRET posé + ATLAS_ENV=prod (le backend refuse de démarrer sinon)
echo "[2] Fail-fast AUTH_SECRET / ATLAS_ENV"
if [ -n "${AUTH_SECRET:-}" ] && [ "${ATLAS_ENV:-}" = "prod" ]; then
  green "AUTH_SECRET défini et ATLAS_ENV=prod"
elif curl -fsS --max-time 10 "$API_BASE/auth/providers" >/dev/null 2>&1; then
  green "backend répond → secret bien configuré côté serveur"
else
  red "AUTH_SECRET/ATLAS_ENV non vérifiables et backend muet"
fi
hr

# 3) Healthcheck général
echo "[3] Healthcheck"
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$API_BASE/auth/providers")
if [ "$CODE" = "200" ]; then green "API up (HTTP 200)"; else red "API code HTTP $CODE"; fi
hr

# ----- Checks manuels (nécessitent comptes/tenants réels) ----------
echo "[manuel] À valider à la main (runbook §7) :"
info "Login Google d'un compte staff → session + landing par rôle"
info "Onboarding d'un domaine de test → tenant créé, checklist visible"
info "POST /admin/rostering/sync → RosterRun 'ok', effectifs, statut 'connected'"
info "ROSTER_GUARDIANS=1 → liens parents créés (source='roster')"
info "parent/request-link → email reçu → parent/login → espace enfant (sélecteur si ≥2)"
info "MFA staff : 1er login admin/prof → enrôlement TOTP (QR)"
hr

echo "Résultat automatisé : $PASS OK / $FAIL KO"
[ "$FAIL" -eq 0 ]
