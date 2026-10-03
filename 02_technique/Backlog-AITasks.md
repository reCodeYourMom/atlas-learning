# Atlas Learning — Backlog (reste à faire)

Les epics 1 à 6 (25 tâches : référentiel, banque d'items, moteur Elo, session adaptative,
restitution, socle RBAC/SSO/tenant) sont livrés et testés ; leur détail a été retiré de ce
document le 2026-10-03 et reste lisible dans l'historique git. Ne figure ici que ce qui
reste ouvert.

---

## EPIC 7 — Mise en prod & provisioning externe (post-code)

But : passer du code livré (94 tests auth/rostering) à un déploiement réel. Tâches **ops/config externe**, pas du code. Réf. : `Runbook-Deploiement.md`. État au 2026-06-21.

> **Fait (2026-06-21, via console Google)** : projet GCP **Atlas Learning** (`atlas-learning-500120`) créé ; **Admin SDK API** + **Classroom API** activées ; **service account** `atlas-rostering@atlas-learning-500120.iam.gserviceaccount.com` + clé JSON générée ; **consent screen** (app « Atlas Learning », audience Externe, mode test) ; **5 scopes lecture seule** déclarés ; **OAuth client web** « Atlas Web » créé (`OIDC_GOOGLE_CLIENT_ID` = `1044384395682-r6hd96bc1jo5jdt93ji1otg2si0lug9m.apps.googleusercontent.com`), redirect URIs en `localhost` (temp). Détail : `04_code/deploy/google_config_summary.md`.

### T7.1 — Mettre les secrets en coffre (OCI Vault)
**Objectif** : sécuriser le client secret OAuth + la clé JSON du service account.
**Contraintes** : copier `OIDC_GOOGLE_CLIENT_SECRET` depuis la console (Clients > Atlas Web) ; déplacer le `.json` SA (Téléchargements) vers le Vault → `GOOGLE_SA_KEY_FILE` ; supprimer toute copie locale ; `AUTH_SECRET` (déjà généré, `deploy/SECRETS.local.txt`) → Vault aussi.
**AC** : 1. Aucun secret en clair sur disque/repo. 2. Le backend prod lit les 3 secrets depuis le Vault. 3. `deploy/SECRETS.local.txt` supprimé après transfert.

### T7.2 — Délégation domain-wide (côté IT admin client)
**Objectif** : autoriser le service account à lire l'annuaire d'un domaine Workspace.
**Contraintes** : dans la console Admin Workspace du client → Sécurité > Accès aux API > délégation à l'échelle du domaine → ajouter le client `118253211458052923043` avec les 5 scopes (`admin.directory.user/group/group.member/orgunit.readonly` + `classroom.guardianlinks.students.readonly`).
**AC** : 1. `POST /admin/rostering/sync` renvoie un `RosterRun` `ok` sur un domaine de test. 2. Les effectifs remontent. 3. Avec `ROSTER_GUARDIANS=1`, les liens parents sont créés (`source="roster"`).

### T7.3 — Domaine de prod + redirect URIs définitives
**Objectif** : remplacer le placeholder `localhost`.
**Contraintes** : choisir/acheter le domaine ; pointer le front ; ajouter dans l'OAuth client les 2 redirect URIs réelles (`{base}/api/oauth/google/callback`, `{base}/api/onboarding/google/callback`) ; régler `WEB_BASE_URL` / `OIDC_REDIRECT_BASE`.
**AC** : 1. Login Google d'un compte de test aboutit sans erreur redirect_uri_mismatch. 2. `OIDC_REDIRECT_BASE` ne contient plus `localhost`.

### T7.4 — Vérification OAuth Google (chemin critique, ⏳ plusieurs semaines)
**Objectif** : sortir l'app du mode test pour qu'un domaine quelconque puisse l'utiliser.
**Contraintes** : prérequis bloquants = domaine vérifié, homepage publique, **privacy policy** en ligne, **vidéo démo** YouTube, justification par scope. Publier l'app → soumettre à revue Google → traiter l'éventuelle **évaluation CASA** (scopes `admin.directory.*` sensibles). **Lancer dès que les prérequis sont prêts.**
**AC** : 1. Statut consent screen = « In production / Verified ». 2. Un compte hors liste de test peut se connecter.
**Intérim (non bloquant pilote)** : ajouter les comptes des écoles pilotes comme **utilisateurs de test** dans le consent screen.

### T7.5 — Listing Google Workspace Marketplace (privé)
**Objectif** : permettre à l'IT admin d'installer l'app pour son domaine en un clic.
**Contraintes** : créer le listing privé, déclarer les scopes lecture seule, lier au projet `atlas-learning-500120`.
**AC** : 1. L'app apparaît dans le Marketplace du domaine client. 2. L'installation déclenche le consentement admin des scopes.

### T7.6 — Email transactionnel (Postmark)
**Objectif** : activer l'envoi des liens magiques parents.
**Contraintes** : domaine d'envoi vérifié (SPF/DKIM) → `POSTMARK_TOKEN` + `EMAIL_FROM`. Sans token : Noop (aucun email).
**AC** : 1. `parent/request-link` envoie un email réel. 2. `parent/login` via le lien aboutit à l'espace enfant (sélecteur si ≥2).

### T7.7 — Avertissement compte Google (à surveiller)
**Objectif** : lever le bandeau « plusieurs projets sembleraient ne pas respecter la politique d'utilisation » sur le compte nassimboughazi@gmail.com.
**Contraintes** : peut bloquer la vérification OAuth. Vérifier les projets signalés ; envisager un compte/organisation Google dédié vendeur pour la prod.
**AC** : 1. Plus d'avertissement actif, ou cause identifiée et traitée.

### T7.8 — Séquencement & prérequis de vérification (analyse 2026-06-21, à traiter en dernier)

Notes d'orchestration de l'Epic 7 (issues de la revue de session). **Ordre recommandé** :
```
1. Domaine vendeur + compte/org Google dédié   (T7.3 + T7.7)  ← clé de voûte, d'abord
2. Secrets → Vault, purge locale               (T7.1)        ← urgent, en parallèle
3. Pilote en mode test : délégation + test users (T7.2 + intérim T7.4)
4. Privacy policy + vidéo + justifs scopes → soumettre (T7.4) ← long pole
5. Marketplace (T7.5) + Postmark (T7.6)
```

**Insights à ne pas perdre :**
- **🔑 Le domaine est la clé de voûte** : il débloque *simultanément* T7.3 (redirect URIs),
  T7.4 (vérif exige domaine vérifié + homepage + privacy policy *sur ce domaine*) et T7.6
  (domaine d'envoi SPF/DKIM). À trancher avant tout le reste.
- **🔴 Réordonner T7.7 AVANT T7.4** : app à scopes sensibles `admin.directory.*` depuis un
  `gmail.com` personnel + bandeau d'avertissement = risque fort de blocage de la vérif.
  Google pousse vers un **compte d'organisation (Cloud Identity/Workspace) vendeur**. Migrer
  le projet sous une org dédiée AVANT d'investir privacy policy + vidéo (sinon travail à refaire).
- **🟢 Le pilote n'attend pas la vérif** : comptes pilotes en *utilisateurs de test* (intérim
  T7.4) + délégation domain-wide (T7.2) → rostering réel testable en mode test, feedback terrain
  immédiat pendant que la revue Google tourne.
- **🟠 Secrets (T7.1) = urgence** : clé SA (scopes annuaire) dans ~/Téléchargements +
  `SECRETS.local.txt` = exposition réelle → Vault + purge sans attendre le reste.

**Sous-tâches contenu (prérequis T7.4, rédigeables sans Google — à générer le moment venu) :**
- **T7.4a** — Privacy policy (posture PDPL/GCC + scopes lecture seule réellement utilisés).
- **T7.4b** — Justifications par scope (texte demandé par Google, scope par scope, basé sur l'usage réel dans le code).
- **T7.4c** — Script de vidéo démo (parcours minimal exigé : consentement → usage des scopes).
- **T7.4d** — Revue des artefacts `deploy/` (`prod/.env.prod.example`, `prod/verify_deploy.sh`) contre le code.
**AC** : 1. Les 4 livrables produits et reliés à la soumission T7.4. 2. Ordre ci-dessus respecté (domaine + org avant soumission).

---

## Open questions (engineering, hors périmètre immédiat)

- [ ] **LLM pour génération d'items et remédiation** : Claude (cloud, hors GCC) vs LLM arabe local (Jais-70B / ALLaM, hébergeable en région UAE). Trancher quand on industrialise la génération AR et la remédiation (Epic 2.2 / 5.6). Enjeu : un LLM local règle le garde-fou « données hors-GCC » et améliore potentiellement la qualité AR ; Claude reste plus fort en orchestration/raisonnement. Décision conditionnée au volume et aux exigences de souveraineté du premier client. NB : la génération ne contient déjà aucune donnée élève, donc l'enjeu souveraineté est limité au MVP — devient critique si la remédiation s'appuie un jour sur des données d'usage.
- [ ] Échelle Elo définitive et table d'ancrage trajectoire (barème expert initial → cohorte réelle).
- [ ] Seuils exacts : quarantaine item, ré-estimation des poids, arrêt de session.

---

## Backlog produit — issus de la revue crosswalk (05_revue, décisions 2026-07-12)

- [ ] **Métrique de granularité « N gestes Atlas par standard » (C-3)** — argument de vente n°1 : un standard officiel = jusqu'à 5 compétences Atlas mesurées séparément (« là où votre programme voit une case, nous mesurons cinq gestes distincts »). Se calcule trivialement depuis `competency_curriculum_map` (COUNT par `standard_id`). À afficher au **rapport école** et au **one-pager**. Ne touche PAS aux types d'alignement (le type unique par ligne ne peut porter simultanément grain BROADER et grade ENRICH — c'est une métrique dérivée, pas un type). Décidé par le fondateur le 2026-07-12.
