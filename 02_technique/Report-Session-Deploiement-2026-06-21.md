# Report de session — Préparation déploiement Atlas Learning

**Date** : 2026-06-21 · **Périmètre** : validation du code livré + config Google Cloud + génération des artefacts de déploiement.

---

## 1. Validation du code (repo `04_code`)

Exécuté contre le vrai repo (venv Linux propre, deps installées) :

| Vérification | Résultat |
|---|---|
| Suite de tests complète (`pytest`) | **226 tests verts** (1 warning Starlette bénin) |
| Migrations `alembic upgrade head` (0001→0012) | Appliquées proprement, head = `0012_parent_student_source` |
| Réversibilité (`downgrade base` → re-`upgrade head`) | OK |
| Fail-fast `AUTH_SECRET` (`ATLAS_ENV=prod` sans secret) | Lève bien `RuntimeError` ; OK avec secret |
| Boot backend (`uvicorn`) en mode prod sur base migrée | Démarre ; `/auth/providers` répond ; healthcheck 200 |
| Variables d'env du runbook §2 | Confirmées présentes dans `src/` (conventions OIDC incluses) |

**Conclusion** : le code est déployable. Aucun blocage côté application.

---

## 2. Artefacts de déploiement générés (`04_code/deploy/`)

| Fichier | Contenu |
|---|---|
| `.env.prod.template` | Toutes les variables §2, annotées, vérifiées contre le code. `OIDC_GOOGLE_CLIENT_ID` réel renseigné. |
| `SECRETS.local.txt` | `AUTH_SECRET` généré (48 bytes). **Gitignoré.** À mettre en Vault puis supprimer. |
| `verify_deploy.sh` | Checklist §7 exécutable (curl). Testé contre un backend live. `chmod +x`. |
| `roster_sync.cron` | Ligne cron de sync nocturne §6, prête à adapter. |
| `google_cloud_setup.md` | Checklist de config §3 avec ordre conseillé. |
| `google_config_summary.md` | Toutes les valeurs concrètes de la config Google réalisée + reste-à-faire. |

---

## 3. Configuration Google Cloud (réalisée via la console)

Compte `nassimboughazi@gmail.com`, projet **Atlas Learning** (`atlas-learning-500120`).

- ✅ **Projet GCP** créé et sélectionné.
- ✅ **API activées** : Admin SDK API, Google Classroom API.
- ✅ **Service account** `atlas-rostering@atlas-learning-500120.iam.gserviceaccount.com`.
  - Clé JSON générée + téléchargée (dans ~/Téléchargements).
  - ID client OAuth2 (délégation domain-wide) : `118253211458052923043`.
- ✅ **Consent screen** : app « Atlas Learning », audience **Externe**, règlement Google accepté → **mode test**.
- ✅ **5 scopes lecture seule** déclarés : `admin.directory.user/group/group.member/orgunit.readonly` (sensibles) + `classroom.guardianlinks.students.readonly`.
- ✅ **OAuth client web** « Atlas Web (login + onboarding) ».
  - `OIDC_GOOGLE_CLIENT_ID` = `1044384395682-r6hd96bc1jo5jdt93ji1otg2si0lug9m.apps.googleusercontent.com`
  - Redirect URIs : `http://localhost:8000/api/oauth/google/callback` + `.../api/onboarding/google/callback` (**temporaire**, faute de domaine).

---

## 4. Limites / non fait (et pourquoi)

- **Domaine prod absent** → redirect URIs en `localhost` (Google refuse les TLD non publics comme `.example`). À reprendre quand le domaine sera fixé.
- **Secrets non extraits** (par sécurité) : client secret OAuth + clé JSON SA → à récupérer toi-même et mettre en Vault.
- **Délégation domain-wide** : à faire côté IT admin client (console Workspace).
- **Vérification OAuth Google** : non soumise — prérequis bloquants manquants (domaine, privacy policy, vidéo démo). App utilisable en mode test uniquement.
- **Listing Marketplace** et **Postmark** : non traités.
- **⚠️ Bandeau d'avertissement Google** sur le compte (« projets ne respectant pas la politique d'utilisation ») — à surveiller, peut gêner la vérification.

---

## 5. Suite — voir backlog

Tout le reste-à-faire est consigné dans `Backlog-AITasks.md` → **Epic 7 — Mise en prod & provisioning externe** (T7.1 à T7.7), avec critères d'acceptation.

Chemin critique : **T7.4 (vérification OAuth Google)** — plusieurs semaines, à lancer dès que domaine + privacy policy sont prêts. En attendant, pilote possible en ajoutant les écoles comme utilisateurs de test (intérim T7.4).
