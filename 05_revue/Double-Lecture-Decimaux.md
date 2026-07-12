# Double lecture du référentiel décimaux — grille A1.8 pré-remplie

**Lot 3 du dossier de revue** · **Date** : 2026-07-12 · **Statut** : PROPOSITION — à valider
**Objet** : `03_referentiel/referentiel_decimals_draft.json` — **14 nœuds, 26 arêtes** (21 intra + 5 ponts vers les fractions)
**Destinataires** : **Lecteur A — didacticien mathématiques** · **Lecteur B — enseignant primaire EAU en exercice**
**Budget cible : 2 h par lecteur**

> ⚠️ **Avertissement obligatoire (Méthodologie §0)** : les `difficulty_prior` et `correlation_strength` de ce référentiel sont des **points de départ experts**. Ce ne sont **ni un standard, ni une mesure**. Ils seront ré-estimés sur trafic réel (Lot C). **Aucun nœud de ce document n'est calibré, aligné MoE, ni validé.**

---

## 0. Protocole — à lire avant de commencer (5 min)

**Le gate A1.8 est bloquant : aucun nœud ne passe `active` sans double validation.**

1. **Lecture INDÉPENDANTE.** Chacun remplit la grille **seul**, sans voir l'autre. Ne comparez pas vos réponses avant d'avoir terminé.
2. **Réconciliation.** Les désaccords sont listés et arbitrés en séance. **Chaque arbitrage est journalisé** (registre §5). Un désaccord non tranché = le nœud ou l'arête **reste en `draft`**.
3. Les **pré-avis** ci-dessous sont ceux du rédacteur du draft, relus. Ils sont là pour vous faire gagner du temps, **pas** pour vous orienter. Un pré-avis « ✅ conforme » n'est pas une validation : c'est une hypothèse que vous confirmez ou cassez.

**Ce que débloque votre double signature** (avec le Lot 4) : le lancement de la production des ~140 items décimaux (A-5/A-6).

**Comment cocher** : chaque case a **deux colonnes de signature**. Écrivez `✓` si le point passe, `✗` s'il échoue (et dites pourquoi). **Un seul ✗ sur un nœud = retour en rédaction pour ce nœud** (pas pour le référentiel entier).

---

## 1. Vue d'ensemble — ce que le validateur et les compteurs disent déjà

*Ces chiffres sont **calculés**, pas déclarés. Rejoués le 2026-07-12.*

| Contrôle (Méthodologie A1.7 / grille GRAPHE) | Valeur mesurée | Norme | Verdict machine |
|---|---|---|---|
| **G1** Densité **intra-domaine** | **21 / 14 = 1,50** | cible [1,3 – 1,6] | ✅ |
| G1 (bis) Densité globale, ponts compris | 26 / 14 = 1,86 | ponts comptés à part (errata E5) | ✅ |
| **G2** Plus longue chaîne HARD **intra** | **4 nœuds** — `PLACE_VALUE_TENTHS → PLACE_VALUE_HUNDREDTHS → PLACE_VALUE_THOUSANDTHS → MULT_DIV_POW10` | à documenter (fractions = 11) | ✅ documentée |
| G2 (bis) Chaîne HARD sur le **graphe combiné** | **9 nœuds** via le pont `FRACTION_AS_PART → PLACE_VALUE_TENTHS` | idem | ✅ documentée |
| **G3** Racines | `PLACE_VALUE_TENTHS` — **racine locale assumée**, en attente du futur domaine place-value entier ; elle a déjà un pont fraction entrant, donc **0 racine orpheline sur le graphe combiné** | toute racine assumée + prérequis futur nommé | ✅ (❓ **arbitrage 2**) |
| **G4** Ponts vers des codes existants en base | 5/5 vérifiés (`FRACTION_AS_PART`, `EQUIVALENCE_COMPUTE`, `NUMBER_LINE_PLACE`, `COMPARE_SAME_DENOM`) | aucun code inventé | ✅ |
| **G5** Répartition cognitive | **9 APPLY / 4 REASON / 1 RECALL** — G4 : 3/2/1 · G5 : 6/2/0 → **≥ 2 REASON par grade** | ≥ 2 REASON / grade | ✅ (❓ **arbitrage 3**) |
| **G6** Médianes de prior | **G4 = 1620** · **G5 = 1890** — repères fractions : G4 = **1660**, G5 = **1900** | ±100 Elo ou écart argumenté | ✅ dans la tolérance (❓ **arbitrage 1**) |
| **G7** Avertissement « priors experts, non mesurés » | présent (en-tête de ce document) | obligatoire | ✅ |
| **S1** DAG strict sur le graphe **combiné** (fractions + décimaux + ponts) | **0 cycle** | aucun cycle | ✅ |
| **S6** Bornes de poids | HARD ∈ [0,72 – 0,85] · SOFT ∈ [0,55 – 0,65] | HARD [0,65 – 0,90] · SOFT ≤ 0,70 | ✅ |
| **E4** `prior(cible) > prior(source)` sur **tous** les HARD | **26/26 OK**, ponts compris | monotonie | ✅ **aucune exception à documenter** |
| **N5** ≥ 3 `item_contexts` par nœud | 4 ou 5 partout (min 4) | ≥ 3 | ✅ |

**Lecture** : le draft est **structurellement conforme**. Ce que la machine ne peut pas juger — et qui est l'objet de votre lecture — c'est la **justesse didactique** : le découpage des gestes, la plausibilité des priors, la nécessité des HARD.

> **Grille GRAPHE — signature**
>
> | Point | Lecteur A (didacticien) | Lecteur B (enseignant EAU) |
> |---|---|---|
> | G1 densité | ☐ | ☐ |
> | G2 chaînes | ☐ | ☐ |
> | G3 racines | ☐ | ☐ |
> | G4 ponts | ☐ | ☐ |
> | G5 cognitif | ☐ | ☐ |
> | G6 médianes | ☐ | ☐ |
> | G7 avertissement | ☐ | ☐ |

---

## 2. Fiches NŒUD (14) — checklist N1–N6

**Rappel des points** :
**N1** granularité (1 geste cognitif, 1 contrainte procédurale max ; pas de fragmentation par contexte) · **N2** nommage (regex + lisible) · **N3** prior plausible (médiane de grade + ajustement cognitif + position dans la chaîne) · **N4** cognitif correct (heuristique A1.5) · **N5** ≥ 3 contextes générables · **N6** labels bilingues fidèles

**Repères de prior** : **G4 = 1660** · **G5 = 1900** *(médianes fractions observées en base)*.

---

### N-01 · `MATH.G4.NBT.PLACE_VALUE_TENTHS` — G4 · **RECALL** · prior **1520**
**EN** *Identify the tenths place in a decimal* — **AR** تحديد منزلة الأعشار في العدد العشري
**Contextes (4)** : `identify digit place` · `tenths as 1/10` · `expanded form` · `money model (dirhams/fils)`
**Position** : racine locale du domaine. Prérequis entrant : pont HARD 0,75 depuis `MATH.G3.NF.FRACTION_AS_PART` (prior 1400).

**Pré-avis du rédacteur** :
- **N1** ✅ Un seul geste : nommer la position d'un chiffre.
- **N3** ⚠️ **1520, soit −140 sous la médiane G4 (1660).** Justifié par le temps 2 (RECALL abaisse) **et** le temps 3 (racine du domaine). L'écart est important : c'est le nœud qui tire la médiane G4 décimaux (1620) sous celle des fractions — **cf. arbitrage 1**.
- **N4** ✅ RECALL : la réponse est un nom de place stocké en mémoire.
- **N5** ⚠️ **`money model (dirhams/fils)` est mal placé ici.** 1 dirham = **100** fils → le modèle monétaire porte naturellement les **centièmes** (أجزاء المئة), pas les dixièmes. Sur un item « quelle est la place du 3 dans 4,35 AED ? », le fils désigne le centième. **Le contexte serait mieux sur `PLACE_VALUE_HUNDREDTHS`.** *(Lecteur B : c'est votre terrain — le manuel MoE introduit-il le dirham/fils dès les dixièmes ?)*
- **N6** ✅ Label AR conforme au glossaire (منزلة الأعشار).

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** didacticien | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** enseignant EAU | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-02 · `MATH.G4.NBT.PLACE_VALUE_HUNDREDTHS` — G4 · **APPLY** · prior **1580**
**EN** *Identify the hundredths place in a decimal* — **AR** تحديد منزلة أجزاء المئة في العدد العشري
**Contextes (4)** : `identify digit place` · `hundredths as 1/100` · `expanded form` · `zero as placeholder`

**Pré-avis du rédacteur** :
- 🔴 **N1 + N4 — le point le plus contestable du draft.** Ce nœud a **le même geste cognitif** que N-01 (« identifier la place d'un chiffre »), **les mêmes contextes** (`identify digit place`, `expanded form`), et se distingue seulement par la **magnitude**. Or la règle A1.1 dit : *« Une variation qui ne change que le contexte ou la difficulté → tag d'item, jamais un nœud »*, et l'anti-pattern interdit est nommément la fragmentation par magnitude. **Si le geste est le même, ce devrait être un tag, pas un nœud.**
- **Contre-argument (celui de la doctrine)** : la Méthodologie utilise elle-même `TENTHS → HUNDREDTHS` (HARD 0,85) comme **exemple canonique** de HARD. Et le test T3 répond OUI : *un élève peut maîtriser les dixièmes et échouer systématiquement les centièmes* parce qu'il lui manque un geste (la relation ×10 entre places adjacentes), pas de l'entraînement. **La scission est alors justifiée.**
- **Ce qu'il faut trancher** : **si** la scission est justifiée par la relation ×10, alors ce nœud n'est **pas** un RECALL de plus — c'est bien un APPLY (il faut *dériver* la place). ✅ Le cognitif APPLY est cohérent avec cette lecture. **Mais alors N-01 (RECALL) et N-07 (APPLY) doivent être justifiés par la même logique** — et la chaîne à 3 nœuds (dixièmes / centièmes / millièmes) doit être défendue **explicitement**, sinon elle ressemble à `ADD_DECIMALS_TENTHS / _HUNDREDTHS`, l'anti-pattern nommé dans la doctrine. **→ arbitrage 3.**
- **N3** ✅ 1580 (+60 sur N-01) : cohérent avec le temps 3.
- **N5** ✅ `zero as placeholder` : excellent contexte (misconception A4).
- **N6** ✅ أجزاء المئة = forme canonique du glossaire.

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** didacticien | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** enseignant EAU | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-03 · `MATH.G4.NBT.READ_WRITE_DECIMAL` — G4 · **APPLY** · prior **1600**
**EN** *Read and write decimal numbers* — **AR** قراءة الأعداد العشرية وكتابتها
**Contextes (4)** : `words to numeral` · `numeral to words` · `trailing zero (0.5 vs 0.50)` · `money notation`

**Pré-avis** :
- **N1** ⚠️ **« Lire » ET « écrire » sont deux gestes inverses.** Le test T1 (« ce nœud demande-t-il **deux stratégies différentes** ? ») mérite une réponse motivée : passer de `0.35` → « trente-cinq centièmes » (décodage) et l'inverse (encodage) mobilisent la même table de correspondance, dans les deux sens. **Je penche pour un seul nœud** (une seule table, deux sens de lecture — T1 → NON), mais c'est votre appel : les deux contextes `words to numeral` / `numeral to words` sont précisément là pour porter la variation. **Si vous scindez, il faudra 2 nœuds et refaire les arêtes.**
- **N3** ✅ 1600, entre N-02 (1580) et la médiane. Cohérent.
- **N4** ✅ APPLY (procédure connue).
- **N5** ✅ `trailing zero (0.5 vs 0.50)` = misconception A4, générable.
- **N6** ✅ Conforme au glossaire (قراءة … وكتابتها).

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-04 · `MATH.G4.NBT.DECIMAL_AS_FRACTION` — G4 · **REASON** · prior **1660**
**EN** *Convert between decimals and fractions* — **AR** التحويل بين الأعداد العشرية والكسور
**Contextes (4)** : `tenths` · `hundredths` · `simplifiable (0.5 = 1/2)` · `greater than one (1.25)`
**Prérequis** : HARD 0,78 ← `PLACE_VALUE_HUNDREDTHS` · HARD 0,80 ← `FRACTION_AS_PART` (pont) · HARD 0,72 ← `EQUIVALENCE_COMPUTE` (pont)

**Pré-avis** :
- **N1** ⚠️ Même remarque que N-03 : « convertir décimal→fraction » et « fraction→décimal » sont deux sens. Ici la question est plus sérieuse, car les stratégies **divergent** : `0.75 → 75/100 → 3/4` (lecture de place + simplification) vs `3/4 → 0.75` (division ou équivalence sur 100). **T1 → possiblement OUI.** À trancher. *(C'est le nœud le mieux connecté du domaine — 3 HARD entrants dont 2 ponts. Le scinder impacte les ponts.)*
- **N3** ✅ 1660 = pile la médiane G4 fractions. Cohérent (REASON, mais nœud d'entrée).
- **N4** ✅ REASON : il faut choisir entre lecture de place et équivalence, puis décider de simplifier.
- **N5** ✅ 4 contextes, dont le piège `simplifiable`.
- **N6** ✅.

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-05 · `MATH.G4.NBT.DECIMAL_NUMBER_LINE` — G4 · **APPLY** · prior **1640**
**EN** *Place a decimal on a number line* — **AR** تمثيل عدد عشري على خط الأعداد
**Contextes (4)** : `tenths line` · `hundredths zoom` · `between two marks` · `estimate position`

**Pré-avis** : ✅ **Le nœud le plus propre du draft.** N1 (un geste : situer), N3 (1640, sous la médiane, cohérent avec sa position amont), N4 (APPLY), N5 (4 contextes générables, dont le zoom), N6 (label AR = `تمثيل`, forme canonique décidée au glossaire — les fractions disent `تحديد موضع`, divergence assumée et documentée). **Rien à signaler.**

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-06 · `MATH.G4.NBT.COMPARE_DECIMALS` — G4 · **REASON** · prior **1700**
**EN** *Compare and order decimal numbers* — **AR** مقارنة الأعداد العشرية وترتيبها
**Contextes (4)** : `same number of places` · `different number of places (longer-is-larger trap)` · `trailing zero trap` · `ordering 3+ numbers`

**Pré-avis** :
- **N1** ⚠️ « Comparer » (2 nombres) **et** « ordonner » (3+) sont-ils un seul geste ? Le contexte `ordering 3+ numbers` traite la seconde comme une variation. Défendable (même critère appliqué n fois), mais notez que `COMPARE_DECIMALS` est le **nœud le plus haut de G4 (1700)** et qu'il porte **deux misconceptions majeures** — c'est un nœud « lourd ». **T1 → à répondre explicitement.**
- **N3** ✅ 1700, +40 au-dessus de la médiane G4 fractions : REASON + position aval. Conforme au temps 2 (« décimaux : `COMPARE_DECIMALS` REASON à +80 de la médiane G4 » — la Méthodologie cite +80, on est à +40 sur la médiane fractions ; **écart de doc à corriger, pas de fond**).
- **N4** ✅ REASON, incontestable (le piège « longer-is-larger » exige de raisonner sur la magnitude, pas d'appliquer une procédure).
- **N5** ✅ Excellent : les 2 pièges classiques sont encodés comme contextes.
- **N6** ✅.

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-07 · `MATH.G5.NBT.PLACE_VALUE_THOUSANDTHS` — G5 · **APPLY** · prior **1820**
**EN** *Identify the thousandths place and relate adjacent places* — **AR** تحديد منزلة أجزاء الألف والعلاقة بين المنازل المتجاورة
**Contextes (4)** : `identify digit place` · `adjacent places (x10 relation)` · `expanded form` · `zero as placeholder`

**Pré-avis** :
- **N1** ⚠️ Le label porte **deux** gestes : « identifier la place des millièmes » **et** « relier les places adjacentes (×10) ». La règle est « 1 geste + **1 contrainte procédurale max** ». Le second geste (relation ×10) est le **vrai contenu cognitif** du nœud et ce qui le distingue de N-01/N-02. **Recommandation : renommer** (`PLACE_VALUE_ADJACENT` ou `PLACE_VALUE_RELATIONS`) pour que le nom dise le geste réel — cf. test N2 n°2 (« un enseignant qui lit le SKILL devine le geste évalué »). *(Le renommage est libre : ce nœud est en `draft`, aucun item ni mapping ne pointe dessus. Une fois `active`, le renommage est **interdit**, A1.2 test 4.)*
- **N3** ✅ 1820, −80 sous la médiane G5 (1900) : nœud d'entrée de G5. Cohérent.
- **N4** ⚠️ APPLY. Si le geste central est la **relation ×10 entre places**, c'est un raisonnement sur la structure → **REASON** serait défendable. *(Effet de bord : G5 passerait à 3 REASON, ce qui reste conforme.)*
- **N5** ✅ · **N6** ✅ (أجزاء الألف, المنازل المتجاورة : conformes au glossaire).

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-08 · `MATH.G5.NBT.ADD_DECIMALS` — G5 · **APPLY** · prior **1840**
**EN** *Add decimal numbers* — **AR** جمع الأعداد العشرية
**Contextes (5)** : `same number of places` · `different number of places (alignment)` · `carrying` · `crossing a whole` · `money`

**Pré-avis** : ✅ Conforme sur les 6 points. N1 : un seul algorithme (aligner, additionner) — l'alignement est bien traité en **tag**, pas en nœud (exemple explicite de la doctrine A1.1). N3 : 1840, sous la médiane G5, cohérent (nœud amont de G5). N4 : APPLY (algorithme unique, sans décision). N5 : 5 contextes, le maximum du draft. N6 : conforme.
**Une seule réserve (N4)** : `crossing a whole` (ex. 0.8 + 0.5 = 1.3) est une source d'erreur qui relève de la compréhension, pas de l'exécution. Si beaucoup d'items l'utilisent, le nœud dérive vers REASON. **Non bloquant** — c'est le rôle du tag.

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-09 · `MATH.G5.NBT.ROUND_DECIMAL` — G5 · **APPLY** · prior **1860**
**EN** *Round a decimal number* — **AR** تقريب عدد عشري
**Contextes (4)** : `to nearest whole` · `to tenths` · `to hundredths` · `digit 5 at boundary`
**Prérequis** : HARD 0,75 ← `COMPARE_DECIMALS` · SOFT 0,55 ← `PLACE_VALUE_THOUSANDTHS`

**Pré-avis** :
- ⚠️ **N5 — les 3 premiers contextes sont des variations de magnitude, pas des dimensions.** `to nearest whole` / `to tenths` / `to hundredths` : c'est le **même geste**, à trois échelles. Le seul contexte qui apporte une **dimension** différente est `digit 5 at boundary` (le piège). La doctrine A1.6 demande de couvrir **magnitude / représentation / pièges / registre** : ici on a **magnitude ×3 + piège ×1**, mais **aucune représentation** (droite numérique !) et **aucun registre** (argent — arrondir un prix au dirham près est *le* cas d'usage EAU). **Recommandation : ajouter `number line model` et `money rounding (to nearest dirham)`.** Cela porte le nœud à 6 contextes et améliore l'étalement de difficulté.
- **N1** ✅ · **N3** ✅ 1860 · **N4** ✅ APPLY · **N6** ✅ (تقريب, conforme).

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-10 · `MATH.G5.NBT.SUB_DECIMALS` — G5 · **APPLY** · prior **1880**
**EN** *Subtract decimal numbers* — **AR** طرح الأعداد العشرية
**Contextes (5)** : `same number of places` · `different number of places (alignment)` · `borrowing` · `from a whole (3 - 0.45)` · `money change`

**Pré-avis** : ✅ Conforme sur les 6 points. `from a whole (3 − 0.45)` est le piège classique (il faut lire 3 comme 3,00) ; `money change` ancre le registre EAU (الباقي). N3 : 1880 > 1840 (`ADD_DECIMALS`) — cohérent, la soustraction est plus dure. N4 : APPLY.
**Réserve (N6)** : le glossaire prescrit **إعادة التجميع** pour *regrouping* et proscrit **حمل / استلاف** — le contexte s'appelle `borrowing`. C'est un tag interne (en anglais), donc **hors périmètre du glossaire AR**, mais les **stems** produits devront dire إعادة التجميع. *(Point pour la linguiste, pas pour vous.)*

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-11 · `MATH.G5.NBT.MULT_DIV_POW10` — G5 · **APPLY** · prior **1900**
**EN** *Multiply and divide a decimal by powers of ten* — **AR** ضرب عدد عشري وقسمته على قوى العدد عشرة
**Contextes (4)** : `x10 x100 x1000` · `/10 /100 /1000` · `shift direction reasoning` · `unit conversion`

**Pré-avis** :
- **N1** ⚠️ « Multiplier » **et** « diviser » par une puissance de 10 : deux gestes **inverses**. Défendable comme un seul nœud (le geste réel est *décaler la virgule* ; le sens est le paramètre) — mais alors le contexte `shift direction reasoning` est **la contrainte procédurale**, et le test T3 mérite réponse : *un élève peut-il maîtriser ×10 et échouer systématiquement ÷10 par manque de geste ?* **Mon avis : oui, très fréquemment** (le sens du décalage est LA misconception du domaine). **Je penche pour la scission**, ou à tout le moins pour une réponse écrite.
- **N4** ⚠️ APPLY, alors qu'un contexte s'appelle littéralement `shift direction **reasoning**`. Si le geste central est de **raisonner sur le sens** du décalage, l'heuristique A1.5 (« l'élève doit-il **choisir** ou raisonner sur la magnitude/structure ? ») pousse vers **REASON**. **Incohérence interne du draft : le nom du contexte contredit le niveau cognitif.**
- **N3** ✅ 1900 = médiane G5. · **N5** ✅ (`unit conversion` = registre : km/m, kg/g). · **N6** ✅.

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-12 · `MATH.G5.NBT.MULT_DECIMAL_WHOLE` — G5 · **APPLY** · prior **1920**
**EN** *Multiply a decimal by a whole number* — **AR** ضرب عدد عشري في عدد صحيح
**Contextes (4)** : `single-digit whole` · `two-digit whole` · `point placement` · `estimation check`
**Prérequis** : ⚠️ **SOFT 0,60 ← `MULT_DIV_POW10` — c'est son SEUL prérequis.**

**Pré-avis** :
- 🔴 **Le problème de ce nœud n'est pas dans la fiche NŒUD, il est dans ses arêtes.** `MULT_DECIMAL_WHOLE` est le **seul nœud du domaine sans aucun prérequis HARD**. Conséquence directe : quand un élève échoue `MULT_DECIMAL_DECIMAL` (N-14), la **clôture amont des HARD** — c'est-à-dire le **diagnostic causal**, l'argument de vente d'Atlas — s'arrête sur `MULT_DECIMAL_WHOLE` et ne peut **rien** désigner en amont. Le moteur dira « la cause racine est : multiplier un décimal par un entier » — c'est-à-dire *rien*.
- **Question à trancher** : `MULT_DECIMAL_WHOLE` n'exige-t-il vraiment **aucun** prérequis logique ? Candidats évidents : `PLACE_VALUE_HUNDREDTHS` (placer la virgule au produit suppose de compter les décimales) ou `ADD_DECIMALS` (la multiplication par un entier *est* une addition répétée). **Voir arête E-17 et arbitrage 4.**
- **N1** ✅ · **N3** ✅ 1920 · **N4** ✅ APPLY (algorithme unique : multiplier comme des entiers, replacer la virgule) · **N5** ✅ · **N6** ✅ (régime `ضرب X في Y`, conforme au glossaire).

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-13 · `MATH.G5.NBT.DIV_DECIMAL_WHOLE` — G5 · **REASON** · prior **1950**
**EN** *Divide a decimal by a whole number* — **AR** قسمة عدد عشري على عدد صحيح
**Contextes (4)** : `exact quotient` · `quotient needs added zero` · `point placement` · `sharing model`

**Pré-avis** : ✅ Conforme. N4 : REASON justifié (`quotient needs added zero` = il faut **décider** d'ajouter un zéro, ce n'est pas dans l'algorithme naïf). N3 : 1950, +50 au-dessus de la médiane G5, cohérent avec REASON + position aval. N5 : `sharing model` = registre. N6 : régime `قسمة X على Y` conforme.
**Réserve (arête)** : son seul HARD entrant vient de `PLACE_VALUE_HUNDREDTHS` (0,72) — un nœud **G4**, très en amont. Le diagnostic causal d'un échec en division renverra donc « valeur de position des centièmes », ce qui est probablement **trop loin** pour être actionnable par l'enseignant. *(À mettre en regard de l'arbitrage 4.)*

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

### N-14 · `MATH.G5.NBT.MULT_DECIMAL_DECIMAL` — G5 · **REASON** · prior **1960**
**EN** *Multiply a decimal by a decimal* — **AR** ضرب عدد عشري في عدد عشري
**Contextes (4)** : `tenths x tenths` · `counting decimal places` · `product smaller than factors` · `estimation check`

**Pré-avis** : ✅ Conforme, et c'est le nœud le mieux argumenté du draft. N1 : la scission d'avec N-12 est explicitement justifiée par la doctrine (*« Multiplier deux décimaux exige le comptage des décimales au produit et le raisonnement "le produit peut être plus petit que les facteurs" — stratégie distincte »*). N4 : REASON, incontestable. N3 : 1960, le prior le plus haut du domaine, en bout de chaîne. N5 : `product smaller than factors` = LA misconception. N6 : conforme.

| | N1 | N2 | N3 | N4 | N5 | N6 |
|---|---|---|---|---|---|---|
| **A** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| **B** | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

*Désaccord / remarque* : ______________________________________________________________

---

## 3. Fiches ARÊTE (26) — checklist E1–E4

**Rappel des points** :
**E1** type justifié (test : *« peut-on construire un item honnête de la CIBLE qu'un élève réussirait tout en échouant SYSTÉMATIQUEMENT la source ? »* NON → HARD · OUI mais corrélé → SOFT) — **et le blocage de routing d'un HARD doit être pédagogiquement défendable**
**E2** poids dans la grille d'ancres — **rappel : plancher méthodologique HARD = 0,65–0,70** · plafond SOFT = 0,70
**E3** pas de cycle — ✅ **validateur exécuté sur le graphe combiné, 0 cycle** (rapport joint, §1)
**E4** `prior(cible) > prior(source)` — ✅ **26/26 vérifiés**, aucune exception à documenter

*E3 et E4 sont donc acquis pour les 26 arêtes. **Votre lecture porte sur E1 et E2.***

### 3.1 — Arêtes intra-domaine (21)

| # | Source → Cible | Type | Poids | Ancre sémantique attendue (A1.3) | Pré-avis E1 / E2 | **A** | **B** |
|---|---|---|---|---|---|---|---|
| E-01 | `PLACE_VALUE_TENTHS` → `PLACE_VALUE_HUNDREDTHS` | HARD | **0,85** | *dépendance quasi-mécanique* | ✅ Exemple canonique de la doctrine. Blocage de routing défendable. **Mais dépend du sort de N-02 (arbitrage 3).** | ☐ | ☐ |
| E-02 | `PLACE_VALUE_HUNDREDTHS` → `PLACE_VALUE_THOUSANDTHS` | HARD | **0,85** | *dépendance quasi-mécanique* | ✅ Idem. Cohérent avec E-01. | ☐ | ☐ |
| E-03 | `PLACE_VALUE_TENTHS` → `READ_WRITE_DECIMAL` | HARD | **0,80** | *prérequis fort* | ✅ On ne lit pas « trois dixièmes » sans savoir ce qu'est un dixième. | ☐ | ☐ |
| E-04 | `PLACE_VALUE_HUNDREDTHS` → `READ_WRITE_DECIMAL` | HARD | **0,75** | *prérequis fort, contournable à la marge* | ⚠️ **Double HARD entrant** avec E-03. Justifiable (lire `0,35` exige les deux places), mais **le routing bloquera la lecture tant que les DEUX places ne sont pas maîtrisées** — or on peut parfaitement lire `0,3`. **Question : le poids 0,75 est-il un HARD ou un SOFT fort ?** | ☐ | ☐ |
| E-05 | `READ_WRITE_DECIMAL` → `DECIMAL_NUMBER_LINE` | HARD | **0,75** | *prérequis fort* | ✅ Placer suppose de lire. | ☐ | ☐ |
| E-06 | `PLACE_VALUE_HUNDREDTHS` → `DECIMAL_AS_FRACTION` | HARD | **0,78** | *prérequis fort* | ✅ `0,35 = 35/100` : la place **est** le dénominateur. | ☐ | ☐ |
| E-07 | `PLACE_VALUE_HUNDREDTHS` → `COMPARE_DECIMALS` | HARD | **0,82** | *quasi-mécanique* | ✅ Le piège « longer-is-larger » se résout **par** la valeur de position. Blocage défendable. | ☐ | ☐ |
| E-08 | `DECIMAL_NUMBER_LINE` → `COMPARE_DECIMALS` | SOFT | **0,60** | *corrélation modérée* | ✅ La droite **aide** à comparer, ne la conditionne pas. Test E1 → OUI (comparer par la place, sans droite). | ☐ | ☐ |
| E-09 | `DECIMAL_AS_FRACTION` → `COMPARE_DECIMALS` | SOFT | **0,55** | *corrélation modérée* | ✅ Idem. | ☐ | ☐ |
| E-10 | `COMPARE_DECIMALS` → `ROUND_DECIMAL` | HARD | **0,75** | *prérequis fort* | ✅ Arrondir = décider de quel repère on est **le plus proche** ⇒ comparer. Le HARD est bien fondé. | ☐ | ☐ |
| E-11 | `PLACE_VALUE_THOUSANDTHS` → `ROUND_DECIMAL` | SOFT | **0,55** | *corrélation modérée* | ✅ Arrondir au centième ne requiert pas les millièmes… sauf quand si. SOFT est le bon choix (pas de blocage). | ☐ | ☐ |
| E-12 | `PLACE_VALUE_HUNDREDTHS` → `ADD_DECIMALS` | HARD | **0,80** | *prérequis fort* | ✅ Aligner la virgule = aligner les places. | ☐ | ☐ |
| E-13 | `READ_WRITE_DECIMAL` → `ADD_DECIMALS` | HARD | **0,72** | *prérequis nécessaire mais partiellement* | ⚠️ **Deuxième HARD entrant**. Le poids 0,72 est **juste au-dessus du plancher (0,65–0,70)** : l'ancre correspondante est « prérequis nécessaire **mais partiellement** ». **Un HARD "partiel" bloque le routing tout autant qu'un HARD à 0,90** (le diagnostic causal traite tous les HARD identiquement — errata E4). **Est-ce vraiment un HARD, ou un SOFT à 0,70 ?** | ☐ | ☐ |
| E-14 | `PLACE_VALUE_HUNDREDTHS` → `SUB_DECIMALS` | HARD | **0,80** | *prérequis fort* | ✅ Symétrique de E-12. | ☐ | ☐ |
| E-15 | `ADD_DECIMALS` → `SUB_DECIMALS` | SOFT | **0,65** | *corrélation forte (≤ 0,70)* | ✅ Exemple explicite de la doctrine (*« la soustraction ne requiert pas logiquement l'addition — un blocage de routing serait abusif »*). | ☐ | ☐ |
| E-16 | `PLACE_VALUE_THOUSANDTHS` → `MULT_DIV_POW10` | HARD | **0,78** | *prérequis fort* | ⚠️ Défendable (décaler la virgule = changer de place), **mais** pourquoi passer par les **millièmes** (G5) et non par les **centièmes** ? `2,5 × 10` ne mobilise aucun millième. Le HARD sur `THOUSANDTHS` **bloque le routing** d'un élève qui saurait très bien faire ×10. **Le vrai prérequis est probablement la relation ×10 entre places adjacentes** — c'est-à-dire le **second geste** de N-07, celui qu'il faudrait isoler (cf. N-07). | ☐ | ☐ |
| E-17 | `MULT_DIV_POW10` → `MULT_DECIMAL_WHOLE` | **SOFT** | **0,60** | *corrélation modérée* | 🔴 **Point d'arbitrage 4.** C'est le **seul** prérequis de `MULT_DECIMAL_WHOLE`, et il est SOFT ⇒ **le nœud n'a aucun parent HARD** ⇒ le **diagnostic causal ne peut rien remonter** au-delà de lui, y compris pour son enfant `MULT_DECIMAL_DECIMAL`. **Manque-t-il une arête HARD ?** | ☐ | ☐ |
| E-18 | `MULT_DECIMAL_WHOLE` → `MULT_DECIMAL_DECIMAL` | HARD | **0,80** | *prérequis fort* | ✅ Justifié par la doctrine (stratégie distincte, HARD 0,8). | ☐ | ☐ |
| E-19 | `MULT_DIV_POW10` → `MULT_DECIMAL_DECIMAL` | SOFT | **0,62** | *corrélation modérée* | ✅ | ☐ | ☐ |
| E-20 | `PLACE_VALUE_HUNDREDTHS` → `DIV_DECIMAL_WHOLE` | HARD | **0,72** | *nécessaire mais partiellement* | ⚠️ Même remarque qu'E-13 : poids proche du plancher, et **saut de 4 nœuds** dans le graphe (G4 → G5 aval). Le diagnostic causal d'un échec en division renverra « centièmes » — **peu actionnable**. Un prérequis intermédiaire (`ADD_DECIMALS` ? `MULT_DECIMAL_WHOLE` en HARD ?) serait plus utile. | ☐ | ☐ |
| E-21 | `MULT_DECIMAL_WHOLE` → `DIV_DECIMAL_WHOLE` | SOFT | **0,60** | *corrélation modérée* | ⚠️ Multiplication et division sont **inverses** : la corrélation est réelle, mais la division n'exige pas la multiplication. SOFT est défendable. **Sauf si** on veut que le diagnostic remonte (cf. E-20). | ☐ | ☐ |

### 3.2 — Ponts inter-domaines (5) — *comptés à part (errata E5)*

| # | Source (fractions) → Cible (décimaux) | Type | Poids | Pré-avis E1 / E2 | **A** | **B** |
|---|---|---|---|---|---|---|
| P-01 | `MATH.G3.NF.FRACTION_AS_PART` (1400) → `PLACE_VALUE_TENTHS` (1520) | HARD | **0,75** | ✅ Un dixième **est** une fraction a/b. Sans le concept de part d'un tout, la place décimale n'a pas de sens. Blocage défendable. **C'est le pont qui fait que `PLACE_VALUE_TENTHS` n'est pas orpheline (S4).** | ☐ | ☐ |
| P-02 | `MATH.G3.NF.FRACTION_AS_PART` (1400) → `DECIMAL_AS_FRACTION` (1660) | HARD | **0,80** | ✅ Évident. | ☐ | ☐ |
| P-03 | `MATH.G4.NF.EQUIVALENCE_COMPUTE` (1620) → `DECIMAL_AS_FRACTION` (1660) | HARD | **0,72** | ⚠️ `0,75 → 75/100 → 3/4` exige l'équivalence. **Mais** convertir `0,3 → 3/10` ne l'exige pas. Le test E1 répond donc **OUI** (item honnête de la cible réussi sans la source) ⇒ **la règle dit SOFT**. Le HARD **bloquera** le routing vers `DECIMAL_AS_FRACTION` pour un élève qui n'a pas `EQUIVALENCE_COMPUTE` — alors qu'il pourrait très bien faire les items « dixièmes ». 🔴 **Recommandation : SOFT 0,65**, ou restreindre le HARD au contexte `simplifiable`. **Le poids 0,72, juste au-dessus du plancher, trahit le doute du rédacteur.** | ☐ | ☐ |
| P-04 | `MATH.G3.NF.NUMBER_LINE_PLACE` (1480) → `DECIMAL_NUMBER_LINE` (1640) | SOFT | **0,60** | ✅ Bon appel : le geste se transfère, mais placer 0,7 ne requiert pas d'avoir placé 3/4. | ☐ | ☐ |
| P-05 | `MATH.G3.NF.COMPARE_SAME_DENOM` (1500) → `COMPARE_DECIMALS` (1700) | SOFT | **0,55** | ✅ Corrélation pédagogique, pas de nécessité. | ☐ | ☐ |

> **Grille ARÊTE — verdict global**
>
> | | Lecteur A | Lecteur B |
> |---|---|---|
> | **E1** — tous les types sont justifiés | ☐ | ☐ |
> | **E2** — tous les poids sont dans la grille d'ancres | ☐ | ☐ |
> | **E3** — DAG validé sur le graphe combiné (rapport joint) | ☐ | ☐ |
> | **E4** — monotonie des priors sur les HARD | ☐ | ☐ |

---

## 4. Points d'arbitrage — posés comme questions explicites

*Ce sont les questions qui **doivent** ressortir de la séance de réconciliation avec une réponse écrite. Les deux premières sont celles déjà identifiées par le rédacteur ; les deux suivantes sortent de cette relecture.*

---

### ❓ Arbitrage 1 — **La médiane G4 des décimaux (1620) est sous celle des fractions (1660). Est-ce défendable ?**

**Les faits.** Priors G4 décimaux : 1520, 1580, 1600, 1640, 1660, 1700 → **médiane 1620**. Repère fractions G4 : **1660**. Écart : **−40 Elo**, dans la tolérance du test opératoire n°1 (±100), donc **non bloquant** — mais la doctrine exige qu'un écart soit *« argumenté par écrit et soumis à l'arbitrage de la revue »*.

**Position du rédacteur** (à confirmer ou casser) :
> *« Défendable : ce sont des **nœuds d'entrée de domaine** (CCSS 4.NF.C). Un élève de G4 rencontre les décimaux pour la première fois ; les fractions G4, elles, sont déjà au 6ᵉ ou 7ᵉ maillon de leur chaîne. Comparer les deux médianes compare des positions différentes dans le curriculum, pas des difficultés intrinsèques. »*

**Mon avis contradictoire** : l'argument est bon **mais il prouve trop**. Si les décimaux G4 sont plus faciles *parce qu'ils sont en entrée de domaine*, alors **tout nouveau domaine** aura une médiane basse, et le repère de grade perd son sens. La vraie question est : **un élève de G4 réussit-il plus souvent « identifier la place des dixièmes » que « générer une fraction équivalente » ?** Si oui, l'écart est réel et le prior est juste. Si non, on a sous-estimé les décimaux, et **tous les items décimaux seront servis trop faciles au démarrage** (le prior d'item dérive du prior de nœud, ±250 Elo).

**Enjeu concret** : un prior trop bas fait converger l'Elo par le bas — l'élève voit des items faciles, réussit, et il faut plus de réponses pour l'atteindre. Coût : la longueur de session au pilote.

> **Question au didacticien** : à niveau G4 équivalent, la valeur de position décimale est-elle **plus facile** que l'équivalence de fractions ?
> ☐ Oui, 1620 est juste · ☐ Non, remonter la médiane G4 décimaux à ______ · ☐ Autre : ______________
>
> **Question à l'enseignant EAU** : dans vos classes, où placez-vous les décimaux par rapport aux fractions en G4 ?
> ☐ Plus facile · ☐ Comparable · ☐ Plus difficile · Commentaire : ________________________

---

### ❓ Arbitrage 2 — **`PLACE_VALUE_TENTHS` est une racine locale en attente du domaine « place-value entier ». Peut-on produire les items sans ce domaine ?**

**Les faits.** `PLACE_VALUE_TENTHS` n'a **aucun prérequis intra-domaine** — c'est la racine du domaine décimaux. Sa seule dépendance est le **pont** `FRACTION_AS_PART → PLACE_VALUE_TENTHS` (HARD 0,75). La contrainte S4 est donc satisfaite **sur le graphe combiné** (elle a une arête entrante), mais **le vrai prérequis cognitif — la valeur de position des entiers (unités/dizaines/centaines) — n'existe pas encore dans le référentiel.**

**Position du rédacteur** : racine locale assumée, prérequis futur **nommé** (« futur domaine place-value entier »). Conforme à G3.

**Mon avis contradictoire** : c'est conforme à la doctrine, **mais** cela crée un angle mort de diagnostic. Un élève qui échoue `PLACE_VALUE_TENTHS` sera diagnostiqué avec une lacune sur… `FRACTION_AS_PART` (le seul HARD amont). **Or la vraie cause est très probablement la valeur de position des entiers**, que le produit ne mesure pas. **Le diagnostic causal donnera une réponse fausse — pas « je ne sais pas », mais une fausse piste.**

> **Question** : est-ce acceptable pour le pilote, ou faut-il ajouter 2–3 nœuds « place-value entier » (G2–G3) avant la production décimaux ?
> ☐ Acceptable (on documente la limite) · ☐ Non : il faut le domaine entier d'abord · ☐ Compromis : ______________

---

### ❓ Arbitrage 3 — **La chaîne dixièmes / centièmes / millièmes est-elle 3 nœuds, ou 1 nœud + un tag de magnitude ?**

*Question ouverte par cette relecture. Elle conditionne 3 nœuds (N-01, N-02, N-07) et 2 arêtes (E-01, E-02).*

**Le conflit, dans la doctrine elle-même** :

| Ce qui plaide pour **1 nœud + tag** | Ce qui plaide pour **3 nœuds** |
|---|---|
| A1.1 : *« Une variation qui ne change que le **contexte ou la difficulté** → tag d'item, **jamais** un nœud »* | A1.3 donne `PLACE_VALUE_TENTHS → PLACE_VALUE_HUNDREDTHS` (HARD 0,85) comme **exemple canonique** de HARD |
| L'anti-pattern nommément interdit est `ADD_DECIMALS_TENTHS` / `_HUNDREDTHS` — **la fragmentation par magnitude** | Test T3 : un élève **peut** maîtriser les dixièmes et échouer les centièmes par manque du geste « ×10 entre places adjacentes » |
| Les 3 nœuds partagent les **mêmes contextes** (`identify digit place`, `expanded form`, `zero as placeholder`) | Les 3 nœuds n'ont pas le même cognitif (RECALL / APPLY / APPLY) — ce qui suppose bien des gestes différents |

**Mon avis** : les 3 nœuds sont défendables **à condition** que ce qui les distingue soit **nommé**. Aujourd'hui, seul N-07 nomme la relation ×10 (« relate adjacent places »). N-01 et N-02 sont, sur le papier, le **même geste à deux échelles** — donc l'anti-pattern. **Recommandation** : soit fusionner N-01/N-02 avec un tag `place: tenths|hundredths`, soit **renommer N-02** pour que le geste supplémentaire apparaisse. **Ne pas laisser en l'état** : c'est le premier reproche qu'un didacticien externe fera au référentiel.

> ☐ **3 nœuds, on assume** — justification écrite : ______________________________________________
> ☐ **Fusionner N-01 + N-02** (1 nœud, tag de magnitude) → refonte des arêtes E-01/E-03/E-04/E-06/E-07/E-12/E-14/E-20
> ☐ **3 nœuds mais renommer N-02** pour nommer le geste (ex. `PLACE_VALUE_HUNDREDTHS_RELATION`)

---

### ❓ Arbitrage 4 — **`MULT_DECIMAL_WHOLE` n'a aucun prérequis HARD. Le diagnostic causal est mort sur cette branche.**

*Question ouverte par cette relecture. C'est, à mon sens, le défaut le plus coûteux du draft.*

**Les faits.** Sur les 14 nœuds, **13 ont au moins un parent HARD**. `MULT_DECIMAL_WHOLE` (N-12) n'en a **aucun** : son unique arête entrante est **SOFT 0,60** (E-17, depuis `MULT_DIV_POW10`).

**Pourquoi c'est grave.** Le diagnostic causal d'Atlas — *« l'élève bloque sur X **parce que** le prérequis Y n'est pas maîtrisé »*, l'argument de vente différenciant — se calcule par la **clôture amont des arêtes HARD**. Sur cette branche :

- élève échoue `MULT_DECIMAL_DECIMAL` (N-14) → HARD remonte à `MULT_DECIMAL_WHOLE` (N-12) → **et s'arrête là**, faute de HARD amont.
- élève échoue `MULT_DECIMAL_WHOLE` → **aucune cause racine à proposer**. Le produit affiche « la cause racine est : multiplier un décimal par un entier », c'est-à-dire la lacune elle-même.

**Deux nœuds sur quatorze (14 %) — dont le nœud le plus difficile du domaine — sont donc diagnostiquement muets.**

**Candidats de prérequis HARD manquants** :

| Arête candidate | Argument | Contre-argument |
|---|---|---|
| `ADD_DECIMALS` → `MULT_DECIMAL_WHOLE` (HARD ~0,72) | `2,5 × 3` **est** `2,5 + 2,5 + 2,5` — c'est le modèle mental de la multiplication par un entier | Un élève peut poser l'algorithme colonne sans passer par l'addition répétée ⇒ test E1 → OUI ⇒ SOFT |
| `PLACE_VALUE_HUNDREDTHS` → `MULT_DECIMAL_WHOLE` (HARD ~0,75) | Placer la virgule au produit exige de **compter les décimales** ⇒ valeur de position | Symétrique de E-12/E-14 (add/sub) — **cohérent avec le reste du graphe** |
| `MULT_DIV_POW10` → `MULT_DECIMAL_WHOLE` **en HARD** (0,70) au lieu de SOFT | Le décalage de virgule est le même geste | Le blocage de routing serait abusif : on peut multiplier par 3 sans savoir multiplier par 10 |

**Ma recommandation** : ajouter **`PLACE_VALUE_HUNDREDTHS → MULT_DECIMAL_WHOLE` en HARD 0,75**. C'est la seule qui passe le test E1 (« item honnête de la cible réussi malgré échec systématique de la source » → NON : sans les places, on ne place pas la virgule) **et** qui rend le graphe symétrique : les quatre opérations (`ADD`, `SUB`, `MULT`, `DIV`) auraient alors toutes le même prérequis structurel de valeur de position. *(Effet de bord : densité intra passe à 22/14 = **1,57** — toujours dans la cible [1,3–1,6].)*

> ☐ **Ajouter `PLACE_VALUE_HUNDREDTHS → MULT_DECIMAL_WHOLE` HARD 0,75** (recommandé)
> ☐ Ajouter une autre arête : ____________________________________________________
> ☐ Laisser en l'état — et **acter par écrit** que le diagnostic causal est muet sur `MULT_DECIMAL_WHOLE` / `MULT_DECIMAL_DECIMAL` (à dire aussi en démo commerciale)

---

## 5. Registre d'arbitrage — à remplir en séance de réconciliation

*Un désaccord non tranché = le nœud/l'arête **reste en `draft`**. Rien ne passe `active` sans une ligne dans ce registre.*

| Date | Objet (code nœud/arête) | Position lecteur A (didacticien) | Position lecteur B (enseignant EAU) | Arbitrage retenu | Motif |
|---|---|---|---|---|---|
| | Arbitrage 1 — médiane G4 (1620) | | | | |
| | Arbitrage 2 — racine `PLACE_VALUE_TENTHS` | | | | |
| | Arbitrage 3 — chaîne place-value (3 nœuds ?) | | | | |
| | Arbitrage 4 — `MULT_DECIMAL_WHOLE` sans HARD | | | | |
| | N-01 · `money model` sur les dixièmes | | | | |
| | N-07 · nommage + cognitif | | | | |
| | N-09 · contextes d'arrondi | | | | |
| | N-11 · `MULT_DIV_POW10` : 1 ou 2 nœuds ? cognitif ? | | | | |
| | E-13 / E-20 · HARD à 0,72 (plancher) | | | | |
| | P-03 · `EQUIVALENCE_COMPUTE → DECIMAL_AS_FRACTION` : HARD ou SOFT ? | | | | |
| | | | | | |
| | | | | | |

---

## 6. Après la revue — ce qui s'enchaîne

1. Arbitrages journalisés (§5) → corrections dans `referentiel_decimals_draft.json`.
2. **Re-validation DAG** sur le graphe combiné (`src/graph/validator.py`) — obligatoire après toute modification d'arête.
3. Recalcul des médianes et de la densité si des nœuds/arêtes ont bougé.
4. Seed idempotent en base (gate **G4** du Lot A).
5. Simulation de cohorte (gate **G5**) — ⚠️ **`scripts/simulate_cohort.py` hardcodait `referentiel_fractions.json` (errata E10)** : vérifier qu'il est paramétré **avant** de compter sur ce gate.
6. Production des items (A-5) puis version arabe (A-6) — **conditionnée aussi par le Lot 4** (décision D-A1 confirmée).

**Ce que débloque cette double signature** : le passage des 14 nœuds de `draft` à `active`, donc le démarrage de la production décimaux.

---

## Signatures

| | **Lecteur A — Didacticien** | **Lecteur B — Enseignant primaire EAU** |
|---|---|---|
| **Nom** | ____________________________ | ____________________________ |
| **Date de lecture (seul)** | ____________________ | ____________________ |
| **Nœuds validés** | ______ / 14 | ______ / 14 |
| **Arêtes validées** | ______ / 26 | ______ / 26 |
| **Verdict** | ☐ Draft validé ☐ Validé sous réserve ☐ Retour en rédaction | ☐ Draft validé ☐ Validé sous réserve ☐ Retour en rédaction |
| **Signature** | ____________________________ | ____________________________ |

| **Réconciliation** | |
|---|---|
| Date de la séance | ____________________ |
| Désaccords tranchés | ______ / ______ |
| Nœuds maintenus en `draft` | ____________________________________________ |
| **Gate A1.8** | ☐ **FRANCHI** ☐ Non franchi |

*Les priors et poids de ce référentiel sont des choix experts, non mesurés. Ils seront ré-estimés sur trafic réel (Lot C). Aucune compétence décimaux n'est calibrée ni alignée sur un curriculum tant que le crosswalk (Lot B, règle CI B6) ne l'a pas mappée.*
