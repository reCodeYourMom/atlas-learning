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

## 0. Prérequis (à faire par toi — identité + domaine)

Deux choses ne peuvent venir que de toi :

1. **Compte OCI** (carte bancaire + identité requises à l'inscription, même pour l'Always Free).
   ⚠️ **Choisis la home region = UAE (`me-dubai-1` ou `me-abudhabi-1`) à la création : elle est
   IRRÉVERSIBLE, et l'Always Free n'existe que dans la home region.** Mauvais choix = plus de free en EAU.
2. **Un domaine** (2 sous-domaines : `app.` + `auth.`). Pas encore de domaine ? Démarre en
   `<IP_VM>.nip.io` (gratuit, résout vers l'IP) le temps d'en acheter un.

> 💡 Deux chemins ensuite : **(A) automatisé** via Terraform (`deploy/infra/oci/`, §1bis) qui crée la
> VM + le réseau + lance le déploiement ; **(B) manuel** (§1→§5). Les deux aboutissent au même résultat.

## 1. VM OCI (région UAE — résidence GCC)

- **Compute** Ubuntu 22.04 sur *VM.Standard.A1.Flex* (Ampere, **Always Free**). Plafond free =
  **2 OCPU / 12 Go total** (réduit depuis ~15 juin 2026, avant 4/24). On dimensionne pile au plafond.
  Les limites mémoire du compose (≈ 4 Go cumulés) tiennent largement dans 12 Go.
- ⚠️ **Capacité A1** parfois tendue en EAU : si le provisioning échoue (« out of capacity »), réessaie
  (autre AD, ou plus tard). C'est le seul aléa réel du free tier.
- **Security List / NSG** : ouvrir **80** et **443** en entrée (et 22 pour SSH, idéalement restreint à ton IP).
- Installer Docker + compose :
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER   # se reconnecter ensuite
  ```

## 1bis. Chemin automatisé (Terraform — recommandé)

Provisionne VM + réseau + déploiement en une fois depuis `deploy/infra/oci/` :

```bash
cd deploy/infra/oci
cp terraform.tfvars.example terraform.tfvars   # renseigner OCIDs + clé API + domaines
terraform init && terraform apply
```
La clé API OCI se génère dans : **Console OCI → Profil → User settings → API Keys → Add API Key**
(elle fournit tenancy/user OCID + fingerprint + la clé privée). `terraform output` donne l'IP publique
et les étapes DNS. Si `repo_url` est renseigné, cloud-init clone et lance `deploy.sh` tout seul.

## 2. DNS

Deux enregistrements **A** → IP publique de la VM :
```
app.tondomaine.com    → <IP_VM>
auth.tondomaine.com   → <IP_VM>
```
(Le TLS est émis automatiquement par Caddy via Let's Encrypt au 1er démarrage.)

## 3. Déploiement (chemin manuel — une commande)

Copier le dépôt (`atlas-learning/`) sur la VM, puis :
```bash
cd atlas-learning/deploy/prod
APP_DOMAIN=app.tondomaine.com AUTH_DOMAIN=auth.tondomaine.com ./deploy.sh
```

`deploy.sh` fait tout, de façon **idempotente** :
- crée `.env` depuis l'exemple si absent ;
- **génère les secrets manquants** (`AUTH_SECRET`, mots de passe Postgres, `KC_ADMIN_PASSWORD`,
  `OIDC_GENERIC_CLIENT_SECRET`) — relancer ne les régénère pas ;
- **synchronise automatiquement** le secret OIDC entre `.env` et le realm Keycloak (fini le gotcha
  de l'ancien §4 : plus de copier-coller manuel de `CHANGE_ME_…`). Le realm runtime est généré dans
  `keycloak/import/` (gitignoré) depuis `keycloak/atlas-realm.template.json` — **aucun secret versionné** ;
- lance `docker compose up -d --build`.

```bash
docker compose logs -f backend     # voir migrations + provision (récupère les IDs école/classe/enfant)
```
Le backend migre (`alembic upgrade head`) au boot. **`PROVISION_ON_BOOT=0` par défaut** : en prod
on ne sème jamais la démo. Pour une instance de **démonstration** uniquement, mettre
`PROVISION_ON_BOOT=1` dans `.env` (crée tenant démo + 4 mouvements, idempotent) puis remettre `0`
avant d'accueillir de vraies données élèves.

> Secrets gérés par `deploy.sh` : `AUTH_SECRET` (HMAC sessions), `APP_DB_PASSWORD`/`KC_DB_PASSWORD`,
> `KC_ADMIN_PASSWORD` (console `https://AUTH_DOMAIN/admin`), `OIDC_GENERIC_CLIENT_SECRET`,
> `DEMO_ACCOUNTS_PASSWORD` (mdp initial des 3 comptes démo, cf. §6). Tu peux les
> éditer à la main dans `.env` si tu préfères les fournir toi-même.

## 6. Comptes & TOTP (Authy / Google Authenticator)

Le realm crée 3 comptes : `admin@demo.atlas` (admin pédago) · `prof@demo.atlas` (enseignant) ·
`parent@demo.atlas` (parent). Leur mot de passe initial est **généré par `deploy.sh`**
(`DEMO_ACCOUNTS_PASSWORD` dans `.env` — jamais versionné, plus de mot de passe public dans le
repo) et il est **réellement temporaire** : Keycloak force son **remplacement au 1er login**
(`UPDATE_PASSWORD`), puis l'**enrôlement TOTP** (`CONFIGURE_TOTP`).

1. Récupère le mot de passe : `grep DEMO_ACCOUNTS_PASSWORD .env` (sur la VM).
2. Ouvre `https://APP_DOMAIN` → bouton **« Continuer avec Atlas »** → page Keycloak.
3. Saisis l'email + le mot de passe → Keycloak **impose un nouveau mot de passe**, puis demande
   de **scanner le QR** avec Authy/Google Authenticator → code à 6 chiffres → session Atlas
   ouverte, redirigée par rôle.

Pour ajouter d'autres utilisateurs : console Keycloak (`https://AUTH_DOMAIN/admin`, realm *atlas*) —
crée l'user **et** l'email correspondant doit exister côté app (provision ou liaison staff).
**TOTP realm-level** : `CONFIGURE_TOTP` est une *required action* par défaut du realm
(`defaultAction: true`) — TOUT nouvel utilisateur (dont les vrais comptes du pilote créés via la
console) devra enrôler un TOTP à son 1er login, pas seulement les 3 comptes démo.

## 7. Vérification

```bash
API_BASE=https://APP_DOMAIN/api ./verify_deploy.sh
```
Puis le parcours produit, par rôle (les IDs viennent des logs de provision, §5 —
nécessite une instance de démo avec `PROVISION_ON_BOOT=1`, cf. §3) :

| Mouvement | Écran |
|---|---|
| M01 digest hebdo | `prof@` → `/teacher/<classroom>` (bannière « Cette semaine » + lacune émergente) |
| M01 action 10 min | `parent@` → `/parent/<child>` (carte maison, sans score) + bloc anti-compulsion |
| M02 console arabe | `linguist@` → `/linguist` (file de validation AR : corriger → valider). L'admin d'école ne lit que la couverture (`GET /admin/arabic/coverage`) : proposer/valider l'arabe est un acte de staff Atlas, jamais d'un client. |
| M03 surfaces preuve | `admin@` → `/admin/<school>/report` (avant 33 % → après 67 %) |
| M04 tuteur causal | `prof@` → fiche élève → « Pourquoi cet exercice ? » |

## 8. Exploitation

- **Sauvegardes (off-box)** : `./backup.sh` dumpe les **2 bases** (app + Keycloak), gzip, rotation
  locale (`BACKUP_KEEP`, défaut 14). Pour copier hors-VM, exporte `BACKUP_OS_BUCKET` (+
  `BACKUP_OS_NAMESPACE`) → upload vers **OCI Object Storage via instance principal** (aucune clé sur
  le disque). Planifie avec `backup.cron` (quotidien 02:30). Restauration : `./restore.sh app|keycloak`.
  > ⚠️ Le free tier = **DB auto-gérée** : sans cette sauvegarde off-box, une perte de VM = perte des
  > données élèves. C'est le seul vrai risque « pérenne » à couvrir avant un pilote réel.
- **Purge de rétention (PDPL)** : `scripts/purge_retention.py` supprime durement les élèves
  soft-deleted depuis plus de `RETENTION_DAYS` (défaut 30) + les jti de liens magiques expirés.
  **Dry-run par défaut** ; purge réelle via `--execute` ; chaque purge journalisée dans AuditLog.
  Planifie avec `retention.cron` (quotidien 03:10) — à installer **à côté de `backup.cron`**.
- **Quarantaine des items dérivants** : `scripts/run_quarantine.py` (dry-run par défaut,
  `--execute`, réversible via review.promote). Planifie avec `quarantine.cron` (quotidien 03:40).
- **Installation des 3 crons** (`backup.cron` + `retention.cron` + `quarantine.cron`) :
  `crontab -e` sur la VM et coller les lignes de chaque fichier (adapter le chemin du bundle).
- **Logs** : `docker compose logs -f <service>`.
- **Mise à jour** : `git pull && ./deploy.sh`.
- **Sync nocturne rostering** (si Google branché plus tard) : cron `scripts/roster_sync.py` (modèle : `roster_sync.cron`, cf. Runbook §6).

## 9. Gotchas

- **Keycloak derrière proxy** : `KC_HOSTNAME=https://AUTH_DOMAIN` + `KC_PROXY_HEADERS=xforwarded`
  (déjà posés). Si boucle de redirection https, vérifier que Caddy transmet `X-Forwarded-Proto`.
- **GROQ_API_KEY** vide = OK (démo) ; requis seulement pour *générer/traduire* des items (console arabe « Proposer »).
- **POSTMARK_TOKEN** vide = aucun email (liens magiques parents non envoyés) ; brancher Postmark/Resend pour la prod réelle.
- **Données réelles** : `PROVISION_ON_BOOT=0` est le défaut — la démo n'est injectée que si tu
  passes explicitement à `1` (cf. §3), et il faut remettre `0` ensuite.
- **Compte smoke `test@demo.atlas`** : **retiré du realm prod** (revue sécu 2026-07-07 — mdp connu,
  sans TOTP, avec ROPC = contournement du SSO). Il ne vit plus que dans le realm de dérisquage local
  (`keycloak/derisk/atlas-realm.derisk.json`, importé uniquement par `docker-compose.keycloak.yml`).
  Ne le réintroduis jamais dans `atlas-realm.template.json`.
- **Client OIDC prod** : `directAccessGrantsEnabled=false` (pas de password grant) et
  `redirectUris`/`webOrigins` **explicites**, dérivés d'`APP_DOMAIN` par `deploy.sh` (plus de wildcard).
- **Realm** : le secret OIDC n'est plus dans `keycloak/atlas-realm.json` (renommé en
  `atlas-realm.template.json`). Ne réintroduis pas de secret en clair dans un fichier versionné ;
  `deploy.sh` génère `keycloak/import/` (gitignoré) à chaque déploiement.
- **Harnais de dérisquage** (`docker-compose.keycloak.yml`) : Keycloak en mode `start` (plus de
  `start-dev`) et credentials admin **obligatoires** via `KC_ADMIN_USER`/`KC_ADMIN_PASSWORD`/
  `KC_DB_PASSWORD` — le compose échoue explicitement s'ils manquent (fini `admin/admin`).

## 10. Prérequis pilote (sécurité / conformité — à faire AVANT de vraies données élèves)

1. **Chiffrement at-rest avec CMK (OCI Vault)** : aujourd'hui les emails (parents/staff) sont
   stockés **en clair** en base. Mitigation infra à activer côté OCI : créer un Vault + une
   *Customer-Managed Key*, puis chiffrer les volumes block/boot de la VM avec cette CMK
   (Console OCI → Block Storage → volume → *Assign* la clé du Vault). Sans ça, un snapshot de
   disque expose les emails.
2. **Rotation de la clé Groq** : la clé actuelle vit dans le `.env` **local** de dev (jamais
   commitée, mais active). La **rotater** (console Groq → révoquer + regénérer) avant le pilote,
   et ne poser la nouvelle que dans le `.env` de la VM.
3. **Rétention des données mineurs** : la purge automatisée est **livrée**
   (`scripts/purge_retention.py` : dry-run par défaut, `--execute` pour purger, fenêtre
   `RETENTION_DAYS` — défaut 30 jours, journalisation AuditLog). **À brancher en cron avant le
   pilote** : installer `retention.cron` (cf. §8) et aligner `RETENTION_DAYS` sur la durée de
   rétention promise aux écoles.
