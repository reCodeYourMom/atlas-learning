# Revue du pivot crosswalk — dossier de confirmation experte

**Lot 1 du dossier de revue** · **Date** : 2026-07-12 · **Statut** : PROPOSITION — à valider
**Destinataire** : didacticien / auteur du crosswalk · **Budget cible : 45 minutes**
**Objet de la validation** : passer `reconciliation.expert_confirmation_pending` de `true` à `false` dans `03_referentiel/crosswalk_fractions_draft.json`.

> **Rien dans ce document n'est validé.** Les décisions ci-dessous ont été prises **automatiquement** par la réconciliation du 2026-07-11 en appliquant les règles R1–R3. Ce dossier les met à plat, cite le texte source qui les justifie, et y ajoute un avis contradictoire. Vous cochez. Tant qu'aucune case n'est cochée, le crosswalk **n'est pas confirmé** et ne doit pas être seedé en production.

---

## 0. Ce que vous validez, en une minute

Le crosswalk fractions (32 compétences × 3 frameworks) existait en **markdown authored** (`Crosswalk-Curriculum-Fractions.md`, v1 du 2026-06-23). Il a été converti en **pivot JSON machine-readable** — désormais la source de vérité, le markdown devenant une vue générée.

La conversion a buté sur deux incohérences (annoncées dans `Cadrage-LotB` §3/B1) :

1. **La table source porte UN type d'alignement par ligne, mais l'alignement diffère selon le framework.** Ex. `NF.SIMPLIFY_FRACTION` est EXACT vis-à-vis d'UK Y6 et ENRICH vis-à-vis de CCSS — une seule colonne « Type » ne peut pas porter les deux. La synthèse authored (CCSS 22/5/5, UK 24/2/4) n'était d'ailleurs **pas reconstructible** depuis les lignes (UK : 24+2+4 = 30 ≠ 32).
2. **12 des 32 niveaux cognitifs MoE contredisaient l'enum `CognitiveLevel` du référentiel**, alors que le doc source revendique un pont 1:1.

La réconciliation a **dédoublé le type par framework** (10 lignes changent de type d'un côté ou de l'autre) et **aligné les 12 cognitifs sur l'enum Atlas**. Vous confirmez ou corrigez ces 22 décisions, puis vous tranchez 2 questions ouvertes.

**Ce que débloque votre signature** : le seed du crosswalk en base (`scripts/seed_crosswalk.py` refuse de tourner si le validateur échoue), puis l'affichage des codes de standards dans le produit (B4/B5).

---

## 1. Les règles appliquées (à valider en bloc, avant les lignes)

| Règle | Énoncé (tel qu'écrit dans le pivot) | Mon avis |
|---|---|---|
| **R1** | « les notes et la section Divergences de `Crosswalk-Curriculum-Fractions.md` **font foi** quand elles existent » | ✅ Correct. C'est la seule hiérarchie possible : la note est l'expression explicite de l'intention de l'auteur ; la colonne « Type » est un résumé lossy. |
| **R2** | « équivalence d'âge UK Year ≈ US Grade+1 : nœud Atlas G mappé Y(G+1) = **EXACT en âge**, mappé Y(G+2) = **ENRICH** » | ⚠️ **Règle asymétrique** — elle ne dit rien du cas Y(G) ou Y(G−1), c.-à-d. quand le framework UK introduit la notion **plus tôt** qu'Atlas. Or c'est le cas de ~10 nœuds G3 mappés Y3 (âge = Y4). Ils restent EXACT, ce qui est défendable, mais la règle ne le dit pas : **à compléter par écrit** (« Y ≤ G+1 ⇒ EXACT »), sinon un tiers ne peut pas rejouer la réconciliation. |
| **R3** | « CCSS : standard cité d'un grade **supérieur** au nœud Atlas ⇒ ENRICH (Divergence 1) » | ✅ Correct et cohérent avec la doctrine (« le graphe Atlas est ordonné par prérequis, pas par grade »). Voir toutefois le point de contradiction **C-2** ci-dessous : R3 n'a pas été appliquée à #9. |
| **Cognitif** | « l'enum `CognitiveLevel` du référentiel **fait foi** (RECALL→Knowing, APPLY→Applying, REASON→Reasoning) ; aucun override retenu, proposition originale conservée dans `authored_cognitive` » | ✅ Conforme à la reco du `Cadrage-LotB` §3/B1 (« l'enum Atlas fait foi ; la colonne MoE du pivot devient dérivée »). **Mais** cela suppose que l'enum du référentiel est juste — voir **C-4**. |

**Priorité des règles en cas de conflit : R1 > R2 = R3.** (C'est ce que fait le code ; ce n'est écrit nulle part → à acter.)

- [ ] **ACCEPTER les 4 règles** · [ ] **REJETER / corriger** : ______________________________________________

---

## 2. Décisions — types d'alignement (10 lignes réconciliées)

Chaque ligne : la décision prise, la règle, **la citation exacte** du doc source qui la justifie, mon avis contradictoire.

---

### D1 · #10 `MATH.G3.NF.NUMBER_LINE_PLACE` [uk_nc] : **EXACT → PARTIAL**

**Règle** : R1 (note du doc source).
**Citation source** (`Crosswalk-Curriculum-Fractions.md`, ligne 40) :
> `| 10 | NF.NUMBER_LINE_PLACE | Place a fraction on a number line | 3 | 3.NF.A.2 (2a, 2b) | Y3 fractions as numbers | EXACT | H | CCSS très number-line-centric ; **UK l'implique sans l'isoler**. |`

**Raisonnement retenu** : l'EXACT de la ligne venait du côté CCSS (3.NF.A.2 est explicite) ; côté UK la note dit elle-même que la correspondance est implicite ⇒ PARTIAL.

**Mon avis** : ✅ **D'accord.** La note est sans ambiguïté. Contre-argument possible : « fractions as numbers » en Y3 *est* la droite numérique dans l'esprit du programme UK (c'est la seule représentation qui fait d'une fraction un nombre) — un puriste défendrait EXACT. Mais PARTIAL est le choix honnête, et l'honnêteté est ici l'argument commercial.

- [ ] ACCEPTER · [ ] REJETER → type retenu : ____________ · Motif : _______________________________

---

### D2 · #13 `MATH.G3.NF.WHOLE_AS_FRACTION` [uk_nc] : **EXACT → PARTIAL**

**Règle** : R1.
**Citation source** (ligne 43) :
> `| 13 | NF.WHOLE_AS_FRACTION | Whole numbers as fractions (b/b=1) | 3 | 3.NF.A.3c | **Y3–Y5 (implicite)** | EXACT | H | CCSS explicite (3.NF.A.3c). |`

**Raisonnement retenu** : le descriptor UK est lui-même marqué « implicite » ; `b/b = 1` n'est nommé par **aucun** objectif UK NC ⇒ PARTIAL au grain honnête.

**Mon avis** : ✅ **D'accord — et je serais même plus dur.** Si aucun objectif UK ne nomme la compétence, le type le plus juste n'est pas PARTIAL (« couvre une partie d'un standard plus large ») mais **PREREQ** (« grain plus fin / prérequis cognitif non nommé explicitement par le standard, mais nécessaire pour l'atteindre ») — la définition de PREREQ dans votre propre légende décrit exactement ce cas. **Question à trancher** (même famille que #30/#31, §4).

- [ ] ACCEPTER (PARTIAL) · [ ] PREREQ · [ ] AUTRE : ____________ · Motif : _______________________

---

### D3 · #18 `MATH.G4.NF.ADD_UNLIKE_SIMPLE` [ccss_m] : **EXACT → ENRICH**

**Règle** : R3 (standard CCSS d'un grade supérieur).
**Citation source** (ligne 48) :
> `| 18 | NF.ADD_UNLIKE_SIMPLE | Add unlike, one denom multiple of other | 4 | **5.NF.A.1 (sous-cas)** | Y5 denom = multiples du même nombre | EXACT | H | UK Y5 exactement ce cas. |`
et Divergence 1 (ligne 81) :
> « addition à dénominateurs différents en G4 chez Atlas, G5/Y6 dans les frameworks. **C'est intentionnel.** »

**Raisonnement retenu** : 5.NF.A.1 est un standard G5, Atlas place le nœud en G4 ⇒ avance d'un grade ⇒ ENRICH côté CCSS. L'EXACT de la ligne venait d'UK Y5, qui est bien l'âge du nœud G4 (R2) — il est conservé côté UK. La mention « sous-cas » va en **nuance** (champ `note`), pas en type.

**Mon avis** : ✅ **D'accord, et c'est la décision la plus importante des 10.** Elle établit que « Atlas est en avance sur le grade » ⇒ ENRICH, uniformément. Le seul contre-argument sérieux : ENRICH signifie « exigence absente du standard OU placée différemment » — ici l'exigence **existe** dans CCSS, seulement un an plus tard. Un lecteur CCSS pourrait lire « beyond 5.NF.A.1 expectations » (le wording produit associé à ENRICH) comme « au-delà du programme », alors que le sens réel est « avant l'heure ». **Le wording d'ENRICH est trompeur pour ce cas** — voir §6, point de vigilance produit.

- [ ] ACCEPTER · [ ] REJETER → type retenu : ____________ · Motif : _______________________________

---

### D4 · #19 `MATH.G4.NF.COMMON_DENOM` [ccss_m] : **EXACT → ENRICH**

**Règle** : R3.
**Citation source** (ligne 49) :
> `| 19 | NF.COMMON_DENOM | Find a common denominator | 4 | **5.NF.A.1 (embarqué)** | Y6 common multiples for same denomination | EXACT | H | |`

**Raisonnement retenu** : compétence embarquée dans 5.NF.A.1 (G5) ; Atlas la place en G4 ⇒ même situation que #17/#18 sur le même standard ⇒ ENRICH.

**Mon avis** : ⚠️ **D'accord sur ENRICH, mais le mot « embarqué » aurait dû produire un autre type.** « Embarqué dans 5.NF.A.1 » = *un seul standard officiel regroupe plusieurs compétences Atlas* — c'est **littéralement la définition de BROADER** dans votre légende. Le vrai type de cette ligne est bi-dimensionnel : BROADER en **grain** (Atlas est plus fin que 5.NF.A.1) *et* ENRICH en **grade**. Le schéma du pivot ne porte qu'un type, donc il faut choisir. Je retiens ENRICH (le grade est ce qui perturbe l'enseignant), mais voir la **contradiction C-3** : BROADER n'est utilisé **nulle part** dans le pivot, alors que la finesse du grain Atlas est l'argument de vente n°1.

- [ ] ACCEPTER (ENRICH) · [ ] BROADER · [ ] AUTRE : ____________ · Motif : _____________________

---

### D5 · #19 `MATH.G4.NF.COMMON_DENOM` [uk_nc] : **EXACT → ENRICH**

**Règle** : R2 (Y6 pour un nœud G4 dont l'âge est Y5 ⇒ Y(G+2) ⇒ ENRICH).
**Citation source** (ligne 49) : descriptor `Y6 common multiples for same denomination`.

**Mon avis** : ✅ **D'accord**, et c'est cohérent avec #17 (`ADD_UNLIKE_LCM`, G4 → Y6, déjà ENRICH dans le doc source). **Mais** cette décision crée mécaniquement la contradiction **C-1** ci-dessous : #23 est aussi un nœud G4 mappé Y6 et reste EXACT.

- [ ] ACCEPTER · [ ] REJETER → type retenu : ____________ · Motif : _______________________________

---

### D6 · #20 `MATH.G4.NF.COMPARE_BENCHMARK` [uk_nc] : **EXACT → PARTIAL**

**Règle** : R1.
**Citation source** (ligne 50) :
> `| 20 | NF.COMPARE_BENCHMARK | Compare using benchmarks (½, 1) | 4 | 4.NF.A.2 (benchmark fraction) | **Y5–Y6 (implicite)** | EXACT | H | CCSS nomme explicitement le benchmark ½. |`

**Raisonnement retenu** : UK NC n'exige pas la stratégie benchmark que CCSS nomme ; la compétence couvre une partie des objectifs « compare and order » Y5–Y6 ⇒ PARTIAL.

**Mon avis** : ✅ **D'accord.** C'est le cas d'école du PARTIAL : le standard UK (« compare and order fractions ») est **plus large** que la compétence Atlas (comparer *via un repère*). Aucun contre-argument.

- [ ] ACCEPTER · [ ] REJETER → type retenu : ____________ · Motif : _______________________________

---

### D7 · #21 `MATH.G4.NF.COMPARE_DIFF_DENOM` [uk_nc] : **EXACT → PARTIAL**

**Règle** : R2 (couverture répartie sur deux years).
**Citation source** (ligne 51) :
> `| 21 | NF.COMPARE_DIFF_DENOM | Compare different denominators | 4 | 4.NF.A.2 | **Y5 (multiples) / Y6 (incl. >1)** | EXACT | H | |`

**Raisonnement retenu** : à l'âge du nœud (G4 ≈ Y5), UK ne couvre que le cas « dénominateurs multiples du même nombre » ; la généralisation relève de Y6 ⇒ couverture partielle **à l'âge** ⇒ PARTIAL.

**Mon avis** : ⚠️ **D'accord sur le fond, mais le raisonnement mélange deux dimensions.** Ce n'est pas une couverture partielle *du standard* (définition de PARTIAL), c'est une couverture *étalée sur deux années*. On pourrait tout aussi bien dire : EXACT vis-à-vis de Y5 **et** ENRICH vis-à-vis de Y6. Le pivot ne permet qu'un type par (compétence, framework) alors que le seed matérialise **deux standards** (Y5 **et** Y6, cf. `seed_crosswalk.py`) qui héritent tous deux du même PARTIAL. Conséquence concrète : le standard **Y5** est étiqueté PARTIAL alors que la compétence le couvre exactement. **Point structurel à trancher** — voir §6.

- [ ] ACCEPTER (PARTIAL sur Y5 et Y6) · [ ] EXACT sur Y5 / ENRICH sur Y6 · [ ] AUTRE : ____________

---

### D8 · #26 `MATH.G4.NS.GCD` [uk_nc] : **ENRICH → EXACT**

**Règle** : R2 (levée du flag « À réconcilier » de la note).
**Citation source** (ligne 56) :
> `| 26 | NS.GCD | Greatest common divisor | 4 | 6.NS.B.4 | **Y5 common factors** / Y6 simplify | ENRICH | H | CCSS formalise le PGCD en **G6** ; Atlas l'introduit en G4 comme prérequis de simplification. |`

**Raisonnement retenu** : la note ne justifie l'ENRICH **que côté CCSS** (PGCD formalisé G6). Côté UK, « common factors of two numbers » est un objectif **Y5**, soit exactement l'âge du nœud G4 ⇒ EXACT.

**Mon avis** : ✅ **D'accord — c'est la meilleure des 10 décisions.** C'est un cas où la ligne authored était objectivement fausse côté UK, et la réconciliation la corrige. Petit bémol : « common factors » (facteurs communs) ≠ « greatest common divisor » (le **plus grand**) ; UK Y5 demande d'identifier des facteurs communs, pas d'en extraire le maximum. On pourrait défendre PARTIAL. Je maintiens EXACT (le geste cognitif est le même, l'extremum est une trivialité procédurale), mais **c'est votre appel de didacticien.**

- [ ] ACCEPTER (EXACT) · [ ] PARTIAL · [ ] AUTRE : ____________ · Motif : ____________________

---

### D9 · #30 `MATH.G5.NF.IMPROPER_TO_MIXED` [ccss_m] : **EXACT → PARTIAL** ❓ *question ouverte, cf. §4*

**Règle** : R1.
**Citation source** (ligne 60) :
> `| 30 | NF.IMPROPER_TO_MIXED | Convert improper → mixed | 5 | **4.NF.B.3b (implicite)** | Y5 convert one form to the other | EXACT | H | UK Y5 explicite. |`

**Raisonnement retenu** : CCSS ne nomme pas la conversion impropre→mixte comme standard dédié ; c'est un sous-geste de 4.NF.B.3b ⇒ PARTIAL. L'EXACT venait d'UK Y5, conservé côté UK.

**Mon avis** : ❌ **Je ne suis pas d'accord : c'est un PREREQ, pas un PARTIAL.** Voir §4 — argumentation complète.

- [ ] PARTIAL · [ ] PREREQ · [ ] AUTRE : ____________ · Motif : _______________________________

---

### D10 · #31 `MATH.G5.NF.MIXED_TO_IMPROPER` [ccss_m] : **EXACT → PARTIAL** ❓ *question ouverte, cf. §4*

**Règle** : R1. **Citation source** (ligne 61) : `4.NF.B.3c / 5.NF.A.1 (impl.)` — « UK Y5 explicite ».
**Mon avis** : ❌ Idem D9. Voir §4.

- [ ] PARTIAL · [ ] PREREQ · [ ] AUTRE : ____________ · Motif : _______________________________

---

## 3. Décisions — niveaux cognitifs MoE (12 alignements)

**Règle unique** : l'enum `CognitiveLevel` du référentiel fait foi. La colonne MoE du markdown était **indicative** — le doc source le dit lui-même :

> **Citation source** (ligne 143) : « Le niveau cognitif est **indicatif** (proposé selon le geste, alignable sur l'enum `CognitiveLevel` d'Atlas). »
> **Citation source** (ligne 102) : « le niveau cognitif MoE (Knowing/Applying/Reasoning) correspond **1:1** à l'enum `CognitiveLevel` d'Atlas (RECALL/APPLY/REASON) ».

La proposition d'origine est conservée dans le champ `authored_cognitive` (aucune information perdue).

**Vérification faite** : les 32 `cognitive_level` du pivot correspondent désormais **exactement** à l'enum des 32 nœuds de `referentiel_fractions.json`. 0 écart. ✅

| # | Compétence | MoE authored | Enum Atlas | → retenu | Mon avis |
|---|---|---|---|---|---|
| 1 | `NS.EQUAL_SHARES` | Knowing | APPLY | **Applying** | ✅ Partager en parts égales est une exécution, pas un fait mémorisé. |
| 3 | `NS.NAME_FRACTION_VISUAL` | Knowing | APPLY | **Applying** | ✅ Idem — il faut *compter puis nommer*. |
| 7 | `NF.EQUIVALENCE_VISUAL` | Knowing | REASON | **Reasoning** | ⚠️ **Le plus discutable des 12.** Reconnaître 1/2 = 2/4 sur deux diagrammes superposés est perceptif, pas argumentatif. Applying serait défendable. L'enum Atlas dit REASON → on suit l'enum. **Si vous corrigez, corrigez le référentiel (A1.5), pas le pivot.** |
| 8 | `NF.FRACTION_AS_PART` | Knowing | APPLY | **Applying** | ✅ |
| 12 | `NF.UNIT_FRACTION` | Knowing | REASON | **Reasoning** | ⚠️ Même réserve que #7 : « comprendre 1/b » est classé REASON par l'enum. Défendable (c'est le nœud conceptuel du domaine), mais c'est un jugement fort. |
| 13 | `NF.WHOLE_AS_FRACTION` | Knowing | REASON | **Reasoning** | ✅ `b/b = 1` demande bien un raisonnement sur la structure. |
| 15 | `NF.ADD_SAME_IMPROPER` | Applying | REASON | **Reasoning** | ✅ Le résultat impropre force une décision de forme. |
| 17 | `NF.ADD_UNLIKE_LCM` | Applying | REASON | **Reasoning** | ✅ Choix du PPCM = choix de stratégie. |
| 18 | `NF.ADD_UNLIKE_SIMPLE` | Applying | REASON | **Reasoning** | ⚠️ Ici l'élève **n'a pas** à choisir (un dénominateur est multiple de l'autre : la stratégie est forcée). Par l'heuristique A1.5 (« si l'item type peut être réussi en déroulant un algorithme unique sans décision, c'est APPLY »), ce nœud devrait être **APPLY**. **Incohérence probable du référentiel, pas du pivot.** À corriger côté A1.5 si vous en convenez. |
| 25 | `NS.FACTORS` | Knowing | APPLY | **Applying** | ✅ |
| 28 | `NF.ADD_MIXED` | Applying | REASON | **Reasoning** | ✅ |
| 32 | `NF.SUB_UNLIKE_LCM` | Applying | REASON | **Reasoning** | ✅ |

**Décision de bloc** :

- [ ] **ACCEPTER les 12 alignements** (l'enum Atlas fait foi)
- [ ] ACCEPTER, **mais corriger l'enum du référentiel** sur : ☐ #7 `EQUIVALENCE_VISUAL` ☐ #12 `UNIT_FRACTION` ☐ #18 `ADD_UNLIKE_SIMPLE` ☐ autre : ____________
  *(Attention : corriger l'enum change le `difficulty_prior` attendu (A1.4, temps 2) et le pivot devra être régénéré. Ce n'est pas une correction cosmétique.)*
- [ ] REJETER : la colonne MoE doit primer sur l'enum → motif : _________________________________

---

## 4. Les 2 questions ouvertes signalées dans le pivot — à trancher

Le pivot les pose explicitement : *« PARTIAL (alternative PREREQ possible, à trancher par l'expert) »*.

### Q1 — #30 `IMPROPER_TO_MIXED` et #31 `MIXED_TO_IMPROPER` [ccss_m] : **PARTIAL ou PREREQ ?**

**Les faits.** CCSS-M ne consacre **aucun** standard à la conversion entre forme impropre et nombre mixte. La conversion apparaît comme un geste intermédiaire *à l'intérieur* de 4.NF.B.3b/c (« decompose a fraction into a sum of fractions with the same denominator… ») et de 5.NF.A.1. UK NC, lui, l'exige explicitement en Y5 (« convert one form to the other »).

**Les deux lectures, avec votre propre légende** :

| Type | Définition (doc source, lignes 18 & 20) | Application à #30/#31 |
|---|---|---|
| **PARTIAL** | « La compétence Atlas couvre **une partie** d'un standard plus large. » | 4.NF.B.3b est plus large (décomposition) ; convertir en est un morceau. **Vrai.** |
| **PREREQ** | « Grain plus fin / prérequis cognitif **non nommé explicitement** par le standard, mais nécessaire pour l'atteindre. » | CCSS ne nomme jamais la conversion ; elle est nécessaire pour réussir 4.NF.B.3c et 5.NF.A.1. **Vrai aussi, et plus précis.** |

**Ma recommandation : PREREQ.** Trois raisons.

1. **Le critère discriminant est « nommé ou non ».** PARTIAL suppose que la compétence est un *sous-ensemble identifiable* de l'énoncé du standard ; PREREQ couvre le cas où le standard **ne la nomme pas** et où elle est un prérequis pour l'atteindre. Le pivot dit lui-même « Implicite » — c'est le mot-clé de PREREQ.
2. **Conséquence produit, décisive** : la règle B5 (`Cadrage-LotB` §3/B5) dit que le booléen « standard couvert » n'est vrai que si **toutes les compétences EXACT** du standard sont maîtrisées, et que « les PARTIAL/PREREQ n'y contribuent jamais positivement seuls ». Les deux types se comportent donc **identiquement** pour l'agrégation. **Le seul effet observable du choix est le wording affiché** : PARTIAL → *« covers part of 4.NF.B.3b »* ; PREREQ → *« building block for 4.NF.B.3b »*. Devant un Head of Assessment américain, « building block for » est **exact** ; « covers part of » invite la question « quelle partie ? » et vous n'aurez pas de réponse dans le texte du standard. **PREREQ est plus défendable en due diligence.**
3. **Cohérence** : si #30/#31 sont PARTIAL, alors #13 (`WHOLE_AS_FRACTION` [uk_nc], D2) — dont le descriptor est aussi « implicite » — devrait l'être aussi pour la même raison. Or les deux cas sont identiques. **Trancher les trois ensemble.**

**Coût du choix PREREQ** : le type `PREREQ` n'est aujourd'hui utilisé **nulle part** dans le pivot (0/64 alignements CCSS+UK). L'adopter fait vivre une catégorie de plus dans le wording produit — le code la supporte déjà (`_ALIGNMENT_WORDING_EN/AR`, `views_service.py`), donc coût technique nul.

> **Décision Q1** — #30 et #31 [ccss_m] :
> - [ ] **PREREQ** (recommandé) — et j'aligne aussi ☐ #13 [uk_nc]
> - [ ] **PARTIAL** (statu quo du pivot)
> - [ ] Autre : ____________________________________________________________________
> Motif : ______________________________________________________________________

---

### Q2 — Le type par framework est-il suffisant, ou faut-il un type **par standard** ?

Cette question n'est pas dans le pivot, mais elle en sort mécaniquement (cas #21, D7). Le pivot porte **un type par (compétence, framework)**. Or `seed_crosswalk.py` matérialise **plusieurs standards par framework** pour une même compétence :

- CCSS : #28 `ADD_MIXED` cite `4.NF.B.3c` **et** `5.NF.A.1` → 2 standards, **même type** (EXACT).
- UK : #21 `COMPARE_DIFF_DENOM` a `years: "Y5-Y6"` → 2 standards (Y5, Y6), **même type** (PARTIAL) — alors que la note dit que Y5 couvre exactement le cas et Y6 la généralisation.

**Conséquence concrète** : le badge affiché à l'enseignant sur le standard **Y5** dira « covers part of Y5 » alors que la compétence le couvre exactement.

**Ma recommandation : ne pas ouvrir ce chantier maintenant.** Le grain « type par framework » est suffisant pour la v1 (le wording reste conservateur, jamais sur-claim) et le schéma DB (`competency_curriculum_map`, PK `(competency_id, standard_id)`) supporte déjà un type par standard **sans migration** — c'est un enrichissement du pivot, pas du modèle. À rouvrir si un prospect UK conteste un badge.

> - [ ] D'accord, on reste au type par framework en v1
> - [ ] Non, il faut un type par standard dès maintenant → lignes concernées : ______________________

---

## 5. Contradictions que la réconciliation N'A PAS traitées (à arbitrer)

Ces quatre points ne figurent **pas** dans les 10 décisions du pivot. Ils sont sortis de la relecture ligne à ligne. **Chacun est un vrai désaccord, pas une broutille.**

### C-1 · #23 `SIMPLIFY_FRACTION` [uk_nc] reste **EXACT** alors que R2 impose ENRICH — ❗ **incohérence directe**

Trois nœuds Atlas de grade **G4** sont mappés sur un descriptor **UK Y6** :

| # | Compétence | Grade Atlas | Year UK | Type retenu | Dérivation |
|---|---|---|---|---|---|
| 17 | `ADD_UNLIKE_LCM` | G4 | Y6 | **ENRICH** | note (doc source) |
| 19 | `COMMON_DENOM` | G4 | Y6 | **ENRICH** | *reconciled (R2)* ← D5 |
| **23** | **`SIMPLIFY_FRACTION`** | **G4** | **Y6** | **EXACT** ❗ | note (doc source) |
| 27 | `LCM` | G4 | Y6 | **ENRICH** | row-confirmed |

R2 dit : *« nœud Atlas G mappé Y(G+2) = ENRICH »*. G4 → Y6 = Y(G+2). **#23 devrait donc être ENRICH côté UK.** Il reste EXACT parce que la note du doc source l'affirme (R1 > R2) :

> **Citation source** (Divergence 2, lignes 84–86) : « La compétence `NF.SIMPLIFY_FRACTION` est donc : **EXACT vis-à-vis d'UK Y6**, ENRICH (au-delà du standard) vis-à-vis de CCSS. »

**Mon avis** : la note du doc source parle de la **nature de l'exigence** (UK exige la réduction, CCSS non) — pas du **placement en grade**. Elle répond à la question « le standard demande-t-il cette compétence ? », pas à « au même âge ? ». **Sur les deux dimensions, la ligne devrait être ENRICH côté UK** (exigence réelle, mais deux ans plus tôt qu'UK), exactement comme #19 et #27. **Laisser EXACT est incohérent** : le même couple (G4, Y6) reçoit deux types différents dans le même fichier, sans que rien ne le distingue.

> - [ ] **Corriger #23 [uk_nc] : EXACT → ENRICH** (recommandé — cohérence avec #17/#19/#27)
> - [ ] Maintenir EXACT → motif écrit (il en faut un, sinon le prochain lecteur refera le tour) : ______________

---

### C-2 · #9 `FRACTION_OF_SET` [ccss_m] : R3 n'a pas été appliquée

`FRACTION_OF_SET` est un nœud **G3** mappé sur `4.NF.B.4` — un standard **G4**. R3 dit : « standard cité d'un grade supérieur au nœud Atlas ⇒ ENRICH ». Le type retenu est pourtant **PARTIAL**, sur la foi de la note :

> **Citation source** (ligne 39 & Divergence 3) : « CCSS : pas de standard dédié G3 ; couvert plus tard via multiplication. » / « Mapping marqué PARTIAL / confiance M côté CCSS. »

**Mon avis** : ✅ **La décision est bonne, la trace ne l'est pas.** R1 (la note) prime sur R3 — c'est la règle. Mais le fichier ne le dit nulle part, et un tiers qui rejoue R3 mécaniquement trouvera une « erreur ». **Il manque un `reconciliation_note` sur cette ligne** documentant que R3 a été délibérément écartée au profit de R1. Coût : une ligne de JSON. Bénéfice : le pivot redevient auditable sans vous.

> - [ ] Ajouter un `reconciliation_note` sur #9 [ccss_m] documentant l'arbitrage R1 > R3
> - [ ] Changer #9 en ENRICH · [ ] Ne rien faire

---

### C-3 · **`BROADER` n'est utilisé nulle part — l'argument de vente n°1 est invisible dans le pivot**

`BROADER` = *« Un seul standard officiel regroupe plusieurs compétences Atlas (Atlas est plus fin → meilleure granularité de mesure) »*. C'est **la** proposition de valeur d'Atlas. Or **0 des 64 alignements CCSS/UK ne porte ce type**. Pourtant les cas sont là :

| Standard officiel | Compétences Atlas qui s'y rattachent | Type actuellement porté |
|---|---|---|
| CCSS `4.NF.B.3a` | #4 `ADD_SAME_NOSIMP`, #11 `SUB_SAME_NOSIMP`, #16 `ADD_SAME_SIMPLIFY`, #24 `SUB_SAME_SIMPLIFY` | ENRICH, ENRICH, PARTIAL, PARTIAL |
| CCSS `3.NF.A.3d` | #5 `COMPARE_SAME_DENOM`, #6 `COMPARE_SAME_NUM` | EXACT, EXACT |
| CCSS `5.NF.A.1` | #17, #18, #19, #29, #32 (5 compétences) | ENRICH ×3, EXACT ×2 |
| CCSS `6.NS.B.4` | #23 `SIMPLIFY`, #26 `GCD`, #27 `LCM` | ENRICH ×3 |
| UK `Y6` | #17, #19, #23, #27, #28, #29, #32… | mélange |

**Un standard CCSS = jusqu'à 5 compétences Atlas.** C'est exactement ce que BROADER décrit, et c'est le chiffre qu'on veut mettre sous les yeux d'un acheteur (« là où votre programme voit une case, nous mesurons cinq gestes distincts »).

**Mon avis** : le type unique par ligne **ne peut pas** porter simultanément la dimension *grain* (BROADER) et la dimension *grade* (ENRICH) — c'est une limite du schéma, pas une erreur. Mais alors **le pivot ne doit pas être la seule source de l'argument de granularité** : la métrique « n compétences Atlas par standard » se calcule trivialement depuis `competency_curriculum_map` et devrait être **affichée** (rapport école, one-pager). **Ne changez pas les types ; ajoutez la métrique.**

> - [ ] D'accord : ne pas toucher aux types ; ajouter la métrique « compétences Atlas par standard » (backlog B/produit)
> - [ ] Non : réintroduire BROADER sur les lignes concernées → lesquelles : ______________________

---

### C-4 · Le cognitif MoE est désormais **dérivé** de l'enum Atlas — ce qui déplace la charge de la preuve

En alignant les 12 cognitifs sur l'enum, la colonne MoE du pivot **cesse d'être une information indépendante** : elle est une pure fonction de `cognitive_level`. Elle ne peut donc plus servir de **contrôle croisé** du référentiel. Si l'enum se trompe (cf. mes réserves sur #7, #12, #18 en §3), le pivot se trompe **avec lui**, silencieusement, et le validateur R3 est vert par construction.

**Mon avis** : c'est la bonne décision (une source de vérité), **mais** elle rend la revue A1.5 du référentiel plus importante qu'avant. **Recommandation** : profiter de cette session pour rejuger les 3 nœuds signalés en §3. Sinon, acter par écrit que l'enum fractions est figé et que les écarts MoE observés étaient des erreurs de la colonne indicative.

> - [ ] Acté : l'enum fractions est figé, la colonne MoE est dérivée
> - [ ] Je rejuge #7 / #12 / #18 (cf. §3) avant de figer

---

## 6. Vérifications automatiques déjà passées (rien à faire, pour information)

| Contrôle | Résultat |
|---|---|
| Couverture 32/32 dans les 3 frameworks | ✅ |
| `computed_synthesis` recalculée depuis les lignes | ✅ CCSS **18 EXACT / 6 PARTIAL / 8 ENRICH** · UK **22 / 7 / 3** — chaque total = 32 (l'authored UK 24+2+4 = 30 était faux) |
| Cognitifs MoE ≡ enum des 32 nœuds | ✅ 0 écart |
| Syntaxe des codes (CCSS / UK / clé composée MoE) | ✅ |
| `scripts/validate_crosswalk.py` sur le pivot actuel | ✅ **0 erreur** (rejoué le 2026-07-12) |

**Point de vigilance produit (hors périmètre de votre signature, mais lié à vos décisions)** — le wording associé aux types, tel que câblé dans `src/api/views_service.py` :

| Type | Texte affiché EN | Risque |
|---|---|---|
| EXACT | *aligned to {code}* | — |
| PARTIAL | *covers part of {code}* | invite « quelle partie ? » (cf. Q1) |
| **ENRICH** | ***beyond {code} expectations*** | ⚠️ **Ambigu pour les 8 lignes ENRICH-de-grade** (#4, #11, #17, #18, #19, #23, #26, #27) : le sens réel est « **avant** l'heure du programme », pas « **au-delà** du programme ». Un parent ou un inspecteur lira « hors programme ». **Recommandation : un second wording pour l'ENRICH-de-grade** (ex. *« taught earlier than {code} »*) — décision produit, pas didactique, mais elle découle de D3/D4/D5. |

*(Ce point est repris dans `05_revue/Revue-Code-Findings.md`, finding M-4.)*

---

## 7. Procédure de clôture

**Qui coche quoi.**

| Étape | Qui | Action |
|---|---|---|
| 1 | **Didacticien / auteur du crosswalk** | Coche §1 (règles), §2 (D1–D10), §3 (bloc cognitif), §4 (Q1, Q2), §5 (C-1 à C-4). Date et signe ci-dessous. |
| 2 | **Fondateur** | Reporte les corrections dans `03_referentiel/crosswalk_fractions_draft.json` (types, `reconciliation_note`, éventuels changements d'enum). |
| 3 | **Fondateur** | Passe `reconciliation.expert_confirmation_pending` à **`false`** et ajoute : `"expert_confirmed_by": "<nom>"`, `"expert_confirmed_at": "<YYYY-MM-DD>"`. |
| 4 | **Fondateur** | Relance le validateur — **doit rester à 0 erreur** : |

```bash
cd 04_code
./.venv/bin/python scripts/validate_crosswalk.py \
  --pivot ../03_referentiel/crosswalk_fractions_draft.json \
  --referentiel ../03_referentiel/referentiel_fractions.json
# attendu : « 0 erreur — crosswalk valide (règles B6 R1–R5). »
```

| 5 | **Fondateur** | Régénère la vue markdown : `./.venv/bin/python scripts/generate_crosswalk_md.py` (le `.md` est une vue, ne jamais l'éditer à la main). |
| 6 | **Fondateur** | ⚠️ **Avant de reseeder** : lire le finding **CRIT-2** de `Revue-Code-Findings.md` — `seed_crosswalk.py` est **insert-only, pas upsert**. Si le crosswalk a déjà été seedé, relancer le seed **n'appliquera aucune de vos corrections**. Vider les deux tables ou corriger le script d'abord. |
| 7 | **Fondateur** | Seed : `./.venv/bin/python scripts/seed_crosswalk.py` (refuse de tourner si le validateur échoue). |

**Condition de sortie** : validateur à 0 erreur **et** `expert_confirmation_pending: false` **et** nom + date renseignés.

**Ce que débloque cette signature** : le seed production du crosswalk → l'affichage des codes de standards (B4) → la section « Couverture du programme » du rapport école (B5), c'est-à-dire l'argument commercial du Lot B.

---

## Signature

| | |
|---|---|
| **Nom du relecteur** | ____________________________________________ |
| **Qualité** | ☐ Didacticien mathématiques ☐ Auteur du crosswalk ☐ Autre : ____________ |
| **Date** | ____________________ |
| **Verdict global** | ☐ Confirmé (toutes cases cochées) ☐ Confirmé sous réserve des corrections ci-dessus ☐ Non confirmé |
| **Signature** | ____________________________________________ |

*Les priors, types d'alignement et niveaux cognitifs de ce crosswalk sont des **choix experts citant des frameworks publiés**. Ce document n'est ni une certification ni un endossement par un régulateur (KHDA / ADEK / MoE). Aucune compétence n'est « calibrée » ni « validée MoE » : la mesure est expert-seeded et sera ré-estimée sur trafic réel (Lot C).*
