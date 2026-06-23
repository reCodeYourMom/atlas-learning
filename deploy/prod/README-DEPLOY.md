# Déploiement prod Atlas — 1 VM (OCI UAE), Docker, auth TOTP (Keycloak)

Stack auto-suffisante : **Caddy** (TLS auto) → **frontend** Next.js + **backend** FastAPI,
**Keycloak** (login + TOTP via Authy/Google Authenticator), **2 Postgres** (app GCC + Keycloak).
Auth = OIDC générique sur Keycloak (prouvé : id_token `aud=atlas-web` accepté par le backend).
Pas besoin de Google Workspace : le tenant + les comptes sont provisionnés au boot.

```
Caddy :443
 ├─ APP_DOMAIN        → frontend:3000   (+ /api/* → backend:8000, préfixe retiré)
 └─ AUTH_DOMAIN       → keycloak:8080   (issuer OIDC)
app-db (Postgres, données pédagogiques)   kc-db (Postgres Keycloak)
```

---

## 1. VM OCI (région UAE — résidence GCC)

- **Compute** Ubuntu 22.04, ≥ 2 vCPU / 4 Go RAM (Keycloak + 2 Postgres) — un *VM.Standard.A1.Flex*
  (Ampere, Always Free) 2 OCPU/12 Go convient bien.
- **Security List / NSG** : ouvrir **80** et **443** en entrée (et 22 pour SSH). Rien d'autre.
- Installer Docker + compose :
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER   # se reconnecter ensuite
  ```

## 2. DNS

Deux enregistrements **A** → IP publique de la VM :
```
app.tondomaine.com    → <IP_VM>
auth.tondomaine.com   → <IP_VM>
```
(Le TLS est émis automatiquement par Caddy via Let's Encrypt au 1er démarrage.)

## 3. Récupérer le bundle sur la VM

Copier le dossier `04_code/` (ou cloner le repo) sur la VM, puis :
```bash
cd 04_code/deploy/prod
cp .env.prod.example .env
```

## 4. Secrets (`.env`) — étape critique

Générer chaque secret : `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`

| Variable | Valeur |
|---|---|
| `APP_DOMAIN` / `AUTH_DOMAIN` | tes 2 sous-domaines (§2) |
| `AUTH_SECRET` | secret HMAC (obligatoire, fail-fast prod) |
| `APP_DB_PASSWORD` / `KC_DB_PASSWORD` | mots de passe Postgres |
| `KC_ADMIN_PASSWORD` | console admin Keycloak (`https://AUTH_DOMAIN/admin`) |
| `OIDC_GENERIC_CLIENT_SECRET` | **doit être IDENTIQUE** au `secret` du client dans `keycloak/atlas-realm.json` |

> ⚠️ **Synchroniser le secret du client OIDC.** Avant le 1er boot, remplace
> `CHANGE_ME_atlas_kc_client_secret` dans `keycloak/atlas-realm.json` **ET** mets la même
> valeur dans `OIDC_GENERIC_CLIENT_SECRET` du `.env`. Sinon l'échange de code échoue.

## 5. Lancer

```bash
docker compose up -d --build
docker compose logs -f backend     # voir migrations + provision (récupère les IDs école/classe/enfant)
```
Le backend migre (`alembic upgrade head`) et provisionne le tenant démo + les 4 mouvements
(`PROVISION_ON_BOOT=1`). Idempotent : un redémarrage ne duplique rien.

## 6. Comptes & TOTP (Authy / Google Authenticator)

Le realm crée 3 comptes, mot de passe temporaire `ChangeMe1234!`, **TOTP requis au 1er login** :
`admin@demo.atlas` (admin pédago) · `prof@demo.atlas` (enseignant) · `parent@demo.atlas` (parent).

1. Ouvre `https://APP_DOMAIN` → bouton **« Continuer avec Atlas »** → page Keycloak.
2. Saisis l'email + `ChangeMe1234!` → Keycloak demande de **scanner le QR** avec Authy/Google
   Authenticator → entre le code à 6 chiffres → session Atlas ouverte, redirigée par rôle.
3. (Reco) Change les mots de passe par défaut dans la console Keycloak admin.

Pour ajouter d'autres utilisateurs : console Keycloak (`https://AUTH_DOMAIN/admin`, realm *atlas*) —
crée l'user **et** l'email correspondant doit exister côté app (provision ou liaison staff).

## 7. Vérification

```bash
API_BASE=https://APP_DOMAIN/api ./verify_deploy.sh
```
Puis le parcours produit, par rôle (les IDs viennent des logs de provision, §5) :

| Mouvement | Écran |
|---|---|
| M01 digest hebdo | `prof@` → `/teacher/<classroom>` (bannière « Cette semaine » + lacune émergente) |
| M01 action 10 min | `parent@` → `/parent/<child>` (carte maison, sans score) + bloc anti-compulsion |
| M02 console arabe | `admin@` → `/admin/<school>/arabic` (couverture 6/9, 3 en attente → Proposer/Valider) |
| M03 surfaces preuve | `admin@` → `/admin/<school>/report` (avant 33 % → après 67 %) |
| M04 tuteur causal | `prof@` → fiche élève → « Pourquoi cet exercice ? » |

## 8. Exploitation

- **Sauvegardes** : `docker exec atlas-app-db-1 pg_dump -U atlas atlas | gzip > backup.sql.gz` (cron).
- **Logs** : `docker compose logs -f <service>`.
- **Mise à jour** : `git pull && docker compose up -d --build`.
- **Sync nocturne rostering** (si Google branché plus tard) : cron `scripts/roster_sync.py` (cf. Runbook §6).

## 9. Gotchas

- **Keycloak derrière proxy** : `KC_HOSTNAME=https://AUTH_DOMAIN` + `KC_PROXY_HEADERS=xforwarded`
  (déjà posés). Si boucle de redirection https, vérifier que Caddy transmet `X-Forwarded-Proto`.
- **GROQ_API_KEY** vide = OK (démo) ; requis seulement pour *générer/traduire* des items (console arabe « Proposer »).
- **POSTMARK_TOKEN** vide = aucun email (liens magiques parents non envoyés) ; brancher Postmark/Resend pour la prod réelle.
- **Données réelles** : passer `PROVISION_ON_BOOT=0` une fois le tenant pilote en place pour ne plus injecter la démo.
