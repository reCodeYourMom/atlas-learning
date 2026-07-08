#!/usr/bin/env bash
# =====================================================================
# Atlas — déploiement prod EN UNE COMMANDE.
#   - crée .env depuis l'exemple si absent
#   - génère les secrets manquants (AUTH_SECRET, mots de passe, secret OIDC)
#   - SYNCHRONISE le secret OIDC realm↔.env automatiquement (fini le gotcha §4)
#   - construit le realm runtime (sans secret versionné) puis lève la stack
#
# Domaines : passe-les en variables d'env (recommandé pour Terraform/cloud-init) :
#   APP_DOMAIN=app.tondomaine AUTH_DOMAIN=auth.tondomaine ./deploy.sh
# Sinon, renseigne-les dans .env avant de relancer.
#
# Idempotent : relancer ne régénère pas les secrets déjà posés.
# =====================================================================
set -euo pipefail
cd "$(dirname "$0")"

gen() { python3 -c 'import secrets; print(secrets.token_urlsafe(48))'; }

# --- 1. .env ---------------------------------------------------------
if [ ! -f .env ]; then
  echo "[deploy] .env absent → copie depuis .env.prod.example"
  cp .env.prod.example .env
fi

set_var() {  # KEY VALUE — met à jour ou ajoute KEY=VALUE dans .env
  local key="$1" val="$2"
  if grep -qE "^${key}=" .env; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" .env && rm -f .env.bak
  else
    printf '%s=%s\n' "$key" "$val" >> .env
  fi
}
get_var() { grep -E "^$1=" .env | tail -n1 | cut -d= -f2- || true; }

ensure_secret() {  # remplace si vide ou encore en placeholder __REMPLACER…
  local key="$1" cur; cur="$(get_var "$key")"
  if [ -z "$cur" ] || [[ "$cur" == __REMPLACER* ]] || [[ "$cur" == CHANGE_ME* ]]; then
    set_var "$key" "$(gen)"; echo "[deploy]   secret généré : $key"
  fi
}

# Domaines fournis via env → on les écrit dans .env.
[ -n "${APP_DOMAIN:-}" ]  && set_var APP_DOMAIN  "$APP_DOMAIN"
[ -n "${AUTH_DOMAIN:-}" ] && set_var AUTH_DOMAIN "$AUTH_DOMAIN"

echo "[deploy] génération/contrôle des secrets…"
ensure_secret AUTH_SECRET
ensure_secret APP_DB_PASSWORD
ensure_secret KC_DB_PASSWORD
ensure_secret KC_ADMIN_PASSWORD
ensure_secret OIDC_GENERIC_CLIENT_SECRET
# Mot de passe INITIAL des comptes démo Keycloak : généré par instance (jamais
# versionné — revue adversariale 2026-07-07 : l'ancien mdp statique du template,
# publié dans le repo, permettait la course au premier login). temporary:true +
# UPDATE_PASSWORD dans le realm : Keycloak force son remplacement au 1er login.
ensure_secret DEMO_ACCOUNTS_PASSWORD

# --- 2. garde-fou domaines ------------------------------------------
APP_D="$(get_var APP_DOMAIN)"; AUTH_D="$(get_var AUTH_DOMAIN)"
if [[ "$APP_D" == *atlas.example ]] || [[ "$AUTH_D" == *atlas.example ]]; then
  echo "[deploy] ✗ Domaines encore en exemple ($APP_D / $AUTH_D)." >&2
  echo "         Renseigne APP_DOMAIN et AUTH_DOMAIN (env ou .env) puis relance." >&2
  exit 1
fi

# --- 3. realm runtime (secrets + domaine injectés, jamais versionnés) --
echo "[deploy] génération du realm Keycloak runtime…"
mkdir -p keycloak/import
OIDC_SECRET="$(get_var OIDC_GENERIC_CLIENT_SECRET)"
DEMO_PASSWORD="$(get_var DEMO_ACCOUNTS_PASSWORD)"
# redirectUris/webOrigins explicites (plus de wildcard) : dérivés d'APP_DOMAIN,
# même mécanisme de substitution que le secret client. Le mot de passe démo est
# injecté au même endroit : AUCUN credential en clair dans un fichier versionné.
sed -e "s|CHANGE_ME_atlas_kc_client_secret|${OIDC_SECRET}|" \
    -e "s|CHANGE_ME_demo_password|${DEMO_PASSWORD}|g" \
    -e "s|CHANGE_ME_app_domain|${APP_D}|g" \
  keycloak/atlas-realm.template.json > keycloak/import/atlas-realm.json
echo "[deploy]   → keycloak/import/atlas-realm.json (secret + mdp démo + redirectUris synchronisés)"

# --- 4. build + up ---------------------------------------------------
echo "[deploy] docker compose up -d --build…"
docker compose -f docker-compose.yml up -d --build

echo ""
echo "[deploy] ✓ stack lancée. Suivi des migrations + provision :"
echo "         docker compose logs -f backend"
echo "[deploy]   App : https://${APP_D}   ·   Auth : https://${AUTH_D}/admin"
echo "[deploy]   Comptes démo : admin@/prof@/parent@demo.atlas"
echo "[deploy]     mdp initial = DEMO_ACCOUNTS_PASSWORD dans .env (généré, jamais versionné)"
echo "[deploy]     au 1er login : changement de mdp FORCÉ (temporary) + enrôlement TOTP obligatoire"
echo "[deploy]   Données démo côté app : PROVISION_ON_BOOT=0 par défaut → mettre 1 dans .env pour les semer (cf. README §3)"
