# Atlas Learning — Backlog AI Tasks (format "human piloting Claude")

**Statut** : ✅ Livré — les 6 epics (25 tâches) sont codés et testés (149 tests verts au 2026-06-21). Ce backlog sert désormais de référence des critères d'acceptation et d'historique ; il n'est plus un reste-à-faire.
**Date** : créé 2026-06-20 · livré 2026-06-21
**Périmètre MVP figé** : vertical Fractions, **32 nœuds** (seedés), **300 items** bilingues (299 actifs ; cible initiale ~420), moteur Elo + propagation 1-saut.
**Stack** : FastAPI + Postgres (SQLAlchemy 2.0 + Alembic) + Next.js, hébergement Oracle OCI UAE.

> **Réalisé (2026-06-21)** : Epic 1 ✅ · Epic 2 ✅ (banque déterministe 300 items + AR) · Epic 3 ✅ (Elo + propagation + simulation cohorte) · Epic 4 ✅ (sélection/arrêt + API session) · Epic 5 ✅ (agrégation, restitution, diagnostic causal, vues enseignant/admin, remédiation) · Epic 6 ✅ (tenant + RBAC 6 rôles + MFA/OIDC). En plus du périmètre initial : audit log append-only (migration 0007) et front Next.js bilingue fonctionnel (`04_code/web/`). Restent ouvertes les *open questions* en bas de doc (table d'ancrage, seuils, LLM AR souverain).

## Comment utiliser ce backlog

Chaque tâche est un **prompt prêt à coller** dans Claude/Cursor. Structure :
- **Objectif** : l'action technique précise.
- **Inputs** : ce dont l'IA a besoin pour démarrer (docs, schémas, données).
- **Contraintes** : les garde-fous (périmètre, anti-sur-engineering).
- **AC** : critères d'acceptation testables (entrée → sortie attendue). Coller les AC dans l'IA avec « écris le test qui prouve chaque AC ».

Ordre de construction : Epic 1 → 2 (socle data, sans dépendance) puis 3 (moteur) → 4 (session) → 5 (restitution). Epic 6 (RBAC/SSO) en parallèle, non bloquant pour la démo.

**Règle opératoire** : 1 AI Task = 1 sortie de code vérifiable + 1 fichier de test + 0 débordement fonctionnel. Backlog figé d'un coup, exécution ticket par ticket avec validation stricte à chaque étape.

Référence permanente : `DataModel-KnowledgeGraph.md` (le schéma fait foi).

---

## EPIC 1 — Référentiel (graphe fractions)

But : avoir les ~35 nœuds + arêtes pondérées (poids experts) en base, validés DAG.

### T1.1 — Modèles SQLAlchemy du référentiel

**Objectif** : créer les modèles `Competency` et `CompetencyPrerequisite` + enums associés, conformes au data model.

**Inputs** : `DataModel-KnowledgeGraph.md` §3.

**Contraintes** :
- Suivre les conventions projet : UUID PK, `timestamptz`, enums Postgres natifs, soft delete `deleted_at`, FK `ON DELETE` explicite.
- Enums à créer : `Subject` (MATH), `CognitiveLevel` (RECALL/APPLY/REASON), `CompetencyStatus` (draft/active/deprecated), `EdgeType` (HARD/SOFT), `WeightSource` (expert/empirical).
- `competency_prerequisite` : PK composite `(source_id, target_id)`, champs `correlation_strength`, `weight_source`, `weight_version`.
- NE PAS coder le moteur ni l'API ici. Modèles + migration Alembic seulement.

**AC** :
1. `alembic upgrade head` crée les 2 tables + enums sans erreur.
2. Insérer une `competency` avec `code` dupliqué → violation contrainte `unique`.
3. Insérer une arête `(A, A)` (auto-référence) → rejetée par un check applicatif ou contrainte.
4. Insérer une arête dont `source_id` n'existe pas → violation FK.
5. Soft delete : `deleted_at` renseigné → la ligne reste en base, requête filtrée par défaut ne la retourne pas.

### T1.2 — Validateur DAG (anti-cycle)

**Objectif** : fonction qui vérifie que l'ajout d'une arête ne crée pas de cycle dans le graphe de prérequis.

**Inputs** : modèles T1.1.

**Contraintes** :
- Fonction pure testable : `would_create_cycle(edges: list[tuple], new_edge: tuple) -> bool`.
- Algo DFS coloration (white/gray/black). Pas de dépendance externe lourde (pas de networkx pour ça).
- À appeler avant tout insert d'arête côté service.

**AC** :
1. Graphe `A→B→C`, ajouter `C→A` → retourne `True` (cycle).
2. Graphe `A→B`, `A→C`, ajouter `B→C` → retourne `False` (DAG valide, diamant OK).
3. Graphe vide, première arête `A→B` → `False`.
4. Auto-boucle `A→A` → `True`.

### T1.3 — Seed du référentiel fractions

**Objectif** : script de seed qui peuple les ~35 nœuds du vertical fractions + leurs arêtes avec poids experts.

**Inputs** : la liste de nœuds/arêtes fournie (étendre l'échantillon des 14 nœuds existants jusqu'à ~35, couvrant partages → équivalences → addition même dénom → PPCM → addition dénom différents, avec scissions par geste cognitif selon la règle de granularité).

**Contraintes** :
- Idempotent : relancer le seed ne duplique pas (upsert sur `code`).
- Tous les poids initiaux `weight_source = expert`, `weight_version = 1`.
- Respecter la règle de granularité : scinder par geste cognitif (ex. `add_same_denom_no_simplify` vs `_simplify`), PAS par contexte.
- Lancer le validateur DAG T1.2 sur l'ensemble avant commit.

**AC** :
1. Après seed : `count(competency WHERE deleted_at IS NULL)` ∈ [30, 40].
2. Le graphe complet passe `would_create_cycle` sans détecter de cycle.
3. Chaque nœud a un `code` unique au format `MATH.G{n}.{STRAND}.{SKILL}`.
4. Relancer le seed → le count ne change pas (idempotence).
5. Tout nœud non-racine a au moins 1 arête entrante (pas de nœud orphelin sauf racines).

---

## EPIC 2 — Banque d'items (~420 items)

But : pipeline de génération + revue + validation AR produisant les items calibrables, 1 item = 1 compétence.

### T2.1 — Modèle SQLAlchemy de l'item

**Objectif** : créer le modèle `Item` + enums, conforme au data model.

**Inputs** : `DataModel-KnowledgeGraph.md` §4.

**Contraintes** :
- `competency_id` unique par item (FK `ON DELETE RESTRICT`). PAS de secondary_skill.
- `content_en` / `content_ar` en JSONB ; `context_tags` JSONB ; `provenance` JSONB.
- Enums : `ItemStatus` (ai_generated/human_reviewed/linguist_validated/active/quarantined), `AnswerFormat` (MCQ/NUMERIC/SHORT).
- Modèle Pydantic `ItemContent` (stem, options, answer) pour valider le JSONB à l'écriture.

**AC** :
1. Migration crée la table + enums sans erreur.
2. Insérer un item dont `content_en` ne respecte pas `ItemContent` → rejet à la validation Pydantic.
3. `difficulty_elo` par défaut = `difficulty_prior` à la création.
4. Supprimer une `competency` ayant un item vivant → bloqué par RESTRICT.
5. `context_tags` accepte un dict arbitraire et le stocke/relit sans perte.

### T2.2 — Pipeline de génération d'items (Claude)

**Objectif** : fonction qui génère N items pour une compétence donnée via l'API Claude, en sortie structurée prête à insérer.

**Inputs** : un `competency` (code, label, cognitive_level, difficulty_prior) + un set de `context_tags` cibles à couvrir.

**Contraintes** :
- **Garde-fou IA (sécu)** : le prompt ne contient AUCUNE donnée élève. Compétence + contexte seulement.
- Sortie JSON strict (stem, options, answer, format) — parser et valider via `ItemContent`. Pas de texte libre.
- Statut initial `ai_generated`, `provenance` trace le modèle + l'id de prompt.
- Générer en EN d'abord ; l'AR vient en T2.4.
- NE PAS insérer en base ici : la fonction retourne des objets validés, l'insertion est une étape séparée (revue T2.3 d'abord).

**AC** :
1. Pour une compétence donnée, génère N items dont chacun parse en `ItemContent` valide.
2. Chaque item généré porte le `competency_id` de la compétence demandée (1:1).
3. Les `context_tags` demandés sont couverts (ex. au moins 1 item `simplify=true` et 1 `simplify=false` si demandé).
4. Un item au format MCQ a ≥ 2 options et une `answer` ∈ options.
5. Aucune fuite : le prompt envoyé ne contient aucun identifiant élève (vérifiable sur le log de prompt).

### T2.3 — Workflow de revue humaine

**Objectif** : interface/CLI minimale pour qu'un humain (toi) revoie les items `ai_generated` et les promeuve en `human_reviewed` ou les rejette.

**Inputs** : items générés T2.2.

**Contraintes** :
- Périmètre minimal : lister les items à revoir, afficher stem/answer, action approuver/rejeter/éditer.
- Une transition de statut ne saute pas d'étape (ai_generated → human_reviewed, pas → active directement).
- Logger qui a revu (provenance).
- Pas d'usine à gaz UI : CLI ou page admin basique suffit au MVP.

**AC** :
1. Un item `ai_generated` approuvé passe `human_reviewed`.
2. Tenter de promouvoir un item directement de `ai_generated` à `active` → refusé.
3. Un item rejeté est marqué (soft delete ou statut dédié), pas détruit.
4. `provenance` contient l'identité du reviewer après action.

### T2.4 — Validation linguistique AR

**Objectif** : workflow pour que la linguiste valide/corrige `content_ar` et lève `ar_validated`.

**Inputs** : items `human_reviewed`.

**Contraintes** :
- `content_ar` éditable indépendamment de `content_en`.
- `ar_validated = true` requis pour passer `active`.
- Gérer le RTL correctement (stockage + futur affichage).

**AC** :
1. Un item `human_reviewed` avec `ar_validated=false` ne peut PAS passer `active`.
2. Après validation AR, `ar_validated=true` et l'item peut passer `active`.
3. Éditer `content_ar` ne modifie pas `content_en`.

### T2.5 — Promotion en pool actif + garde-fou quarantaine

**Objectif** : logique de promotion d'un item en `active` (servi aux élèves) + mécanisme de mise en `quarantined` automatique.

**Inputs** : items `human_reviewed` + `ar_validated`.

**Contraintes** :
- Passage `active` seulement si `human_reviewed` ET `ar_validated`.
- Quarantaine auto : un item `active` dont les stats divergent (ex. taux de réussite incohérent avec `difficulty_elo` au-delà d'un seuil, après `n_responses` minimal) bascule `quarantined` et sort du pool servi. Implémentation réelle (revue 2026-07-07) : détection = fonction pure (`src/items/quarantine.py`), exécutée en **job planifié** — `scripts/run_quarantine.py` + cron quotidien `deploy/prod/quarantine.cron` — pas de bascule au fil de l'eau à chaque réponse.
- La quarantaine est réversible après revue.

**AC** :
1. Un item sans `ar_validated` ne peut pas passer `active`.
2. Un item `active` avec taux de réussite 95% mais `difficulty_elo` très élevé (incohérent), après ≥ seuil de réponses → passe `quarantined`.
3. Un item `quarantined` n'est pas retourné par la fonction de sélection d'item (Epic 4).
4. En dessous du seuil de réponses, aucun item n'est mis en quarantaine (pas de quarantaine sur du bruit).

---

## EPIC 3 — Moteur de mesure (Elo + propagation)

But : le cœur. Boucle Elo mutuelle élève/item, calibration item **gelée au prior pendant un burn-in puis K décroissant** (cf. T3.1, revue 2026-07-07), propagation 1-saut pondérée, confiance. Toutes les valeurs Elo sont bornées dans [0–4000] (`clamp_elo`). Aucun LLM ici — maths pures, déterministe, testable au chiffre près.

### T3.1 — Fonction de mise à jour Elo (élève × item)

**Objectif** : fonction pure qui, pour une réponse, calcule le nouvel `ability_elo` de l'élève et le nouveau `difficulty_elo` de l'item.

**Inputs** : `ability` (float), `item_difficulty` (float), `is_correct` (bool), `n_direct_student` (int), `n_responses_item` (int). Échelle [0–4000] centrée 1500.

**Contraintes** :
- Fonction pure : `update_elo(ability, item_difficulty, is_correct, n_direct, n_resp_item) -> (new_ability, new_item_difficulty)`.
- K élève adaptatif : 32 si `n_direct < 10`, sinon 16.
- K item avec **burn-in** (revue 2026-07-07, `src/engine/elo.py`) : `K_item = 0` tant que `n_resp_item < ITEM_BURN_IN = 20` — la difficulté reste **gelée au `difficulty_prior`** (le prior, calibré par le générateur déterministe, est plus fiable qu'une poignée de réponses bruitées ; un K simplement réduit dériverait encore sur une petite cohorte biaisée). À la sortie du burn-in : `K_item = 32 / (1 + n_resp_item / 30)` (≈ 19.2 à n=20), décroissant ensuite.
- **Clamp** : `new_ability` et `new_item_difficulty` sont bornées dans [0, 4000] (`clamp_elo` — anti-dérive sur longue série : triche, bug client, rejeu).
- L'item bouge en sens inverse de l'élève (somme à zéro pondérée — hors burn-in et hors clamp, cf. AC6).
- PAS de propagation ici (T3.3). PAS d'accès DB (fonction pure).

**AC** :
1. `ability=1500, difficulty=1500, correct=True, n_direct=0` → expected=0.5, delta=+16, new_ability=1516.
2. Même entrée, `correct=False` → new_ability=1484.
3. `n_direct=20` (élève stabilisé) → K=16 utilisé, l'amplitude du delta est moitié de celle à K=32.
4. `n_resp_item < 20` (burn-in) → K_item = 0, la difficulté ne bouge PAS (gelée au prior) ; `n_resp_item=30` → K_item = 16 (item sorti du burn-in, calibration décroissante).
5. Élève très fort (2500) répond juste à item facile (1000) → delta quasi nul (expected≈1).
6. Propriété : new_ability + new_item_difficulty conservent la masse selon la pondération définie (test d'invariant `Δability/K_student + Δdifficulty/K_item == 0`) — exigée UNIQUEMENT hors burn-in (K_item > 0) et hors saturation du clamp [0–4000] (au clamp, borner prime sur conserver).

### T3.2 — Mise à jour de la confiance

**Objectif** : fonction qui calcule la `confidence` d'une ability en fonction du nombre de réponses directes.

**Inputs** : `n_direct` (int).

**Contraintes** :
- `confidence(n_direct) = 1 - exp(-n_direct / 8)`, bornée [0, 1].
- Fonction pure.

**AC** :
1. `n_direct=0` → confidence=0.0.
2. `n_direct=8` → confidence ≈ 0.63 (±0.01).
3. `n_direct=10` → confidence ≈ 0.71 (±0.01).
4. Monotone croissante : `confidence(n) < confidence(n+1)` pour tout n.
5. Tend vers 1 sans jamais l'atteindre (n=100 → > 0.99).

### T3.3 — Propagation 1-saut

**Objectif** : après mise à jour directe d'une compétence, propager un delta amorti aux voisins (prérequis + dépendants) via les arêtes, pondéré par `correlation_strength`.

**Inputs** : `competency_id` touchée, `delta` de l'update direct, liste des arêtes voisines (avec `correlation_strength`, `edge_type`), abilities/confidences actuelles des voisins.

**Contraintes** :
- 1 saut uniquement (voisins directs). PAS de propagation transitive au MVP.
- `propagated_delta = delta * correlation_strength * DAMPING`, DAMPING=0.4.
- Ne PAS écraser une mesure plus sûre : ne propager vers un voisin que si `confidence(voisin) < confidence(source)`.
- La propagation n'incrémente PAS `n_direct` du voisin (c'est de l'inféré, pas du mesuré).
- Asymétrie : propagation vers prérequis (descendante) autorisée pleine ; vers dépendants (montante) plus faible — encodée par `correlation_strength` des arêtes concernées.

**AC** :
1. Source confiance 0.7, voisin confiance 0.2, arête strength 0.8, delta +16 → voisin reçoit +16×0.8×0.4 = +5.12.
2. Voisin déjà plus sûr (confiance 0.9 > source 0.7) → voisin NON modifié.
3. `n_direct` du voisin inchangé après propagation.
4. Compétence sans voisin → aucune propagation, aucune erreur.
5. Propagation ne touche QUE les voisins directs (un voisin-de-voisin n'est pas modifié).

### T3.4 — Orchestrateur on_response (transaction)

**Objectif** : fonction service qui, à la réception d'une réponse, enchaîne : écrire la `response`, update Elo direct (T3.1), update confiance (T3.2), propagation (T3.3), le tout en une transaction.

**Inputs** : `student_id`, `item_id`, `is_correct`, `response_time_ms`, `session_id`, `school_id`.

**Contraintes** :
- Une transaction atomique : si une étape échoue, rollback complet (pas d'état partiel).
- `response` est append-only.
- Isolation tenant : toutes les écritures portent `school_id`.
- Charger les voisins via le graphe (selectinload, éviter N+1).
- Idempotence raisonnable : rejouer exactement la même réponse (même id) ne double pas l'effet. Implémentation réelle (revue 2026-07-07) : `response_id` **dérivé `uuid5(session_id, item_id)`** + contrainte unique `(session_id, item_id)` sur `response` → un rejeu ne réapplique rien (409 côté API).
- Concurrence (revue 2026-07-07) : les lignes lues-puis-écrites (item, abilities élève et voisins) sont verrouillées par SELECT … FOR UPDATE en **ordre déterministe** (item d'abord, puis abilities triées par `competency_id`) — sinon read-modify-write last-write-wins en READ COMMITTED sur les items populaires.

**AC** :
1. Une réponse correcte crée 1 ligne `response`, met à jour l'ability directe ET l'item.
2. Si la propagation lève une exception → la `response` n'est PAS committée (rollback).
3. Les abilities des voisins éligibles sont mises à jour dans la même transaction.
4. Toutes les lignes créées portent le bon `school_id`.
5. La fonction ne fait aucun appel LLM (vérifiable : zéro appel réseau sortant).

### T3.5 — Données synthétiques + réglage des paramètres

**Objectif** : générer une cohorte synthétique d'élèves de niveaux connus, simuler des réponses, vérifier que le moteur retrouve les niveaux et que les difficultés d'items convergent.

**Inputs** : le référentiel seedé (Epic 1), un pool d'items à difficulté connue (Epic 2 ou items factices).

**Contraintes** :
- Élèves synthétiques avec « vraie » ability cachée ; réponses tirées selon la proba Elo.
- Mesurer l'erreur entre ability estimée et ability vraie après N réponses.
- Sert à régler K, τ, DAMPING avant le pilote réel. Script de simulation, pas du code de prod.

**AC** :
1. Après ~30 réponses/élève, l'ability estimée est à ±150 points Elo de la vraie ability (médiane).
2. La `difficulty_elo` des items converge vers leur difficulté vraie (corrélation > 0.8 après trafic suffisant).
3. La propagation réduit l'erreur sur les compétences peu testées vs un baseline sans propagation (comparaison chiffrée).
4. Aucun item ne part en quarantaine à tort sur des données cohérentes.

---

## EPIC 4 — Session adaptative

But : sélectionner le bon item, faire passer une session élève bilingue AR/EN, savoir quand s'arrêter.

### T4.1 — Sélection d'item adaptative

**Objectif** : fonction qui choisit le prochain item à servir : difficulté ≈ ability de l'élève sur la compétence visée, priorité aux compétences à faible confiance.

**Inputs** : `student_id`, compétence(s) candidate(s), pool d'items `active`, historique récent (pour ne pas répéter).

**Contraintes** :
- Cible : item dont `difficulty_elo` est le plus proche de l'`ability` de l'élève (max d'information).
- Exclure les items `quarantined`, déjà vus récemment dans la session.
- Prioriser les compétences à `confidence` basse (on mesure d'abord ce qu'on connaît mal).
- Respecter les prérequis HARD non maîtrisés : ne pas servir une compétence dont un prérequis HARD est clairement échoué (rediriger vers le prérequis).
- Fonction pure côté logique de choix (l'accès DB est séparé).

**AC** :
1. Élève ability 1600 → l'item choisi a la `difficulty_elo` la plus proche de 1600 parmi les éligibles.
2. Un item `quarantined` n'est jamais sélectionné.
3. Un item déjà vu dans la session courante n'est pas resélectionné tant qu'il reste des alternatives.
4. Compétence dont un prérequis HARD est échoué (ability très basse) → le moteur propose d'abord le prérequis.
5. À confiances égales, la compétence la moins testée (n_direct plus bas) est priorisée.

### T4.2 — Règles d'arrêt de session

**Objectif** : déterminer quand une session/diagnostic doit s'arrêter (assez d'information ou limite atteinte).

**Inputs** : état de confiance des compétences visées, nombre d'items déjà servis, temps.

**Contraintes** :
- Arrêt si confiance cible atteinte sur les compétences visées, OU plafond d'items atteint, OU temps écoulé.
- Paramètres en config (pas en dur).
- Fonction pure.

**AC** :
1. Toutes les compétences visées atteignent confiance ≥ seuil → arrêt = True.
2. Plafond d'items atteint avant la confiance → arrêt = True (raison = plafond).
3. Aucune condition remplie → arrêt = False.
4. La raison d'arrêt est retournée (confiance / plafond / temps).

### T4.3 — API de session + interface élève AR/EN

**Objectif** : endpoints FastAPI pour démarrer une session, servir un item, soumettre une réponse ; UI élève Next.js bilingue RTL/LTR.

**Inputs** : T4.1, T4.2, T3.4.

**Contraintes** :
- Endpoints : `POST /sessions`, `GET /sessions/{id}/next-item`, `POST /sessions/{id}/responses`.
- L'UI gère RTL (arabe) et LTR (anglais) ; bascule de langue propre.
- Aucune donnée élève identifiable envoyée à un service externe.
- UI minimale fonctionnelle, pas léchée au MVP (la beauté vient après la preuve moteur).

**AC** :
1. `POST /sessions` crée une session liée à l'élève + school_id.
2. `GET next-item` retourne un item éligible (jamais quarantined/déjà-vu).
3. `POST responses` déclenche `on_response` (T3.4) et retourne l'item suivant ou la fin de session.
4. L'UI affiche correctement un item AR en RTL et un item EN en LTR.
5. Soumettre une réponse à un item déjà répondu dans la session → rejet propre (pas de double comptage).

---

## EPIC 5 — Restitution & dashboards

But : transformer les abilities en valeur visible — diagnostic causal explicable, vues enseignant et admin pédagogique.

### T5.1 — Agrégation des abilities (compétence → strand → matière)

**Objectif** : fonction qui agrège les `ability_elo` par compétence en scores de niveau supérieur (strand, matière), pondérés par confiance.

**Inputs** : abilities d'un élève, structure du graphe (strands).

**Contraintes** :
- Agrégation pondérée par confiance (une ability peu sûre pèse moins).
- Distinguer mesuré vs inféré dans le rendu.
- Fonction pure.

**AC** :
1. Un élève avec toutes compétences d'un strand à 1800 → score strand ≈ 1800.
2. Une ability à confiance 0.1 influence le score agrégé bien moins qu'une à confiance 0.9.
3. Un strand sans aucune mesure directe → marqué « estimé » et non « mesuré ».

### T5.2 — Couche de restitution (percentile + niveau + projection)

**Objectif** : convertir l'ability Elo interne en restitution lisible : percentile, équivalent niveau scolaire, bande de trajectoire.

**Inputs** : ability agrégée, table d'ancrage (au départ : barème expert ; à terme : cohorte réelle).

**Contraintes** :
- Séparer strictement moteur (Elo) et restitution (échelle client).
- L'ancrage trajectoire-supérieur est une table de correspondance configurable, pas en dur.
- Afficher un intervalle quand la confiance est basse (honnêteté : estimation vs mesure).

**AC** :
1. Une ability donnée produit un percentile déterministe selon la table d'ancrage.
2. Changer la table d'ancrage change la restitution sans toucher au moteur.
3. Confiance basse → la restitution affiche une fourchette, pas un point.

### T5.3 — Diagnostic causal (le « waw »)

**Objectif** : pour une compétence en lacune, remonter la chaîne de prérequis HARD non maîtrisés pour expliquer POURQUOI l'élève bloque.

**Inputs** : abilities de l'élève, graphe de prérequis.

**Contraintes** :
- Remonter les arêtes HARD : trouver le(s) prérequis non maîtrisé(s) le(s) plus en amont. Implémentation réelle (revue 2026-07-07, `src/restitution/diagnosis.py`) : exploration de la **clôture amont COMPLÈTE** des prérequis HARD (tous les ancêtres transitifs, protection cycles) — la maîtrise n'étant pas monotone le long du graphe, une remontée branche par branche dépendait de l'ordre DB et ratait la vraie racine. Un ancêtre jamais estimé n'est jamais désigné racine.
- Produire une explication structurée (« bloque sur X parce que Y, prérequis de X, n'est pas maîtrisé »).
- Fonction pure (le rendu UI est séparé).

**AC** :
1. Élève maîtrisant tout sauf « add_unlike_denom » et son prérequis « equivalence_compute » → le diagnostic pointe equivalence_compute comme cause racine.
2. Si plusieurs prérequis manquent, le diagnostic remonte au plus en amont (la vraie racine).
3. Compétence en lacune sans prérequis manquant → diagnostic = « lacune sur la compétence elle-même », pas de fausse cause.

### T5.4 — Vue enseignant (classe actionnable, F6b)

**Objectif** : endpoint + UI montrant à l'enseignant les lacunes prioritaires de SA classe, sans correction manuelle.

**Inputs** : abilities agrégées des élèves de la classe, diagnostic causal T5.3.

**Contraintes** :
- Vue scopée à la classe de l'enseignant (RBAC).
- Mettre en avant les lacunes les plus partagées (où concentrer le cours).
- Permettre de déclencher la remédiation (lien vers Epic remédiation/F7).
- Zéro correction manuelle exigée de l'enseignant.

**AC** :
1. L'enseignant ne voit QUE les élèves de ses classes (test d'isolation RBAC).
2. Les compétences en lacune sont triées par fréquence dans la classe.
3. Chaque lacune affiche son diagnostic causal (T5.3).

### T5.5 — Vue admin pédagogique (établissement, F6a)

**Objectif** : endpoint + UI agrégeant les outcomes au niveau école/classe pour le décideur.

**Inputs** : abilities agrégées établissement.

**Contraintes** :
- Vue agrégée (pas le détail élève par défaut) : maîtrise par classe, par compétence, tendances.
- Scopée à l'établissement (RBAC + tenant).
- Pensée pour le reporting familles + régulateur.

**AC** :
1. L'admin voit l'agrégat de toutes les classes de son établissement, pas d'un autre.
2. Les données sont agrégées (pas de PII élève exposée par défaut dans cette vue).
3. Export possible d'un rapport synthétique.

### T5.6 — Remédiation ciblée (F7, génération post-mesure)

**Objectif** : à partir d'une lacune diagnostiquée, générer via Claude un exercice de remédiation ciblé sur la compétence.

**Inputs** : compétence en lacune (T5.3), contexte de difficulté.

**Contraintes** :
- Génération APRÈS mesure, jamais pour la mesure.
- **Garde-fou IA** : prompt sans donnée élève identifiable (compétence + niveau de difficulté seulement).
- Servir d'abord le prérequis HARD racine si c'est lui la cause (cohérent avec T5.3).
- Pilotable/visible par l'enseignant.

**AC** :
1. Lacune sur une compétence → exercice généré ciblant cette compétence (ou son prérequis racine).
2. Le prompt de génération ne contient aucun identifiant élève (vérifiable sur le log).
3. L'exercice généré passe la validation `ItemContent` (réutilise le pipeline T2).

---

## EPIC 6 — Socle RBAC / SSO / tenant (gate d'achat, non bloquant démo)

But : le minimum pour signer une école, sans sur-investir. En parallèle des autres epics.

### T6.1 — Modèle organisation / école / classe / utilisateur + tenant

**Objectif** : modèles SQLAlchemy pour la hiérarchie tenant et les utilisateurs, avec scoping `school_id` partout où il y a de la donnée élève.

**Inputs** : `DataModel-KnowledgeGraph.md` §2.

**Contraintes** :
- Hiérarchie : organization → school → class → student. Users + memberships.
- Toute table de données élève (response, ability) porte `school_id` (déjà au schéma).
- Soft delete sur les entités importantes.

**AC** :
1. Migration crée la hiérarchie sans erreur.
2. Une `response` ne peut être créée sans `school_id` valide.
3. Suppression d'une école → cascade cohérente (ou interdiction explicite selon le sens métier).

### T6.2 — RBAC (6 rôles)

**Objectif** : système d'autorisation appliquant la matrice des 6 rôles (super admin, admin IT, admin pédagogique, enseignant, parent, élève).

**Inputs** : matrice de rôles du PRD.

**Contraintes** :
- Permissions vérifiées côté API (pas seulement masquage UI).
- Parent = lecture seule sur SON enfant. Enseignant = SES classes. Admin pédagogique = SON établissement.
- Décorateur/dépendance FastAPI réutilisable.

**AC** :
1. Un parent qui requête les données d'un autre enfant → 403.
2. Un enseignant qui requête une classe qui n'est pas la sienne → 403.
3. Un élève ne peut accéder qu'à ses propres activités.
4. Un admin pédagogique ne voit pas un autre établissement (test tenant).

### T6.3 — SSO minimal (démo)

**Objectif** : intégration SSO suffisante pour passer le gate d'achat d'un pilote, sans supporter tous les IdP.

**Inputs** : T6.2.

**Contraintes** :
- Un protocole standard (OIDC) suffisant pour la démo ; MFA sur comptes admin/enseignant.
- NE PAS construire un hub multi-IdP au MVP. Un IdP de référence + comptes directs en fallback.
- Documenter le périmètre (pour la conversation DSI).

**AC** :
1. Un utilisateur peut s'authentifier via l'IdP de référence.
2. MFA exigé pour un compte admin.
3. Le fallback compte direct fonctionne pour un pilote sans SSO.

### T6.4 — Back-office localisation manager (validation AR)
**Objectif** : donner à la localization manager une interface dédiée pour relire et **valider** les traductions AR au lieu de passer par les scripts CLI (`review_items.py ar-pending`, `validate-ar`).
**Contexte** : le workflow existe déjà côté backend (`set_arabic`/`validate_arabic`, garde `ar_validated`, flag `ar_math_broken`, audit). Il manque l'UI pour un profil non-technique. Réutilise le RBAC (rôle dédié type `linguist`/`ped_admin`) et l'audit log (qui valide quoi, quand).
**Contraintes** : afficher EN (lecture seule, source de vérité) + AR éditable côté à côte, RTL ; surfacer en priorité les items flaggés `ar_math_broken` ; l'action « valider » pose `ar_validated=True` tracé au nom de l'utilisateur (jamais en masse aveugle) ; ne jamais altérer `content_en`.
**AC** : 1. La localization manager se connecte avec son rôle et ne voit que la file AR à valider (pas de PII élève). 2. Valider un item le fait passer `ar_validated=True` et l'inscrit à l'audit. 3. Les items `ar_math_broken` sont signalés en tête de file. 4. Un item validé devient promouvable vers `active` via le workflow existant.

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
- **T7.4d** — Revue des artefacts `deploy/` (`.env.prod.template`, `verify_deploy.sh`) contre le code.
**AC** : 1. Les 4 livrables produits et reliés à la soumission T7.4. 2. Ordre ci-dessus respecté (domaine + org avant soumission).

---

## Open questions (engineering, hors périmètre immédiat)

- [ ] **LLM pour génération d'items et remédiation** : Claude (cloud, hors GCC) vs LLM arabe local (Jais-70B / ALLaM, hébergeable en région UAE). Trancher quand on industrialise la génération AR et la remédiation (Epic 2.2 / 5.6). Enjeu : un LLM local règle le garde-fou « données hors-GCC » et améliore potentiellement la qualité AR ; Claude reste plus fort en orchestration/raisonnement. Décision conditionnée au volume et aux exigences de souveraineté du premier client. NB : la génération ne contient déjà aucune donnée élève, donc l'enjeu souveraineté est limité au MVP — devient critique si la remédiation s'appuie un jour sur des données d'usage.
- [ ] Échelle Elo définitive et table d'ancrage trajectoire (barème expert initial → cohorte réelle).
- [ ] Seuils exacts : quarantaine item, ré-estimation des poids, arrêt de session.

---

## Backlog produit — issus de la revue crosswalk (05_revue, décisions 2026-07-12)

- [ ] **Métrique de granularité « N gestes Atlas par standard » (C-3)** — argument de vente n°1 : un standard officiel = jusqu'à 5 compétences Atlas mesurées séparément (« là où votre programme voit une case, nous mesurons cinq gestes distincts »). Se calcule trivialement depuis `competency_curriculum_map` (COUNT par `standard_id`). À afficher au **rapport école** et au **one-pager**. Ne touche PAS aux types d'alignement (le type unique par ligne ne peut porter simultanément grain BROADER et grade ENRICH — c'est une métrique dérivée, pas un type). Décidé par le fondateur le 2026-07-12.
