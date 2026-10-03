# Périmètre SSO / authentification — réponse à la revue sécurité DSI

**Statut** : actif · **Date** : 2026-06-23 · Réf. backlog T6.3, PRD §sécurité · MAJ post-revue DSI

Document destiné à la conversation DSI. Répond point par point au retour :
> « Pas de SSO réel. Le MFA TOTP-lite HMAC maison et les comptes directs ne passeront pas
> ma revue. Je veux OIDC avec mon IdP (Microsoft / Google Workspace for Education) et du
> roster sync standard (OneRoster / Clever / Wonde), pas un cron maison. »

## Réponse synthétique

| Exigence DSI | Statut | Implémentation |
|---|---|---|
| **OIDC réel avec mon IdP** | ✅ livré | Microsoft Entra ID + Google Workspace + **UAE PASS** (SSO national, public + privé) + IdP OIDC générique. Flux Authorization Code, **ID token validé cryptographiquement** (JWKS) pour les IdP conformes. |
| **Pas de MFA maison** | ✅ supprimé | Plus aucune MFA applicative. **MFA déléguée à l'IdP.** |
| **Pas de comptes directs** | ✅ supprimé en prod | Plus de login mot de passe en production. Auth **100 % IdP**. *Exception explicite, hors prod uniquement* : `/demo/login` (mot de passe partagé de la stack de démo, 404 si `ATLAS_ENV=prod`, anti-bruteforce, audité — §3). |
| **Roster sync standard, pas un cron maison** | ✅ livré | Connecteurs **OneRoster 1.1/1.2 (REST + CSV)** et **Wonde**, derrière une abstraction commune. |

## 1. OIDC réel — identité prouvée par le ID token (`src/rbac/oidc.py`)
Flux **Authorization Code**. À chaque connexion :
1. `state` signé HMAC (purpose cloisonné, anti-CSRF) **portant un `nonce`** (anti-rejeu).
2. Échange du code → `id_token`.
3. **Validation cryptographique du ID token** (`validate_id_token`) : signature **RS256/ES256
   vérifiée contre le JWKS de l'IdP**, `iss` = émetteur attendu, `aud` = notre `client_id`,
   `exp`/`iat` (tolérance d'horloge), et **`nonce`** = celui émis à l'étape 1.
   `alg=none` et clés symétriques sont refusés.
4. L'email vérifié des **claims signés** résout l'utilisateur. `userinfo` n'est plus une
   preuve d'identité (au plus un complément d'affichage).

Garde-fous : l'email doit **déjà exister** en base (pas d'auto-provisioning d'un inconnu) ;
le token de session est renvoyé au front dans le fragment `#token=` (jamais journalisé).

Providers (rien en dur, tout par variables d'environnement) :
```
# Microsoft Entra ID (Azure AD)
OIDC_MICROSOFT_CLIENT_ID=...
OIDC_MICROSOFT_CLIENT_SECRET=...
OIDC_MICROSOFT_TENANT=<tenant-id de l'école>   # ou "common"
# Google Workspace for Education
OIDC_GOOGLE_CLIENT_ID=...
OIDC_GOOGLE_CLIENT_SECRET=...
# UAE PASS (SSO national EAU — écoles publiques ET privées, via le digital ID gouvernemental)
OIDC_UAEPASS_CLIENT_ID=...
OIDC_UAEPASS_CLIENT_SECRET=...
OIDC_UAEPASS_ENV=production                     # ou "staging" ; OIDC_UAEPASS_ISSUER pour override
# IdP OIDC générique conforme (Okta, Keycloak, ADFS…)
OIDC_GENERIC_CLIENT_ID=...
OIDC_GENERIC_CLIENT_SECRET=...
OIDC_GENERIC_ISSUER=https://idp.exemple/...
# Communs
WEB_BASE_URL=https://app.exemple
OIDC_REDIRECT_BASE=https://app.exemple         # défaut = WEB_BASE_URL
AUTH_SECRET=<secret robuste>                    # ATLAS_ENV=prod → fail-fast si absent
```
Redirect URI à déclarer chez l'IdP : `{OIDC_REDIRECT_BASE}/api/oauth/{provider}/callback`.
Dépendance : `PyJWT[crypto]` (validation RS256/ES256 via JWKS), importée paresseusement.

### Source d'identité par provider (cas UAE PASS)
La preuve d'identité par défaut est le **ID token validé (JWKS)** — Entra, Google, IdP
conformes. **UAE PASS** fait exception assumée : il n'expose pas de `.well-known`/JWKS ni de
`id_token` signé standard (endpoints fixes `id.uaepass.ae/idshub/{authorize,token,userinfo}`).
Pour lui — et lui seul — l'identité est résolue via **`userinfo` over TLS** authentifié par
l'access_token (`Provider.identity_source = "userinfo"`, `acr_values` = SOP, scope
`urn:uae:digitalid:profile:general`). Le `state` signé HMAC reste la protection anti-CSRF.
**Tous les autres IdP conservent la validation cryptographique stricte du ID token** : c'est
une exception ciblée et documentée, pas un affaiblissement global.

## 2. MFA — déléguée à l'IdP (plus de TOTP applicatif)
Le « MFA TOTP-lite HMAC maison » **n'existe plus** : tout le code TOTP/HMAC applicatif a
été retiré. La politique MFA (TOTP, push, FIDO2, conditionnelle) est **gérée par l'IdP de
l'établissement** (Entra ID / Google), conformément à la revue DSI — un seul point de
gouvernance des facteurs, côté établissement.

## 3. Suppression des comptes directs — auth 100 % IdP
- Plus de route `/login` mot de passe, plus d'enrôlement MFA applicatif.
- Le modèle `app_user` ne stocke **plus** `password_hash`, `totp_secret`, `mfa_enabled`
  (migration `0013_drop_direct_auth`, réversible). L'identité durable est ancrée sur
  `external_ref` (id immuable IdP/annuaire), jamais l'email.
- **Trois accès sans mot de passe, par liens magiques signés** (HMAC, usage cloisonné,
  **à usage unique** — jti consommé atomiquement, `src/rbac/single_use.py`) :
  - **Parents** (hors Workspace scolaire) : `/parent/request-link` → `/parent/login`.
  - **Super-admin Atlas** (équipe éditeur) : `/admin/request-link` → `/admin/login`. Ils ne
    peuvent pas dépendre de l'IdP d'un *client* ; lien magique court (30 min), à usage
    unique, réservé aux `SUPER_ADMIN` (rôle revérifié à la connexion).
  - **Linguiste Atlas** (staff global, back-office `/linguist/*`) : `/linguist/request-link`
    → `/linguist/login` ; bootstrap out-of-band par `scripts/onboard_linguist.py`.
- **Dev/tests** sans IdP externe : simulateur SSO `/dev/login`, **fermé par défaut** et
  **en prod** (exige `OIDC_DEV_LOGIN=1` ET `ATLAS_ENV` non-prod). Aucune surface en production.
- **Démo commerciale** (`deploy/demo/`, sans Keycloak) : `/demo/login`, **un** mot de passe
  partagé lu dans l'environnement (`DEMO_LOGIN_PASSWORD`), ouvrant une session sur un compte
  **existant** du jeu de démo. Trois verrous (secret posé, `ATLAS_ENV` non-prod, compte
  actif), comparaison à temps constant, message d'erreur unique, **10 échecs / 10 min par
  IP et par email → 429**, chaque tentative auditée. Session de 4 h en démo
  (`AUTH_SESSION_TTL_S`), 1 h en prod. Cette stack n'est pas destinée à des données réelles.

## 4. RBAC & isolation tenant (inchangé, déjà en place)
- **RBAC 8 rôles** vérifié côté serveur (`src/rbac/authz.py`) : 6 rôles tenant — super admin,
  admin IT, admin pédagogique, enseignant, parent, élève — plus 2 rôles de **staff Atlas
  global**, non tenant-scopés : **linguiste** (validation de l'arabe de la banque) et
  **content reviewer** (revue pédagogique EN, activation, sortie de quarantaine — CLI
  `scripts/review_items.py`). Isolation tenant (école/classe/enfant).
- **Lecture ≠ écriture** : le parent VOIT son enfant (`can_access_student`) mais ne peut ni
  ouvrir une session ni répondre à sa place (`can_act_for_student`) ni gérer les tuteurs
  (`can_manage_student`). Le référentiel (`/competencies`) est réservé au staff.
- `school_id` sur toute donnée élève (response, ability, session) — intégré au schéma.

## 5. Roster sync standard — OneRoster + Wonde (pas un cron maison)
Architecture **agnostique de la source** : chaque connecteur produit le même
`DirectorySnapshot` (`src/rostering/directory.py`) ; le moteur de réconciliation idempotent
(`src/rostering/sync.py`) ne connaît aucune API propriétaire. Le rôle est porté
**explicitement** par les standards (plus de devinette sur les noms d'OU).

| Provider | Module | Transport | Notes |
|---|---|---|---|
| **OneRoster 1.1/1.2 REST** | `src/rostering/oneroster.py` | OAuth2 `client_credentials` | `/orgs /users /classes /enrollments`, `sourcedId` stable, pagination, `tobedeleted` → déprovisionné. |
| **OneRoster 1.1/1.2 CSV** | `src/rostering/oneroster_csv.py` | dossier ou ZIP | Bundle CSV standard (format ministère), réutilise le mapping REST. |
| **Wonde** | `src/rostering/wonde.py` | Bearer token | Per-school, pagination curseur, forte présence MENA/UK. |
| Google Workspace (héritage) | `src/rostering/google.py` | Service account | Conservé ; rôle déduit de l'OU (sources sans rôle explicite). |

Sélection par tenant : `TenantIntegration.provider ∈ {google, oneroster, oneroster_csv, wonde}` ;
factory `directory_for(integ)` (`src/api/app.py`). Configuration via `POST /admin/integration`.
Variables d'environnement (secrets jamais en dur) :
```
# OneRoster REST
ONEROSTER_BASE_URL=...  ONEROSTER_TOKEN_URL=...  ONEROSTER_CLIENT_ID=...  ONEROSTER_CLIENT_SECRET=...
ONEROSTER_VERSION=v1p1            # ou v1p2
# OneRoster CSV
ONEROSTER_CSV_PATH=/chemin/bundle(.zip)
# Wonde
WONDE_TOKEN=...                   # id école Wonde = TenantIntegration.customer_id
```

> **« pas un cron maison »** : un sync planifié reste nécessaire, mais il parle désormais des
> **protocoles standards** ci-dessus. `src/rostering/scheduler.py` est une fonction pure
> déclenchable par n'importe quel ordonnanceur (cron, Cloud Scheduler, K8s CronJob) — c'est
> un *déclencheur*, pas une intégration propriétaire. Clever : non prioritaire (marché US) ;
> l'abstraction l'accepte si expansion (un adaptateur de plus).

## 6. Conformité, licence, parents (inchangé, déjà en place)
- **PDPL** : `GET /admin/audit`, `GET /admin/export`, `POST /admin/students/{id}/erase`,
  `POST /admin/tenant/erase`.
- **Sièges/licence** : `Organization.seats`, dépassement = alerte visible (pas refus dur).
- **Confiance parent↔enfant (push-only)** : lien établi par une autorité (Google Classroom
  guardians, ou staff), jamais auto-déclaré. Le lien magique ne prouve que la possession de
  l'email ; la relation est établie par l'autorité.

## Hors périmètre MVP (roadmap crédible, dit explicitement)
- **Connecteur Clever** (marché US) — abstraction prête, à la demande.
- **SCIM provisioning** temps réel (au-delà du roster batch).
- **Hub multi-IdP simultané** par tenant (un IdP + comptes magiques de secours suffisent).
- **SOC 2 type 2 / ISO 27001** : 6-12 mois ; roadmap PRD, pas prérequis V1.
- **Export SIEM** des logs d'audit (les logs eux-mêmes sont V1).

## Pourquoi ce découpage
Marché K-12 GCC = données de mineurs + souveraineté (UAE fédéral, PDPL saoudienne) + achat
via DSI. La sécurité est un *gate d'achat*. Le périmètre ci-dessus répond intégralement à la
revue : OIDC réel et vérifié, MFA chez l'IdP, zéro compte direct, rostering aux standards.
