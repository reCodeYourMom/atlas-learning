# Runbook — Provisioning beta prod ATLAS (OCI UAE)

Plan d'exécution **séquencé** pour la première mise en ligne réelle (pilote/beta), à dérouler
linéairement. Complète `README-DEPLOY.md` (référence) en **ordonnant** les prérequis sécurité/conformité
du §10 AU BON MOMENT du flux — la règle d'or : **aucune donnée réelle d'élève avant que les points
1→6 ne soient verts.**

Décisions déjà prises pour cette beta :
- **Rotation clé Groq : REPORTÉE après la beta** (clé dev réutilisée ; acceptable tant qu'aucune
  donnée sensible ne transite par la génération d'items — voir §7).
- **RETENTION_DAYS = 30** (base légale ci-dessous).
- **Backup off-box : OBLIGATOIRE** (free tier = DB auto-gérée, perte de VM = perte des données).

---

## Base légale de la rétention (RETENTION_DAYS = 30)

`RETENTION_DAYS` gouverne la **fenêtre de grâce entre soft-delete et purge dure** d'un élève
(désinscription roster, ou demande d'effacement), PAS la durée de conservation d'un élève actif.

- **Donnée active** : conservée pour la **durée du service contractualisé** avec l'école, effacée à
  la résiliation. Principe de limitation de conservation — **UAE PDPL** (Federal Decree-Law No. 45 de
  2021, art. 5 : donnée gardée uniquement le temps nécessaire à la finalité) ; **KSA PDPL** (SDAIA,
  destruction dès que la finalité ne l'exige plus) ; aligné sur RGPD art. 5(1)(e) souvent pris comme
  référence en B2B/B2G GCC.
- **Fenêtre de grâce post-soft-delete = 30 jours** : compromis défendable entre (a) l'obligation
  d'effacement « sans retard injustifié » du PDPL (30 j est le SLA de traitement communément retenu)
  et (b) le besoin opérationnel de récupération (désinscription accidentelle en cours de trimestre,
  litige, ré-inscription). Plus court fragilise la récupération ; plus long affaiblit la minimisation
  pour des données de **mineurs**.

**Confirmé par l'avis juridique (2026-07-08)** : 30 j défendable sous PDPL EAU (pas de safe-harbor
chiffré ; nécessité + limitation + mécanisme d'effacement), pas de durée min/max imposée pour les
mineurs. Formulation opérationnelle actée : **RETENTION_DAYS = 30 (maximum), suppression logique
immédiate, purge définitive automatique à J+30, sauf legal hold ou instruction documentée de
l'école-controller.**

Traduction en code (déjà en place, ne rien coder de plus) :
- **Plafond dur** : `purge_retention.py` **ramène** toute valeur `RETENTION_DAYS > 30` à 30 (la
  fenêtre ne peut pas être étendue par config).
- **Legal hold** : `scripts/legal_hold.py set|clear|list --student <id> | --school <id> --reason "…"`
  suspend la purge (par élève, ou tenant-large par école = instruction controller), audité. Un
  élève sous hold n'est jamais purgé, même au-delà de 30 j.
- **Suppression logique immédiate** : le soft-delete masque déjà l'élève de tous les endpoints
  (durcissement vague 2). **Purge auto J+30** : `retention.cron` lance `--execute` quotidiennement.

Poser `RETENTION_DAYS=30` explicitement dans le `.env` de la VM (§5). Faire déclarer l'école
**controller** dans le DPA (ATLAS = sous-traitant sur instruction). Puis appliquer les clauses par
juridiction ci-dessous.

### Conformité DPA par juridiction (avis juridique 2026-07-08 — clauses à intégrer)

**EAU — écoles publiques / B2G** : la PDPL fédérale (Decree-Law 45/2021) **exclut de son champ les
« Government Data » et les entités publiques**. Pour une école **publique** EAU, le DPA ne peut donc
PAS s'appuyer sur la seule PDPL fédérale : il doit renvoyer à la **gouvernance data du secteur public
de l'émirat**. À Dubaï = *Dubai Data Law* + Résolution n°2/2017, qui imposent une **classification**
(Open / Confidential / Sensitive / Secret) ; les données éducatives sont **au moins « Sensitive »**.
→ Clause DPA de **compliance locale** : l'école publique fournit la classification exacte de ses
données ET les **durées de rétention imposées par son autorité de tutelle** (KHDA à Dubaï, ADEK à Abu
Dhabi) — **celles-ci PRÉVALENT sur les 30 jours**.
- *Traduction technique* : si l'autorité impose une rétention **plus courte**, baisser `RETENTION_DAYS`
  (≤30, déjà supporté). Si elle impose un **archivage plus long** (obligation de conservation des
  relevés scolaires), poser un **legal hold école** (`legal_hold.py set --school`) qui suspend la purge
  — le hold est le mécanisme exact pour « conserver au-delà de 30 j sur obligation locale ». Une
  rétention **par tenant** (config par école plutôt qu'un env global) est un item roadmap si plusieurs
  écoles publiques aux régimes divergents coexistent sur une même instance.
- Réf. : u.ae/data-protection-laws ; garant.ae (PDPL FR).

**KSA — appendice données de mineurs (SDAIA)** : l'hébergement est en **Oracle Cloud EAU** ; tout accès
depuis la **KSA** = **traitement transfrontière** au sens saoudien. Pour un client KSA, ajouter un
**appendice DPA** intégrant la *Children and Incompetents' Data Protection Policy* de la SDAIA :
- l'école **obtient et conserve la preuve du consentement du tuteur légal** de l'élève mineur (sauf
  exceptions liées à la sécurité de l'enfant) et l'informe des finalités/méthodes de collecte ;
- **interdiction stricte de traitement automatisé à des fins de profilage ou de marketing direct**.
  → ATLAS est conforme *par conception* : le seul traitement automatisé est l'**évaluation
  pédagogique** (Elo), jamais du profilage marketing ni de la publicité — à **déclarer explicitement**
  dans l'appendice ;
- **stocker la donnée d'un résident saoudien hors du Royaume** (même dans le GCC) exige l'**approbation
  préalable des autorités saoudiennes** (règles de transfert transfrontière SDAIA). Deux voies, au choix
  du client : (a) l'école **documente cette approbation/exception** (contractuel, voie beta) ; ou (b)
  **anonymisation / tokenisation avant que la donnée ne quitte le territoire KSA** — **feature
  d'ingénierie lourde, NON implémentée, roadmap** à n'ouvrir que si un client KSA public/strict se
  confirme (l'archi actuelle héberge tout en clair côté EAU).
- Réf. : sdaia.gov.sa (PDPL + Children's Data Protection Policy) ; vision2030 (cadre gouvernance data).

> **Portée beta** : le pilote vise une école EAU (privée ou publique selon le client signé). L'appendice
> KSA ne s'active que pour un client saoudien — à ne pas bloquer la beta EAU. Aucun code KSA à livrer
> tant qu'aucun client KSA n'est confirmé ; le point (b) tokenisation est explicitement roadmap.

---

## Séquence d'exécution

### 0. Prérequis identité (toi seul)
- Compte OCI avec **home region = UAE** (`me-abudhabi-1` ou `me-dubai-1`) — **IRRÉVERSIBLE**, l'Always
  Free n'existe que dans la home region.
- Domaine + 2 sous-domaines `app.` / `auth.` (ou démarrer en `<IP>.nip.io` le temps d'en acheter un).
- Clé API OCI : Console → Profil → User settings → API Keys → *Add API Key* (fournit tenancy/user
  OCID + fingerprint + clé privée).
- Clé SSH ed25519 (`~/.ssh/id_ed25519.pub`).

### 1. CMK Vault AVANT la VM (chiffrement at-rest, données mineurs)
Le boot volume doit être chiffré avec une **Customer-Managed Key** créée **avant** le provisioning et
attachée à la création (le Terraform le gère désormais via `boot_kms_key_ocid` — pas de rétrofit).
1. Console OCI → **Identity & Security → Vault** → créer un Vault + une **AES Master Encryption Key**
   (Customer-Managed) dans la région UAE. Noter l'OCID de la clé.
2. Renseigner `boot_kms_key_ocid = "ocid1.key.oc1.me-abudhabi-1.xxxxx"` dans `terraform.tfvars`
   (déjà câblé dans `main.tf` → `source_details.kms_key_id`). Laisser vide = clé Oracle par défaut.
   > Rétrofit possible sinon via Console (Block Storage → boot volume → *Assign* la clé) mais il
   > re-chiffre le volume — l'option Terraform-à-la-création reste préférable.

### 2. Provisionner la VM (Terraform)
```bash
cd deploy/infra/oci
cp terraform.tfvars.example terraform.tfvars   # OCIDs + fingerprint + clé + domaines + (boot_kms_key_ocid si §1)
# ssh_ingress_cidr = "TON.IP/32" pour durcir le SSH ; region = home region UAE
# repo_url : LAISSER VIDE pour une beta (on copie le bundle à la main, pas de clone auto d'un repo public)
terraform init && terraform apply
terraform output          # → public_ip, commande ssh, étapes DNS
```
⚠️ Capacité A1 parfois tendue en EAU (« out of capacity ») : réessayer (autre AD / plus tard).
NSG/Security List : entrées **80**, **443**, et **22 restreint à ton IP**.

### 3. DNS
2 enregistrements **A** → `public_ip` : `app.<domaine>` et `auth.<domaine>` (ou `<IP>.nip.io`).
Caddy émettra le TLS Let's Encrypt au 1er accès HTTPS.

### 4. Déployer la stack
`repo_url` vide → copier le bundle et lancer `deploy.sh` :
```bash
scp -r atlas-learning ubuntu@<public_ip>:/home/ubuntu/
ssh ubuntu@<public_ip>
cd atlas-learning/deploy/prod
APP_DOMAIN=app.<domaine> AUTH_DOMAIN=auth.<domaine> ./deploy.sh
```
`deploy.sh` (idempotent) : crée `.env`, **génère les secrets manquants** (`AUTH_SECRET`, mots de passe
Postgres, `KC_ADMIN_PASSWORD`, `OIDC_GENERIC_CLIENT_SECRET`, `DEMO_ACCOUNTS_PASSWORD`), **synchronise**
le secret OIDC `.env` ↔ realm, génère `keycloak/import/` (gitignoré), `docker compose up -d --build`.
Le backend migre (`alembic upgrade head`) au boot.
```bash
docker compose logs -f backend    # suivre migrations 0001→0016
```
**`PROVISION_ON_BOOT=0`** (défaut) : aucune donnée démo en prod. Le realm crée quand même les 3 comptes
Keycloak `admin@ / prof@ / parent@demo.atlas`, mdp initial généré, **temporaire** (UPDATE_PASSWORD +
CONFIGURE_TOTP forcés au 1er login).

### 5. Config conformité dans le `.env` (AVANT toute vraie donnée)
```bash
grep -q '^RETENTION_DAYS=' .env || echo 'RETENTION_DAYS=30' >> .env   # base légale ci-dessus
# Email = OCI Email Delivery (SMTP). Coller les identifiants générés dans OCI (non ré-affichables) :
#   SMTP_HOST=smtp.email.me-abudhabi-1.oci.oraclecloud.com  SMTP_PORT=587
#   SMTP_USERNAME=<OCI>  SMTP_PASSWORD=<OCI>  EMAIL_FROM=no-reply@mail.atlaslearning.ae
# Sans SMTP_* → aucun lien magique n'est envoyé (parents ET linguistes).
docker compose up -d   # recharger l'env
```
`GROQ_API_KEY` : laisser la clé dev pour la beta (rotation post-beta, §7). Vide = OK sauf pour
générer/traduire des items (console arabe).

### 6. Installer les 3 crons (exploitation)
Tester chaque script en **dry-run** (défaut, ne modifie rien) AVANT de poser le cron :
```bash
docker compose exec backend python scripts/purge_retention.py     # dry-run : liste ce qui serait purgé
docker compose exec backend python scripts/run_quarantine.py      # dry-run : items candidats quarantaine
```
Puis `crontab -e` et coller les lignes de `backup.cron` (02:30, **off-box obligatoire** : exporter
`BACKUP_OS_BUCKET`/`BACKUP_OS_NAMESPACE` → OCI Object Storage via instance principal), `retention.cron`
(03:10) et `quarantine.cron` (03:40) — adapter le chemin absolu du bundle.

### 7. Smoke & vérification
```bash
API_BASE=https://app.atlaslearning.ae/api ./verify_deploy.sh
```
Le script vérifie : backend vivant (`/auth/providers`, public, sans DB), découverte OIDC du realm
`atlas`, HSTS posé par Caddy, redirection HTTP→HTTPS. Exit 0 = vert, 1 = au moins un check rouge.
Puis parcours login réel : `https://app.<domaine>` → « Continuer avec Atlas » → email + mdp démo
(`grep DEMO_ACCOUNTS_PASSWORD .env`) → **remplacement mdp imposé** → **QR TOTP** (Authy/Google
Authenticator) → session par rôle. Confirme que TOTP est bien exigé (preuve MFA staff sur données mineurs).

### 7bis. Onboarder le linguiste (validation arabe)
Aucun parcours self-service ne crée le compte staff `linguist` : le faire via le script dédié
(idempotent). Il crée le compte + le rôle global, et mint un lien magique single-use à transmettre
au linguiste (utile même si le SMTP n'est pas encore posé) :
```bash
docker compose exec backend python scripts/onboard_linguist.py --email linguiste@atlaslearning.ae
# → affiche le lien magique (valide 24 h, usage unique). --no-link si le SMTP est déjà en place
#   (le linguiste demandera son lien lui-même sur https://app.atlaslearning.ae/linguist/login).
```
Le linguiste ouvre le lien → confirme → arrive sur sa file (`/linguist`) : items en attente de
validation AR, les `ar_math_broken` en tête. Il corrige/valide/signale ; tout est audité.

### 8. Post-beta (dette assumée, à fermer avant scale)
- **Rotation clé Groq** : révoquer `gsk_...Wmaa` (console Groq), regénérer, poser la nouvelle
  uniquement dans le `.env` VM.
- **CI** : GitHub Actions en place (pytest + migrations sur Postgres réel + `ATLAS_TEST_PG_URL`
  dé-skippe le test de concurrence). Rien à faire ; surveiller que les runs restent verts.
- **Surveillance quarantaine** : après quelques jours de trafic, `run_quarantine.py` en dry-run,
  vérifier qu'aucun item sain n'est quarantainé ; ajuster `ITEM_BURN_IN` (défaut 20) si besoin.
- **Comm liens magiques** : les liens émis avant le durcissement sont invalidés (format jti) → prévoir
  la ligne FR/EN/AR « redemandez un lien via le parcours habituel ».

---

## Checklist go-live (tout doit être vert avant la 1re vraie donnée)
- [ ] Home region OCI = UAE (irréversible)
- [ ] CMK Vault créée et attachée au boot volume (§1)
- [ ] VM provisionnée, SSH restreint à ton IP, ports 80/443 ouverts
- [ ] DNS `app.`/`auth.` → IP, TLS Caddy émis
- [ ] `deploy.sh` OK, migrations 0001→0018 passées, `PROVISION_ON_BOOT=0`
- [ ] `RETENTION_DAYS=30` posé + reflété dans le DPA école (validé par le conseil)
- [ ] SMTP OCI posé (`SMTP_HOST/PORT/USERNAME/PASSWORD` + `EMAIL_FROM`) — liens magiques parents & linguistes
- [ ] 3 crons installés (backup **off-box** + retention + quarantine), dry-runs validés
- [ ] Smoke OK (health, issuer OIDC, HSTS) + login TOTP prouvé par rôle
