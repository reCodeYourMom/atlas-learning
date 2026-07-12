# Instructions — Projet Atlas Learning

> Mis à jour le 2026-06-21. La section « État d'avancement » ci-dessous est aussi à recopier dans les **réglages du projet Claude** (instructions personnalisées) — c'est elle qui était périmée.

## Ce qu'est Atlas Learning
Plateforme SaaS d'évaluation adaptative K-12 pour le marché GCC (Golfe). Mesure la maîtrise d'un élève **compétence par compétence** (grain fin), via un moteur adaptatif, et restitue une trajectoire crédible vers l'enseignement supérieur. Le produit ne crée pas de contenu pédagogique : sa valeur est la **mesure** et sa **restitution** — en particulier un **diagnostic causal** (« bloque sur X *parce que* le prérequis Y n'est pas maîtrisé »), qui est l'argument de vente différenciant.

MVP : vertical **Fractions** (32 micro-compétences, G2→G5). **Le MVP est codé et testé de bout en bout** (voir État d'avancement).

## Décisions structurantes déjà figées (ne pas rouvrir sans raison)
- **Wedge** = moteur d'évaluation adaptative, PAS l'adaptive learning. L'apprentissage (remédiation) est une couche secondaire.
- **3 couches séparées** : moteur de mesure (Elo) / référentiel de compétences neutre / restitution-trajectoire. La crédibilité "université d'élite" vit dans la restitution, pas dans le moteur.
- **Moteur** = Elo (pas IRT au MVP). IRT en cible phase 2 conditionnelle B2G.
- **Granularité** : 1 nœud = 1 geste cognitif + 1 contrainte procédurale max. Variation de stratégie → nouveau nœud. Variation de contexte → tag d'item. **1 item = 1 compétence** (strict).
- **Mesure propagée** par le graphe de prérequis (arêtes HARD/SOFT pondérées, poids experts puis ré-estimés). Propagation 1-saut au MVP.
- **Matière pluggable** : le moteur est neutre vis-à-vis de la matière (difficulté injectable). Voir `02_technique/Architecture-Matiere-Pluggable.md`.
- **Curriculum** = étiquette de surface (phase 2 via mapping RAG), pas la fondation. Référentiel neutre d'abord.
- **Go-to-market** : B2B écoles privées d'abord, B2G (subvention) enclenché vite. Personas-roadmap : admin pédagogique, enseignant, parent, élève. RBAC à 6 rôles.
- **Hébergement** : Oracle Cloud (OCI) région UAE — free tier dev, résidence GCC, briques portables (anti-lock-in) pour migrer vers cloud souverain si un B2G l'exige (Core42 en réserve).
- **Sécurité** : deal-breakers = résidence données GCC, isolation tenant, chiffrement. SOC2/ISO = roadmap, pas V1. Garde-fou IA : aucune donnée élève identifiable dans un prompt LLM.
- **Bilingue AR/EN avec RTL** dès le MVP.

## Stack
FastAPI + Postgres (SQLAlchemy 2.0 + Alembic) + Next.js 14. Hébergement OCI UAE. Dev/CI sur SQLite. Production en "human piloting Claude/Cursor".

## Méthode de travail
- Backlog en format "AI Task" : objectif + inputs + contraintes anti-débordement + critères d'acceptation testables. Règle : 1 AI Task = 1 sortie de code vérifiable + 1 fichier de test + 0 débordement fonctionnel.
- Backlog figé d'un coup, exécution ticket par ticket.
- Conventions DB : UUID PK, timestamptz, enums Postgres natifs, soft delete, FK ON DELETE explicite.

## Comment je veux que tu m'assistes
- Direct, data-driven, franc. Propose des options ou une position tranchée d'abord, affine ensuite. Pas de hedging, pas de sur-questionnement.
- Challenge-moi quand mon raisonnement est faible ou quand je confonds deux choses. Ne laisse pas passer une erreur structurante.
- Garde le cadrage business/technique. Évite le registre psychologique.
- Sépare toujours MVP de phase 2+. Empêche le sur-engineering et la dispersion (multi-curriculum, multi-matière, features hors backlog).

## État d'avancement (au 2026-06-21)
- ✅ PRD, data model, backlog (25 tâches / 6 epics), référentiel fractions (32 nœuds figés).
- ✅ Brief de product design complet.
- ✅ **MVP backlog intégralement livré et testé — 149 tests verts.** Détail :
  - **Epic 1** (référentiel) : modèles, validateur DAG, seed — 32 compétences en base.
  - **Epic 2** (banque d'items) : pipeline génération + revue + validation AR + quarantaine ; **banque déterministe de 300 items bilingues** (299 actifs).
  - **Epic 3** (moteur Elo) : update Elo + confiance + propagation 1-saut, orchestrateur `on_response` transactionnel, simulation de cohorte (ability ≈ ±95 Elo, calibration ≈ 0.84).
  - **Epic 4** (session adaptative) : sélection + règles d'arrêt + API FastAPI (sessions / next-item / responses), correction côté serveur.
  - **Epic 5** (restitution) : agrégation, échelle/restitution, **diagnostic causal**, vues enseignant + admin (scopées RBAC), remédiation post-mesure.
  - **Epic 6** (socle) : hiérarchie tenant org→école→classe→élève, RBAC 6 rôles vérifié serveur, MFA + périmètre OIDC.
  - **En plus du périmètre initial** : audit log append-only multi-tenant (migration 0007) ; **front Next.js bilingue RTL fonctionnel** (`04_code/web/`, 5 personas) branché sur l'API ; base démo provisionnée (1 école, 12 élèves, sessions de démo).
- ▶️ **Phase en cours** : polish du front (voir Brief-Product-Design) + préparation pilote (durcissement Postgres Oracle UAE, calibration cohorte réelle).
- ⏳ **Open questions encore ouvertes** (bas du backlog) : table d'ancrage trajectoire (barème expert → cohorte réelle), seuils exacts (quarantaine / ré-estimation poids / arrêt session), choix LLM AR souverain (ALLaM/Jais local vs Claude) si la remédiation s'appuie un jour sur des données d'usage.

## Threads de ce projet
1. Stratégie & décisions · 2. Dev Moteur & Data · 3. Product Design · 4. Dev Front & API · 5. Infra & Sécu · 6. Pitch B2B/B2G.
Garder chaque thread focalisé. Le scinder s'il devient lourd.
