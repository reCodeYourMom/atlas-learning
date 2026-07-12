# Atlas Learning — Data Model du Knowledge Graph (F1 + socle F2)

**Statut** : Draft
**Date** : 2026-06-20
**Stack** : Postgres + SQLAlchemy 2.0 + Alembic (conventions projet : UUID PK, `timestamptz`, enums natifs, FK `ON DELETE` explicite, soft delete via `deleted_at`).
**Convention timestamps (revue 2026-07-07)** : toute colonne timestamp est `DateTime(timezone=True)` (`timestamptz` sur Postgres) et toute valeur est produite par `utcnow()` / normalisée par `ensure_utc()` de `src/models/base.py` (datetimes *aware* UTC) — jamais `datetime.now()` naïf. Les extraits de modèles ci-dessous sont illustratifs ; le code réel (`src/models/`) fait foi.
**Périmètre** : maths primaire, grain (c) micro-skill, mesure Elo propagée par prérequis.

---

## 1. Principe de conception

Deux grains distincts, c'est tout le truc :

- **Grain de modélisation = fin (c)**. Le graphe représente les micro-skills (ex. « additionner des fractions à dénominateurs différents ») et leurs prérequis. C'est de la structure : gratuit, précis.
- **Grain de mesure = propagé**. On ne calibre PAS un Elo indépendant par micro-skill dès J1. Une réponse sur un micro-skill informe ses voisins via les arêtes de prérequis, pondérées par une **force de corrélation**. Le graphe est *actif* : il propage la mesure et casse le cold-start.

Conséquence : les arêtes de prérequis ne sont pas décoratives. Elles portent un poids qui sert l'algorithme de mesure.

### Règle de granularité (normative)

**1 nœud = 1 geste cognitif + 1 contrainte procédurale principale max.**

- Une variation qui change la **stratégie** de résolution → **nouveau nœud**.
  (ex. `add_same_denom_no_simplify` vs `add_same_denom_simplify` : simplifier est un geste à part, avec ses propres prérequis.)
- Une variation qui ne change que le **contexte ou la difficulté** → **tag d'item** (`context_tags`), PAS un nœud.
  (ex. dénominateur 4 vs 8, résultat propre vs impropre sans simplification : même geste, contexte différent.)

Seuil pratique : si un nœud demande **deux stratégies différentes** pour être réussi, le scinder. Si une variation de contexte change **fortement** le taux de réussite, signal de sous-découpage à arbitrer (souvent → tag suffisant ; parfois → scission si c'est une stratégie distincte).

Pourquoi : sépare la **granularité de compétence** (le graphe, lisible et calibrable) de la **variabilité de contexte** (les items, qui portent la finesse). Sans elle, chaque variation devient un nœud → explosion à plusieurs milliers de micro-skills, densité de données par nœud trop faible, production d'items ingérable. Avec elle, le moteur détecte quand même les patterns de difficulté par contexte via les `context_tags`, pas via des nœuds séparés.

**Un item mesure une seule compétence** (`competency_id` unique, cf. §4). Pas de multi-skill au MVP : un item multi-compétences rend le signal Elo ambigu. Rouvrable en phase 2 sous protocole — rare en maths primaire au grain (c).

Trois couches de données :
1. **Référentiel** (compétences + prérequis) — neutre, indépendant de tout curriculum.
2. **Items** (questions calibrées) — 1 item mesure 1 compétence.
3. **État de mesure** (ability Elo par élève × compétence + événements de réponse).

Le **curriculum** n'apparaît pas ici : c'est une couche d'étiquetage projetée en phase 2 (hook prévu §7).

---

## 2. Isolation multi-tenant (deal-breaker sécu)

L'isolation par établissement est dans le schéma, pas patchée après. Toute donnée élève/réponse porte un `school_id`. Le **référentiel et les items sont globaux** (partagés entre écoles, c'est l'actif Atlas) ; seules les **données de mesure** (ability, responses, élèves) sont scopées par école.

```
organization (tenant racine, optionnel multi-écoles)
└── school (frontière d'isolation des données élève)
    └── class
        └── student
```

Référentiel global : `competency`, `competency_prerequisite`, `item`.
Scopé école : `student`, `student_competency_ability`, `response`.

---

## 3. Le référentiel — nœuds & arêtes

### 3.1 `competency` (le nœud, grain c)

```python
class Competency(Base):
    __tablename__ = "competency"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    # ex. "MATH.G4.NF.ADD_UNLIKE_DENOM" — identifiant stable, lisible, versionnable

    label_en: Mapped[str] = mapped_column()
    label_ar: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column()

    subject: Mapped[Subject] = mapped_column()          # enum: MATH (extensible)
    grade: Mapped[int] = mapped_column(index=True)      # 1..6 (primaire)
    cognitive_level: Mapped[CognitiveLevel | None]      # enum optionnel: RECALL/APPLY/REASON — utile à la génération d'items

    difficulty_prior: Mapped[float] = mapped_column()   # difficulté a priori (seed de l'Elo item), échelle Elo ~ [-3, +3] ou [0, 4000]
    status: Mapped[CompetencyStatus] = mapped_column(default="draft")  # draft/active/deprecated

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column()  # soft delete
```

Le `code` structuré (`SUBJECT.GRADE.STRAND.SKILL`) permet de lire le graphe à l'œil et de mapper plus tard sur les curriculums sans dépendre des UUID.

### 3.2 `competency_prerequisite` (l'arête active)

```python
class CompetencyPrerequisite(Base):
    __tablename__ = "competency_prerequisite"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="CASCADE"), primary_key=True)   # le prérequis
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="CASCADE"), primary_key=True)   # le dépendant

    edge_type: Mapped[EdgeType] = mapped_column()        # enum: HARD (dépendance stricte) | SOFT (corrélation sans blocage)
    correlation_strength: Mapped[float] = mapped_column()  # [0..1] — combien maîtriser source prédit maîtriser target
    # C'EST le poids qui propage la mesure.
    weight_source: Mapped[WeightSource] = mapped_column(default="expert")  # enum: expert | empirical
    weight_version: Mapped[int] = mapped_column(default=1)  # incrémenté à chaque ré-estimation — traçabilité + rollback

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

- PK composite `(source_id, target_id)` → pas de doublon d'arête.
- `edge_type = HARD` : on ne fait pas B sans A (sert aussi au routing pédagogique : ne pas servir B si A non maîtrisé).
- `edge_type = SOFT` : corrélation utile à la propagation, sans blocage pédagogique.
- Graphe orienté acyclique (DAG) attendu — prévoir un check anti-cycle à l'insertion (sinon la propagation boucle).

Index : sur `source_id` ET `target_id` séparément (propagation dans les deux sens).

---

## 4. Les items

### 4.1 `item` (1 item = 1 compétence)

Règle stricte : **un item mesure une seule compétence**. Un item multi-compétences pollue le signal Elo (on ne sait plus quelle compétence a fait échouer l'élève).

```python
class Item(Base):
    __tablename__ = "item"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    competency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="RESTRICT"), index=True)
    # RESTRICT : on ne supprime pas une compétence qui a des items vivants.

    content_en: Mapped[dict] = mapped_column(JSONB)     # {stem, format, options[], answer} — validé Pydantic
    content_ar: Mapped[dict] = mapped_column(JSONB)
    answer_format: Mapped[AnswerFormat] = mapped_column()  # enum: MCQ | NUMERIC | SHORT

    difficulty_prior: Mapped[float] = mapped_column()   # estimation initiale
    difficulty_elo: Mapped[float] = mapped_column()     # difficulté vivante — gelée au prior pendant le burn-in (20 rép.), puis auto-corrigée par le trafic (cf. §5.3)
    n_responses: Mapped[int] = mapped_column(default=0) # confiance dans la calibration

    context_tags: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    # variation de contexte SANS créer de nœud. ex. {"simplify": false, "result_type": "improper", "representation": "symbolic", "denominator_max": 8}
    # permet au moteur de détecter des patterns de difficulté par contexte sans fragmenter le graphe.

    status: Mapped[ItemStatus] = mapped_column(default="ai_generated")
    # ai_generated → human_reviewed → linguist_validated → active → quarantined
    provenance: Mapped[dict] = mapped_column(JSONB, server_default="{}")  # trace audit (modèle, prompt id, reviewer)
    ar_validated: Mapped[bool] = mapped_column(default=False)  # validation linguiste native

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column()
```

`content_*` en JSONB typé Pydantic : la forme évolue (formats variés) sans migration à chaque ajout. Validation à l'écriture :

```python
class ItemContent(BaseModel):
    stem: str
    options: list[str] | None = None    # pour MCQ
    answer: str                          # clé de correction
```

**Garde-fou IA (sécu)** : la génération et la validation d'items travaillent sur `competency` + `content`, jamais sur des données élève. Aucun PII dans les prompts.

**Statut `quarantined`** : un item dont la `difficulty_elo` dérive de façon aberrante (ex. taux de réussite incohérent avec sa difficulté) est sorti du pool servi — mitigation du risque « items non calibrés » du PRD. Implémentation réelle (revue 2026-07-07) : la détection (`src/items/quarantine.py`, fonction pure) tourne en **job planifié** — `scripts/run_quarantine.py` via le cron quotidien `deploy/prod/quarantine.cron` — pas au fil de l'eau à chaque réponse. La quarantaine est réversible après revue humaine.

---

## 5. L'état de mesure — Elo + propagation

### 5.1 `student_competency_ability` (état par élève × compétence)

```python
class StudentCompetencyAbility(Base):
    __tablename__ = "student_competency_ability"

    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), index=True)     # isolation tenant
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student.id", ondelete="CASCADE"), primary_key=True)
    competency_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competency.id", ondelete="CASCADE"), primary_key=True)

    ability_elo: Mapped[float] = mapped_column()        # meilleure estimation courante (direct + propagé)
    n_direct: Mapped[int] = mapped_column(default=0)     # nb de réponses DIRECTES sur cette compétence
    confidence: Mapped[float] = mapped_column(default=0.0)  # [0..1], croît avec n_direct
    last_measured_at: Mapped[datetime | None] = mapped_column()

    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

PK composite `(student_id, competency_id)`. `confidence` distingue une ability **mesurée directement** (n_direct élevé, confiance haute) d'une ability **inférée par propagation** (n_direct = 0, confiance basse mais estimation déjà disponible). C'est ce qui permet d'afficher un diagnostic dès les premières réponses sans mentir sur sa fiabilité.

### 5.2 `response` (l'événement brut)

```python
class Response(Base):
    __tablename__ = "response"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item.id", ondelete="RESTRICT"), index=True)
    competency_id: Mapped[uuid.UUID] = mapped_column(index=True)  # dénormalisé pour query rapide

    is_correct: Mapped[bool] = mapped_column()
    response_time_ms: Mapped[int | None] = mapped_column()   # signal annexe (devine vs maîtrise)
    session_id: Mapped[uuid.UUID] = mapped_column(index=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
```

`response` est append-only (jamais modifié) : c'est le journal qui permet de recalculer/recalibrer a posteriori, et la base de la future migration IRT (phase 2).

### 5.3 La boucle de mise à jour (pseudocode)

À chaque réponse :

```
on_response(student, item, is_correct):
    c = item.competency_id

    # 1. Elo mutuel standard (élève vs item) sur la compétence directe
    expected = 1 / (1 + 10 ** ((item.difficulty_elo - ability(student, c)) / 400))
    K_student = 32 si n_direct(student, c) < 10, sinon 16
    delta = K_student * (is_correct - expected)
    ability(student, c)       = clamp(ability(student, c) + delta, 0, 4000)

    # côté item : GELÉ au prior pendant le burn-in, puis K décroissant
    si item.n_responses < ITEM_BURN_IN (= 20):
        K_item = 0                                   # difficulté figée au difficulty_prior
    sinon:
        K_item = 32 / (1 + item.n_responses / 30)    # ≈ 19.2 à la sortie du burn-in, décroît ensuite
    item.difficulty_elo       = clamp(item.difficulty_elo - K_item * (is_correct - expected), 0, 4000)

    n_direct(student, c)     += 1
    confidence(student, c)    = 1 - exp(-n_direct / τ)   # τ = 8

    # 2. Propagation amortie vers les voisins (prérequis + dépendants)
    for edge in neighbors(c):
        if confidence(student, edge.other) < confidence(student, c):  # ne pas écraser une mesure plus sûre
            propagated = delta * edge.correlation_strength * DAMPING
            ability(student, edge.other) = clamp(ability + propagated, 0, 4000)
            # n_direct inchangé : c'est de l'inféré, la confiance reste basse
```

**Burn-in item & clamp (aligné sur `src/engine/elo.py`, revue 2026-07-07).** Deux garde-fous s'ajoutent à la boucle naïve ci-dessus :

- **Burn-in item (`ITEM_BURN_IN = 20`)** : tant que `n_responses < 20`, `K_item = 0` — la `difficulty_elo` reste **gelée au `difficulty_prior`** (calibré par item par le générateur déterministe, signal plus fiable qu'une poignée de réponses bruitées). Un K simplement réduit laisserait dériver l'item sur une petite cohorte biaisée (ex. seuls les forts répondent) ; le gel est prévisible et testable. À la sortie du burn-in, `K_item = 32 / (1 + n_responses / 30)` ≈ **19.2** à n=20, puis décroît (16 à n=30, etc.).
- **Clamp `[0, 4000]`** : toute valeur Elo écrite (ability directe, difficulté item, ability propagée) est bornée par `clamp_elo` dans `[ELO_MIN=0, ELO_MAX=4000]` — sans clamp, une longue série (triche, bug client, rejeu) fait dériver les valeurs hors de l'échelle annoncée, et toute la sélection d'items avec.
- **Invariant conservatif** : `Δability / K_student + Δdifficulty / K_item == 0` n'est exigé que **hors burn-in** (`K_item > 0`) et **hors saturation** (aucun clamp déclenché). Au clamp, borner prime sur conserver la masse ; pendant le burn-in, l'ability élève bouge normalement mais l'item ne bouge pas.

**Concurrence & idempotence (implémentation réelle `src/engine/service.py`, revue 2026-07-07).** L'orchestrateur `on_response` verrouille (SELECT … FOR UPDATE) l'item puis les abilities concernées **en ordre déterministe** (item d'abord, abilities triées par `competency_id`) — sans verrou, deux réponses simultanées font un read-modify-write last-write-wins en READ COMMITTED. Le rejeu est neutralisé par un `response_id` **dérivé `uuid5(session_id, item_id)`** + contrainte unique `(session_id, item_id)` sur `response` : rejouer la même réponse ne réapplique rien (409 côté API).

Constantes réglées (dans `src/engine/elo.py`, ajustables via la simulation T3.5) : `K_NEW=32`, `K_STABLE=16`, `N_DIRECT_STABLE=10`, `K_ITEM_BASE=32`, `ITEM_HALFLIFE=30`, `ITEM_BURN_IN=20`, `τ=8` (montée de confiance), `DAMPING=0.4` (atténuation de propagation).

Sens de propagation :
- vers les **prérequis** (réussir B suggère qu'on maîtrise ses prérequis A) → propagation « descendante » forte.
- vers les **dépendants** (réussir A est un faible indice sur B) → propagation « montante » faible.
La `correlation_strength` et le `DAMPING` encodent cette asymétrie.

### 5.4 Calibration des poids d'arête (expert → empirique)

Stratégie en deux temps, tracée par `weight_source` / `weight_version` :

1. **Initialisation experte.** Poids co-construits avec pédagogues, donc interprétables. `weight_source = expert`, `version = 1`. Évite le problème d'identifiabilité du cold-start (un lien faiblement observé n'est pas un lien faible).
2. **Ré-estimation empirique.** Une fois assez de trafic, recalcul des poids sur les données réelles (taux de transition de maîtrise, co-réussite, temps de réponse). `weight_source = empirical`, `version++`.

Garde-fous (sinon le modèle « apprend » des corrélations pédagogiquement absurdes) :
- **Bornes par type d'arête** : un HARD ne descend pas sous un plancher (ex. 0.5) ; un SOFT ne dépasse pas un plafond (ex. 0.7).
- **Monotonie partielle** sur les HARD : la ré-estimation ne peut pas inverser un prérequis validé pédagogiquement.
- **Validation humaine avant promotion** en production d'un poids ré-estimé.
- **Seuil de trafic minimal** par arête avant toute ré-estimation (sinon on calibre sur du bruit).

---

## 6. Restitution (F5) & remédiation (F7) — ce que le modèle alimente

- **Restitution** : l'`ability_elo` agrégée (par compétence → strand → matière) + `confidence` nourrit la couche de restitution (percentile, équivalent niveau, projection trajectoire). L'agrégation remonte le long du graphe.
- **Remédiation** : une lacune = compétence avec `ability_elo` basse ET `confidence` suffisante. Le routing sert d'abord les **prérequis HARD non maîtrisés** (inutile de remédier B si A manque). Claude génère l'exercice ciblé sur la compétence, post-mesure.
- **Sélection d'item adaptative** : servir l'item dont `difficulty_elo ≈ ability_elo` de l'élève (maximise l'information), en priorité sur compétences à `confidence` basse.

---

## 7. Hook curriculum — **Implémenté v1 (Lot B, 2026-07)**

Statut : ~~phase 2, NON construit~~ → **Implémenté v1 (Lot B, 2026-07)**, amendé par la décision **D-B4** (Cadrage-LotB) : le crosswalk réel porte un **type** d'alignement + une **confiance**, pas une force scalaire — `alignment_strength` (placeholder) est remplacé.

```
curriculum_standard (id, framework enum [CCSS_M | UK_NC | MOE_UAE], code,
                     label_en, label_ar, grade_hint NULL,
                     UNIQUE(framework, code))
competency_curriculum_map (competency_id, standard_id,
                           alignment_type enum [EXACT | PARTIAL | BROADER | PREREQ | ENRICH],
                           confidence enum [H | M], note NULL,
                           weight_source, weight_version)   -- même pattern de provenance que competency_prerequisite (§5)
```

**Sémantique MoE (pas de codes officiels)** :
- Les « standards » MoE sont des **clés composées** `domaine + grade-band` (ex. `NUM_OPS/G4-G5`), le cognitif restant porté par la compétence elle-même.
- L'affichage dit « domaine Numbers & Operations, Cycle 1 (G4) » — **jamais un pseudo-code inventé** (« affirmer un code MoE serait faux »).
- `UNIQUE(framework, code)` s'applique à cette clé composée exactement comme à un code officiel — l'upsert par `(framework, code)` reste uniforme au seed.

À l'achat, l'école choisit un curriculum → la restitution étiquette les compétences avec les `code` du standard correspondant. **Le moteur dessous ne change pas.** Le RAG sert ici (ingérer les docs curriculaires officiels → produire la table de mapping), jamais à générer ou mesurer.

---

## 8. Récap des tables

| Table | Portée | Rôle |
|---|---|---|
| `competency` | Globale | Nœud micro-skill (grain c) |
| `competency_prerequisite` | Globale | Arête active (corrélation → propagation) |
| `item` | Globale | Question calibrée, 1:1 compétence |
| `student_competency_ability` | École | État Elo par élève × compétence |
| `response` | École | Journal append-only des réponses |
| `curriculum_standard` / `_map` | Globale | **Implémenté v1 (Lot B, 2026-07)** — étiquetage curriculum |

Tables RBAC/écoles (`organization`, `school`, `class`, `student`, `user`, memberships) : référencées ici pour l'isolation, détaillées dans le module Auth/RBAC (F8) — hors périmètre de ce doc.

---

## 9. Points à trancher (engineering)

- [x] Échelle Elo : **tranché** — classique [0–4000] centrée 1500, bornée par `clamp_elo` (`src/engine/elo.py`, revue 2026-07-07). La restitution (échelle client) est séparée du moteur (T5.2).
- [x] `K`, `τ`, `DAMPING` : **tranché** — constantes dans `src/engine/elo.py` (`K_NEW=32`, `K_STABLE=16`, `K_ITEM_BASE=32`, `ITEM_HALFLIFE=30`, `ITEM_BURN_IN=20`, `τ=8`, `DAMPING=0.4`), validées par la simulation cohorte T3.5 ; ré-ajustables sur données pilotes.
- [ ] Check anti-cycle sur `competency_prerequisite` : à l'insertion applicative ou contrainte SQL ?
- [ ] Profondeur de propagation : 1 saut (voisins directs) suffit-il, ou propager sur 2 sauts ? (1 saut = plus sûr pour démarrer.)
- [ ] Nombre cible de micro-skills maths primaire pour le MVP (borne le volume d'items à produire).
