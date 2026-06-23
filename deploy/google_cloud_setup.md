# Configuration Google Cloud — Atlas Learning (runbook §3)

À faire **une fois, côté vendeur**. Le chemin critique est l'étape 5 (vérification
OAuth Google) : **plusieurs semaines** → lancer en premier.

## Checklist

- [ ] **1. Projet GCP** créé + activer les API **Admin SDK** et **Google Classroom**.
- [ ] **2. Service account** (1 global vendeur) → générer clé JSON
      → renseigner `GOOGLE_SA_KEY_JSON` (inline) **ou** `GOOGLE_SA_KEY_FILE` (chemin).
- [ ] **3. App Google Workspace Marketplace** (listing privé ou public) — c'est ce que
      l'IT admin client installe pour son domaine. Déclarer les **scopes lecture seule** :
      - [ ] `admin.directory.user.readonly`
      - [ ] `admin.directory.orgunit.readonly`
      - [ ] `admin.directory.group.readonly`
      - [ ] `admin.directory.group.member.readonly`
      - [ ] `classroom.guardianlinks.students.readonly`  *(si ROSTER_GUARDIANS=1)*
- [ ] **4. OAuth client (web)** pour login/onboarding → `OIDC_GOOGLE_CLIENT_ID` / `_SECRET`.
      Redirect URIs à déclarer (base = `OIDC_REDIRECT_BASE`, défaut `WEB_BASE_URL`) :
      - [ ] `{OIDC_REDIRECT_BASE}/api/oauth/google/callback`
      - [ ] `{OIDC_REDIRECT_BASE}/api/onboarding/google/callback`
- [ ] **5. Vérification OAuth Google** des scopes sensibles `admin.directory.*` / `classroom.*`
      → revue Google + possible **assessment CASA**. ⏳ Plusieurs semaines — **LANCER TÔT**.
      Tant que non vérifié : mode test (utilisateurs ajoutés manuellement).
- [ ] **6. Postmark** (ou SES/SendGrid) : domaine d'envoi vérifié (SPF/DKIM)
      → `POSTMARK_TOKEN` + `EMAIL_FROM`.

## Ordre conseillé
5 (lancer la revue Google d'abord, c'est le goulot) → 1 → 2 → 3 → 4 → 6.
