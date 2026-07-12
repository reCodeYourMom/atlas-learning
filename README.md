# Atlas Learning — Dossier Produit MVP

Plateforme d'évaluation adaptative K-12 (vertical fractions), marché GCC, SaaS B2B → B2G.
État au 2026-06-21 : stratégie figée. **MVP de bout en bout codé et testé** — les 6 epics du backlog sont livrés (149 tests verts), banque de 300 items bilingues, et un front Next.js bilingue branché sur l'API tourne sur une base démo provisionnée. Phase en cours : polish du front et préparation pilote.

## Comment naviguer ce dossier

### 01_strategie/ — le quoi / pourquoi / pour qui
- **PRD-Atlas-Learning.md** — document de cadrage central. Problème, 3 couches (moteur Elo / référentiel neutre / restitution-trajectoire), personas + RBAC (6 rôles), parcours, sécurité & conformité (matrice deal-breaker), hébergement Oracle UAE. **À lire en premier.**
- **Design-Starter-Inventaire-Ecrans.md** — point de départ rapide du front : inventaire d'écrans par persona, contraintes (AR/EN + RTL), le parcours qui porte la démo.
- **Brief-Product-Design.md** — **le brief complet de product design.** Mission, principes, fiches personas orientées design, direction artistique proposée (couleur, typographie bilingue, data-viz), section RTL approfondie, specs écran par écran, design system à produire, livrables attendus. **À lire pour piloter toute la phase design.**

### 02_technique/ — comment c'est construit
- **DataModel-KnowledgeGraph.md** — schéma de données complet (Postgres/SQLAlchemy). Moteur Elo + propagation par prérequis, règle de granularité, calibration des poids, isolation tenant. Les formes de données affichées par le front viennent d'ici.
- **Backlog-AITasks.md** — 25 tâches de dev sur 6 epics, format "AI Task" (prompt + critères d'acceptation testables). **Les 6 epics sont livrés** (voir code) ; le backlog sert désormais de référence/historique des critères d'acceptation.
- **Architecture-Matiere-Pluggable.md** — architecture qui rend le moteur neutre vis-à-vis de la matière (difficulté pluggable), au-delà des fractions.
- **SSO-Perimetre.md** — périmètre OIDC/MFA retenu pour le gate d'achat pilote.

### 03_referentiel/ — la matière pédagogique
- **Referentiel-Fractions.md** — table de travail des 32 micro-compétences fractions (G2→G5), prérequis HARD/SOFT, poids experts, contextes d'items. Figé pour le MVP.
- **referentiel_fractions.json** — même contenu, format machine (consommé par le seed).

### 04_code/ — le MVP exécutable (6 epics livrés, 149 tests verts)
- **src/models/** — modèles SQLAlchemy des 6 epics : référentiel, item, mesure (Elo), session, org/tenant, audit + enums.
- **src/graph/validator.py** — validateur DAG anti-cycle (fonction pure).
- **src/engine/** — moteur de mesure : `elo.py` (update Elo + confiance + propagation 1-saut), `service.py` (orchestrateur `on_response` transactionnel), `selection.py` (sélection adaptative), `stopping.py` (règles d'arrêt).
- **src/items/** — pipeline banque d'items : `generation.py`, `deterministic.py`, `difficulty.py`, `review.py`, `arabic.py`, `quarantine.py`.
- **src/restitution/** — `aggregate.py`, `scale.py`, `diagnosis.py` (diagnostic causal), `remediation.py`.
- **src/rbac/** — `auth.py` (login/MFA), `authz.py` (6 rôles, isolation tenant vérifiée serveur).
- **src/api/** — API FastAPI (`app.py`) : login, sessions/next-item/responses, gaps classe, profil/trajectoire élève, remédiation, overview école.
- **src/audit.py** — journalisation append-only multi-tenant.
- **scripts/** — seed référentiel, génération + traduction AR + validation de la banque, simulation de cohorte, provisioning de la base démo, MFA.
- **web/** — front **Next.js 14 bilingue AR/EN (RTL natif)**, branché sur l'API : pages élève / enseignant / admin pédagogique / parent / admin IT + composants diagnostic, restitution, remédiation, data-viz.
- **tests/** — **149 tests** (un par critère d'acceptation), tous verts.
- **atlas_bank.db** — base démo SQLite provisionnée : 32 compétences, 300 items (299 actifs), 1 école, 12 élèves, sessions + réponses de démo.

**Mise en route (dev)** — depuis `04_code/` :
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head                 # crée toutes les tables + enums (SQLite dev par défaut)
.venv/bin/python scripts/seed_referentiel.py   # peuple 32 nœuds + arêtes (idempotent)
.venv/bin/python -m pytest -q                   # 149 tests
.venv/bin/python -m uvicorn src.api.app:app --port 8000   # API ; front : cd web && npm run dev
```
En prod : exporter `DATABASE_URL=postgresql+psycopg://…` (Postgres Oracle UAE) avant les mêmes commandes.

## État d'avancement

| Bloc | État |
|---|---|
| Stratégie produit (PRD) | ✅ Figé |
| Sécurité & hébergement (Oracle UAE) | ✅ Tranché |
| Data model + moteur (conception) | ✅ Figé |
| Référentiel fractions (32 nœuds) | ✅ Figé |
| Backlog dev (25 tâches) | ✅ Prêt |
| Epic 1 — référentiel en base | ✅ Codé + testé |
| Epic 2 — banque d'items | ✅ Pipeline complet (T2.1→T2.5) + **banque déterministe 300 items** (math exacte, 300/300 juge LLM) + **difficulté par item** (archi matière pluggable, voir `02_technique/Architecture-Matiere-Pluggable.md`). Validé Postgres |
| Epic 3 — moteur Elo | ✅ T3.1-T3.5 : update Elo + confiance + propagation 1-saut (pur, neutre matière) · orchestrateur on_response transactionnel · simulation cohorte (ability ±95 Elo, calib 0.84). Validé Postgres |
| Epic 4 — session adaptative | ✅ T4.1 sélection + T4.2 arrêt (purs) · T4.3 API FastAPI (sessions/next-item/responses) + UI bilingue RTL/LTR · correction côté serveur. Validé Postgres (boucle réelle) |
| Epic 5 — restitution / dashboards | ✅ T5.1 agrégation · T5.2 restitution · **T5.3 diagnostic causal** · T5.4 vue enseignant + T5.5 vue admin (endpoints scopés RBAC) · T5.6 remédiation |
| Epic 6 — RBAC / SSO / tenant | ✅ T6.1 hiérarchie (org→école→classe→élève) + migration 0006 · T6.2 RBAC 6 rôles vérifié serveur (isolation tenant testée) · T6.3 auth comptes directs + MFA + périmètre OIDC (`02_technique/SSO-Perimetre.md`). Validé Postgres |
| Audit log (sécu V1) | ✅ `audit_log` (migration 0007) append-only, tenant ; journalise sessions/réponses/accès vues/validation AR. Validé Postgres |
| Génération AR industrielle (ALLaM) | ✅ batch `translate_bank_ar.py` + contrôle fidélité math déterministe (`check_ar_fidelity.py`) + file linguiste (`review_items.py ar-pending`) |
| Front Next.js bilingue (web/) | ✅ Fonctionnel — 5 personas (élève/enseignant/admin péda/parent/admin IT), RTL natif, branché sur l'API. Reste : polish design (voir Brief-Product-Design) |

## Prochaine étape selon ton axe

- **Si tu polis le front** → `Brief-Product-Design.md` + `Design-Starter-Inventaire-Ecrans.md` ; le squelette fonctionnel existe dans `04_code/web/`, priorité au parcours « vue classe → diagnostic causal ».
- **Si tu prépares le pilote** → données démo déjà provisionnées (`scripts/provision_demo.py`) ; durcir Postgres Oracle UAE, calibration sur cohorte réelle, et les *open questions* du bas du backlog (table d'ancrage, seuils, LLM AR souverain).
- **Si tu étends la matière** → `02_technique/Architecture-Matiere-Pluggable.md` (le moteur est déjà neutre).
