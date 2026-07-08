#!/usr/bin/env bash
# =====================================================================
# Atlas — smoke de déploiement (README §7). Vérifie qu'une stack fraîche
# répond correctement, SANS toucher aux données. À lancer après deploy.sh.
#
#   API_BASE=https://app.atlaslearning.ae/api ./verify_deploy.sh
#   # AUTH_BASE déduit de API_BASE si non fourni (app.<d> → auth.<d>) ;
#   # sinon : AUTH_BASE=https://auth.atlaslearning.ae ./verify_deploy.sh
#
# Codes de sortie : 0 = tout vert, 1 = au moins un check rouge.
# =====================================================================
set -uo pipefail

API_BASE="${API_BASE:-}"
if [ -z "$API_BASE" ]; then
  echo "✗ API_BASE requis (ex: API_BASE=https://app.atlaslearning.ae/api $0)" >&2
  exit 2
fi
API_BASE="${API_BASE%/}"                       # retire un éventuel slash final

# APP_BASE = API_BASE sans le suffixe /api (pour tester HSTS sur le front).
APP_BASE="${API_BASE%/api}"

# AUTH_BASE : fourni, sinon dérivé du front (app.<domaine> → auth.<domaine>).
if [ -z "${AUTH_BASE:-}" ]; then
  AUTH_BASE="$(printf '%s' "$APP_BASE" | sed -E 's#//app\.#//auth.#')"
fi
AUTH_BASE="${AUTH_BASE%/}"

fail=0
pass() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; fail=1; }

echo "Atlas — vérification déploiement"
echo "  API_BASE=$API_BASE"
echo "  AUTH_BASE=$AUTH_BASE"
echo

# 1) Backend vivant : /auth/providers est public, sans DB ni effet de bord.
echo "[1] Backend (/auth/providers)"
if body="$(curl -fsS --max-time 15 "$API_BASE/auth/providers" 2>/dev/null)" \
   && printf '%s' "$body" | grep -q '"providers"'; then
  pass "backend répond, JSON providers OK"
else
  bad "backend injoignable ou réponse inattendue sur $API_BASE/auth/providers"
fi

# 2) Issuer OIDC Keycloak (realm atlas) : la découverte .well-known doit exposer un issuer.
echo "[2] Keycloak (issuer OIDC realm atlas)"
wk="$AUTH_BASE/realms/atlas/.well-known/openid-configuration"
if disc="$(curl -fsS --max-time 15 "$wk" 2>/dev/null)" \
   && printf '%s' "$disc" | grep -q '"issuer"'; then
  pass "découverte OIDC OK ($wk)"
else
  bad "pas de découverte OIDC sur $wk (Keycloak pas prêt ? realm 'atlas' importé ?)"
fi

# 3) HSTS actif sur le front (en-tête posé par Caddy — durcissement revue 2026-07).
echo "[3] En-têtes sécurité (HSTS sur le front)"
if curl -fsSI --max-time 15 "$APP_BASE/" 2>/dev/null \
   | grep -iq '^strict-transport-security:'; then
  pass "Strict-Transport-Security présent"
else
  bad "HSTS absent sur $APP_BASE/ (Caddy security_headers non appliqués ?)"
fi

# 4) Redirection HTTP→HTTPS (Caddy). Non bloquant : on avertit seulement.
echo "[4] Redirection HTTP→HTTPS (info)"
http_url="http://${APP_BASE#https://}"
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$http_url/" 2>/dev/null)"
code="${code:-000}"
case "$code" in
  30[0-9]) pass "HTTP redirige ($code)";;
  *)       printf '  \033[33m!\033[0m HTTP a répondu %s (attendu 3xx) — vérifier si non bloquant\n' "$code";;
esac

echo
if [ "$fail" -eq 0 ]; then
  echo -e "\033[32mSmoke OK.\033[0m Poursuivre par le login TOTP par rôle (RUNBOOK-BETA §7)."
  exit 0
else
  echo -e "\033[31mSmoke ÉCHOUÉ.\033[0m Voir les ✗ ci-dessus (logs : docker compose logs -f)."
  exit 1
fi
