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

## 2. La VM

N'importe quel serveur avec Docker et les ports 80/443 ouverts. Compter **2 vCPU / 4 Go**
(la stack en réserve ~2,5 Go). `deploy/infra/oci/` provisionne une VM Oracle Cloud gratuite
en région Émirats — utile si la résidence des données dans le Golfe fait partie de
l'argumentaire.

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

## 5. Les 5 comptes

Même mot de passe pour tous, affiché par `deploy.sh` et conservé dans `.env` sur la VM
(jamais versionné).

| Compte | Ce qu'il ouvre |
|---|---|
| `director@alnoor.demo` | Vue école — étape 1 du parcours |
| `teacher.c@alnoor.demo` | Grade 4 — C, la classe qui décroche |
| `teacher.a@alnoor.demo` | Grade 4 — A, le contraste |
| `teacher.b@alnoor.demo` | Grade 4 — B |
| `student049@alnoor.demo` | Session live — étape 5 |

## Ce que cette stack n'est pas

Elle n'est **pas** destinée à des données d'élèves réelles. `ATLAS_ENV=demo` ouvre la
connexion par mot de passe partagé&nbsp;; `ATLAS_ENV=prod` la referme (l'endpoint répond
404). Pour un vrai pilote, c'est `deploy/prod/` qu'il faut déployer : SSO Keycloak, TOTP,
rétention, audit.
