# Runbook de déploiement — Atlas Learning (auth, rostering, accès)

Procédure ops pour mettre en production la chaîne d'achat : SSO, onboarding self-service,
rostering Google, accès parent. **Tout le code est livré et testé (94 tests)** ; ce document
couvre la configuration externe (Google, email, secrets) et l'ordre des opérations.

---

## 1. Prérequis infra

- **Backend** : Python 3.11, PostgreSQL (prod ; Oracle UAE pour la résidence GCC).
- **Frontend** : Node 18+, build Next.js.
- **Cron** : un planificateur pour la sync nocturne (`scripts/roster_sync.py`).
- Dépendances Python : `pip install -r requirements.txt` (inclut `google-auth`, `requests`
  pour la voie Google réelle — sinon import paresseux, donc dev OK sans).

---

## 2. Variables d'environnement (exhaustif)

### Cœur (obligatoire)
| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Postgres prod (`postgresql+psycopg://…`). Défaut dev = SQLite. |
| `AUTH_SECRET` | Clé HMAC des jetons. **Obligatoire en prod** (sinon refus, cf. `ATLAS_ENV`). |
| `ATLAS_ENV` | `prod` active le fail-fast sur `AUTH_SECRET`. |
| `WEB_BASE_URL` | Base du front (ex. `https://app.atlas.example`) — redirections SSO / liens magiques. |
| `GROQ_API_KEY` | Génération d'items (existant). |

### SSO / OIDC (par fournisseur activé)
| Variable | Rôle |
|---|---|
| `OIDC_GOOGLE_CLIENT_ID` / `OIDC_GOOGLE_CLIENT_SECRET` | OAuth Google (login + onboarding). |
| `OIDC_MICROSOFT_CLIENT_ID` / `OIDC_MICROSOFT_CLIENT_SECRET` | OAuth Entra ID (optionnel). |
| `OIDC_MICROSOFT_TENANT` | Tenant Microsoft (défaut `common`). |
| `OIDC_GENERIC_CLIENT_ID` / `_SECRET` / `OIDC_GENERIC_ISSUER` | IdP OIDC générique (optionnel). |
| `OIDC_REDIRECT_BASE` | Base des redirect URI (défaut = `WEB_BASE_URL`). |

Un fournisseur sans `CLIENT_ID`/`SECRET` est simplement absent de `/auth/providers`.

### Rostering Google (Admin SDK + Classroom)
| Variable | Rôle |
|---|---|
| `GOOGLE_SA_KEY_JSON` **ou** `GOOGLE_SA_KEY_FILE` | Clé du service account vendeur (JSON inline ou chemin). |
| `ROSTER_GUARDIANS` | `1` pour activer les tuteurs Classroom (scope dédié requis). |

### Licence & email
| Variable | Rôle |
|---|---|
| `DEFAULT_SEATS` | Quota de sièges par défaut à l'onboarding (vide = illimité). |
| `POSTMARK_TOKEN` / `EMAIL_FROM` | Envoi des emails (liens magiques parents). Sinon : aucun email (Noop). |

---

## 3. Configuration Google Cloud (une fois, côté vendeur)

1. **Projet GCP** + activer les API **Admin SDK** et **Google Classroom**.
2. **Service account** (1 global vendeur) → générer une clé JSON → `GOOGLE_SA_KEY_*`.
3. **App Google Workspace Marketplace** (listing privé/public) — c'est ce que l'IT admin
   installe pour son domaine. Déclarer les **scopes (lecture seule)** :
   - `admin.directory.user.readonly`, `admin.directory.orgunit.readonly`,
     `admin.directory.group.readonly`, `admin.directory.group.member.readonly`
   - `classroom.guardianlinks.students.readonly` (si tuteurs activés)
4. **OAuth client** (web) pour le login/onboarding → `OIDC_GOOGLE_CLIENT_*`. Redirect URIs à
   déclarer :
   - `{OIDC_REDIRECT_BASE}/api/oauth/google/callback`
   - `{OIDC_REDIRECT_BASE}/api/onboarding/google/callback`
5. **Vérification OAuth Google** des scopes sensibles `admin.directory.*` / `classroom.*`
   → revue Google, possible **assessment CASA**. ⏳ Plusieurs semaines : **lancer tôt** (chemin
   critique du deal). Tant que non vérifié, l'app marche en mode test (utilisateurs ajoutés
   manuellement).
6. **Postmark** (ou SES/SendGrid) : domaine d'envoi vérifié (SPF/DKIM) → `POSTMARK_TOKEN` + `EMAIL_FROM`.

---

## 4. Déploiement

```bash
# Backend (04_code)
pip install -r requirements.txt
alembic upgrade head          # 0001 → 0012, réversibles
# (sanity) python -m pytest  OU lancer les tests/*.py via leur __main__
uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# Frontend (04_code/web)
npm ci && npm run build && npm run start   # NEXT_PUBLIC_API_BASE → backend
```

Migrations livrées (ordre) : `0008_totp_secret` → `0009_rostering` → `0010_student_classroom`
→ `0011_roster_run_pending` → `0012_parent_student_source`.

---

## 5. Onboarding d'un tenant (côté client, self-service)

1. Sales envoie l'URL : `{WEB_BASE_URL}/onboarding` (Sign-in Google).
2. L'IT admin se connecte (compte **admin** Workspace requis → vérifié par `users/me.isAdmin`).
   → tenant créé (Org + IT_ADMIN bootstrap + intégration `pending` + école par défaut).
3. La console `/it` affiche la **checklist guidée** : installer l'app Marketplace → lancer la
   1re sync → vérifier les effectifs → inviter les parents.
4. **Quota de sièges** : posé par le vendeur (`POST /admin/organizations/{id}/seats`, rôle
   SUPER_ADMIN) selon le contrat.

---

## 6. Planification (sync nocturne)

```cron
0 2 * * *  cd /app/04_code && DATABASE_URL=… GOOGLE_SA_KEY_FILE=… ROSTER_GUARDIANS=1 \
           python scripts/roster_sync.py >> /var/log/atlas-roster.log 2>&1
```
Idempotent. Une sync qui désactiverait massivement (≥ 8 et ≥ 25 % d'un coup) est **bloquée**
(`RosterRun` = `blocked`) → l'IT admin approuve dans la console (`?force=true`).

---

## 7. Checklist de vérification post-déploiement

- [ ] `GET {API}/auth/providers` liste `google` (et autres configurés).
- [ ] Login Google d'un compte staff → session, landing par rôle.
- [ ] Onboarding d'un domaine de test → tenant créé, checklist visible.
- [ ] `POST /admin/rostering/sync` → `RosterRun` `ok`, effectifs corrects, statut `connected`.
- [ ] Avec `ROSTER_GUARDIANS=1` → liens parents créés (`source="roster"`).
- [ ] `parent/request-link` → email reçu → `parent/login` → espace enfant (sélecteur si ≥2).
- [ ] `AUTH_SECRET` posé + `ATLAS_ENV=prod` (le backend refuse de démarrer sinon).
- [ ] MFA staff : 1er login admin/prof → enrôlement TOTP (QR).

---

## 8. Sécurité & conformité (rappels bloquants)

- **`AUTH_SECRET`** unique, secret, jamais par défaut en prod (fail-fast actif).
- **Résidence GCC** : Postgres en région UAE ; PII Google → Oracle UAE.
- **Sign-off PDPL** (juridique) avant import de PII Google : droits sujets couverts en
  produit (`/admin/audit`, `/admin/export`, effacement sujet/tenant).
- **Moindre privilège** : tous les scopes Google sont en lecture seule.
- **Accès parent** : push-only (jamais d'auto-déclaration) ; lien magique = preuve d'email.
