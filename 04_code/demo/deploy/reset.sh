#!/usr/bin/env bash
# Remise à zéro du jeu de démo ENTRE DEUX RENDEZ-VOUS. À lancer sur la VM.
#
#   cd demo/deploy && ./reset.sh
#
# Ne touche ni au référentiel ni à la banque d'items (invariants, déjà en base) : seule
# l'école de démo est reconstruite — élèves, réponses, mesures, diagnostics. C'est ce qu'un
# rendez-vous salit, et rien d'autre. Reconstruire la banque en plus ferait perdre ~20 s
# pour un résultat identique.
#
# Le seed efface son école avant de la recréer, il est donc rejouable à l'infini.
set -euo pipefail
cd "$(dirname "$0")"

debut=$(date +%s)
echo "▸ reconstruction du jeu de démo…"
docker compose exec -T backend python demo/seed_demo_school.py

# Filet : si la banque avait été vidée, le seed s'arrête tout seul avec un message clair.
echo
echo "✓ terminé en $(( $(date +%s) - debut )) s"
echo
echo "Mot de passe des comptes : voir DEMO_LOGIN_PASSWORD dans demo/deploy/.env"
