# Démo sur `demo.atlaslearning.ae`

Stack minimale pour les rendez-vous écoles : Caddy (TLS auto) → Next.js + FastAPI →
Postgres. **Ni Keycloak ni sa base** — la démo se connecte par mot de passe partagé, le SSO
réel étant hors périmètre.

```
Caddy :443  ─┬─ /api/*  → backend:8000   (préfixe retiré)
             └─ /*      → frontend:3000
                          app-db (Postgres)
```

## La landing page n'est pas touchée

`atlaslearning.ae` et `www.` sont servis par Netlify et le restent. On n'ajoute **qu'un
enregistrement A** pour `demo.`, et Caddy ne demande un certificat que pour ce
sous-domaine — d'où l'absence de `includeSubDomains` sur le HSTS : depuis un sous-domaine,
cette directive engagerait tout le domaine, Netlify compris.

## 1. DNS (chez le registrar du domaine)

Un seul enregistrement à ajouter :

| Type | Nom    | Valeur             | TTL |
|------|--------|--------------------|-----|
| A    | `demo` | `<IP de la VM>`    | 3600 |

Ne touche à aucune autre ligne. Vérifier la propagation avant de déployer :

```bash
dig +short demo.atlaslearning.ae      # doit renvoyer l'IP de la VM
```

> Caddy demande son certificat dès le premier boot. Si le DNS ne pointe pas encore ici, la
> demande échoue **et consomme le quota Let's Encrypt** (5 échecs par heure et par domaine).
> `deploy.sh` refuse donc de partir sur un DNS incohérent — laisse-le faire.

## 2. La VM — Oracle Cloud, région Émirats

`deploy/infra/oci/` provisionne tout (VM + réseau + déploiement) sur l'Always Free d'Oracle
en région Émirats. Gratuit à vie, et **les données restent dans le Golfe** — ce qui se dit
en rendez-vous.

À faire une seule fois, et seulement par toi (identité) :

1. **Créer le compte OCI.** ⚠ La *home region* est **irréversible** : choisir
   `me-abudhabi-1` (UAE Central) ou `me-dubai-1`. L'Always Free n'existe que dans la home
   region — se tromper, c'est perdre la gratuité aux Émirats.
2. **Générer une clé API** : Console → Profil → *User settings* → *API Keys* → *Add API
   Key*. Le bloc de configuration affiché donne `tenancy_ocid`, `user_ocid` et
   `fingerprint`&nbsp;; la clé privée se télécharge à ce moment-là.

Puis :

```bash
cd deploy/infra/oci
cp terraform.tfvars.example terraform.tfvars   # renseigner les OCIDs, deploy_profile="demo"
terraform init && terraform apply
terraform output next_steps                    # l'IP et l'enregistrement DNS exact
```

> **Capacité ARM.** Le shape `VM.Standard.A1.Flex` est parfois saturé aux Émirats
> (« out of capacity »). C'est le seul aléa réel du free tier : réessayer plus tard, ou
> viser un autre *availability domain*. Rien à corriger dans la configuration.

### Ou n'importe quelle autre VM

Docker et les ports 80/443 ouverts suffisent. Compter **2 vCPU / 4 Go** (la stack en
réserve ~2,5 Go).

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && exec su -l $USER
```

## 3. Déploiement

```bash
git clone <repo> && cd atlas-learning/04_code/deploy/demo
DEMO_DOMAIN=demo.atlaslearning.ae ./deploy.sh
```

Le script génère les secrets manquants, dont un mot de passe **tapable en visio**
(ex. `Atlas-hK7mqRt2xv` — ni O/0 ni l/1), construit les images et lève la stack. Le semis
initial — référentiel, 300 items, version arabe, école de démo, 6 semaines d'historique —
tourne au premier boot en ~40 s, **sans aucun appel réseau**.

```bash
docker compose logs -f backend     # suivre le semis
```

## 4. Entre deux rendez-vous

```bash
cd deploy/demo && ./reset.sh
```

Reconstruit l'école — élèves, réponses, mesures, diagnostics — en ~35 s. Le référentiel et
la banque d'items ne sont pas retouchés : ce sont des invariants, un rendez-vous ne les
salit pas.

## 5. Les comptes

Même mot de passe pour tous, affiché par `deploy.sh` et conservé dans `.env` sur la VM
(jamais versionné). Les cinq premiers font le parcours vendu ; les trois suivants existent
pour qu'aucun écran du produit ne soit inatteignable si la question vient (revue
2026-09-20 : parent, IT admin et linguiste n'étaient pas semés, et leurs liens magiques
partent dans le vide sans SMTP).

| Compte | Ce qu'il ouvre |
|---|---|
| `director@alnoor.demo` | Vue école — étape 1 du parcours |
| `teacher.c@alnoor.demo` | Grade 4 — C, la classe qui décroche |
| `teacher.a@alnoor.demo` | Grade 4 — A, le contraste |
| `teacher.b@alnoor.demo` | Grade 4 — B |
| `student049@alnoor.demo` | Session live — étape 5 |
| `parent@alnoor.demo` | Trajectoire de l'élève vitrine, lecture seule (aucune session possible) |
| `it.admin@alnoor.demo` | Console IT : checklist, annuaire, sync, audit, export |
| `linguist@alnoor.demo` | File de validation arabe (back-office staff Atlas) |

La session dure 4 h (`AUTH_SESSION_TTL_S`) : un rendez-vous ne se termine pas par une
déconnexion en plein partage d'écran. Dix mots de passe faux en dix minutes bloquent
l'IP et l'email dix minutes (429) — le mot de passe est partagé, pas public.

## Ce que cette stack n'est pas

Elle n'est **pas** destinée à des données d'élèves réelles. `ATLAS_ENV=demo` ouvre la
connexion par mot de passe partagé&nbsp;; `ATLAS_ENV=prod` la referme (l'endpoint répond
404). Pour un vrai pilote, c'est `deploy/prod/` qu'il faut déployer : SSO Keycloak, TOTP,
rétention, audit.
