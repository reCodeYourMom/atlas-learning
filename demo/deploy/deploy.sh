#!/usr/bin/env bash
# =====================================================================
# Atlas — déploiement de la DÉMO en une commande.
#
#   DEMO_DOMAIN=demo.atlaslearning.ae ./deploy.sh
#
# Crée .env si absent, génère les secrets manquants, construit et lève la stack.
# Idempotent : relancer ne régénère aucun secret déjà posé (le mot de passe de démo
# resterait donc le même — c'est voulu, on ne veut pas le réapprendre à chaque déploiement).
# =====================================================================
set -euo pipefail
cd "$(dirname "$0")"

gen() { python3 -c 'import secrets; print(secrets.token_urlsafe(36))'; }
# Mot de passe TAPÉ À LA MAIN en visio : lisible, sans caractère ambigu (ni O/0 ni l/1),
# assez long pour ne pas être deviné. Un token base64 de 48 octets serait intapable.
gen_pwd() {
  python3 -c "import secrets; a='abcdefghijkmnpqrstuvwxyz'; A=a.upper().replace('I',''); d='23456789'; \
print('Atlas-' + ''.join(secrets.choice(a+A+d) for _ in range(10)))"
}

if [ ! -f .env ]; then
  echo "[demo] .env absent → copie depuis .env.demo.example"
  cp .env.demo.example .env
fi

set_var() {
  local key="$1" val="$2"
  if grep -qE "^${key}=" .env; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" .env && rm -f .env.bak
  else
    printf '%s=%s\n' "$key" "$val" >> .env
  fi
}
get_var() { grep -E "^$1=" .env | tail -n1 | cut -d= -f2- || true; }

[ -n "${DEMO_DOMAIN:-}" ] && set_var DEMO_DOMAIN "$DEMO_DOMAIN"

ensure() {  # KEY GENERATEUR — remplit si vide ou encore en placeholder
  local key="$1" fn="$2" cur; cur="$(get_var "$key")"
  if [ -z "$cur" ] || [[ "$cur" == __REMPLACER* ]]; then
    set_var "$key" "$($fn)"; echo "[demo]   généré : $key"
  fi
}
ensure AUTH_SECRET gen
ensure APP_DB_PASSWORD gen
ensure DEMO_LOGIN_PASSWORD gen_pwd

DOM="$(get_var DEMO_DOMAIN)"
if [ -z "$DOM" ] || [[ "$DOM" == *example* ]] || [[ "$DOM" == __REMPLACER* ]]; then
  echo "[demo] ERREUR : DEMO_DOMAIN n'est pas renseigné dans .env." >&2
  echo "       Relance : DEMO_DOMAIN=demo.atlaslearning.ae ./deploy.sh" >&2
  exit 1
fi

# Garde-fou DNS : Caddy demande un certificat à Let's Encrypt dès le boot. Si le A record
# ne pointe pas encore ici, la demande échoue ET compte dans le quota LE (5 échecs/heure
# par domaine) — on perdrait l'heure suivante. Mieux vaut refuser tout de suite.
ip_vm="$(curl -fsS --max-time 10 https://api.ipify.org 2>/dev/null || echo '')"
ip_dns="$(getent hosts "$DOM" 2>/dev/null | awk '{print $1}' | head -1 || echo '')"
if [ -n "$ip_vm" ] && [ -n "$ip_dns" ] && [ "$ip_vm" != "$ip_dns" ]; then
  echo "[demo] ATTENTION : $DOM pointe vers $ip_dns, or cette VM est en $ip_vm." >&2
  echo "       Corrige le DNS avant de continuer, sinon Let's Encrypt échouera." >&2
  read -r -p "       Continuer quand même ? [y/N] " r; [ "$r" = "y" ] || exit 1
elif [ -z "$ip_dns" ]; then
  echo "[demo] ATTENTION : $DOM ne résout pas encore. La propagation DNS peut prendre"
  echo "       quelques minutes ; si Caddy échoue, relance simplement ce script."
fi

echo "[demo] construction et démarrage (première fois : ~5 min)…"
docker compose up -d --build

echo
echo "═══════════════════════════════════════════════════════════════"
echo "  https://$DOM"
echo "═══════════════════════════════════════════════════════════════"
echo "  Mot de passe des 5 comptes : $(get_var DEMO_LOGIN_PASSWORD)"
echo
echo "  director@alnoor.demo     vue école"
echo "  teacher.c@alnoor.demo    la classe qui décroche"
echo "  teacher.a@alnoor.demo    la classe en avance"
echo "  teacher.b@alnoor.demo"
echo "  student049@alnoor.demo   session live"
echo
echo "  Le semis initial tourne au premier boot (~40 s) :"
echo "    docker compose logs -f backend"
echo "  Remise à zéro entre deux rendez-vous :  ./reset.sh"
echo "═══════════════════════════════════════════════════════════════"
