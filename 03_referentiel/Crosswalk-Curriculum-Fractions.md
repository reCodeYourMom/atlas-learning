# Crosswalk curriculaire — Fractions (CCSS-M ↔ UK National Curriculum)

**Statut** : v1 · **Date** : 2026-06-23 · **Périmètre** : référentiel Fractions (32 compétences, G2–G5)
**Frameworks mappés** :
- **CCSS-M** — *Common Core State Standards for Mathematics*, NGA Center / CCSSO, 2010. Domaines `NF` (Number & Operations—Fractions), `OA` (Operations & Algebraic Thinking), `NS` (Number System), `G` (Geometry).
- **UK NC** — *Mathematics programmes of study: key stages 1 and 2 — National curriculum in England*, DfE, réf. DFE-00180-2013. Repère par **year group** (Y1–Y6).
- **MoE UAE** — *UAE National Curriculum — Mathematics*, Ministry of Education (moe.gov.ae). **N'utilise pas de standards codés** : structure par **domaines de contenu** (Numbers & Operations · Algebra & Patterns · Geometry & Measurement · Data Analysis & Probabilities) + 5 skill strands, par **cycle/grade-band** (Cycle 1 = KG–G5), avec niveaux cognitifs **TIMSS** (Knowing / Applying / Reasoning). Repère = domaine + grade-band + niveau cognitif (voir §MoE).

> **Nature de ce document.** Crosswalk d'expert, citant les frameworks officiels publiés. Ce n'est **pas** une certification ni un endossement par un éditeur de curriculum ou un régulateur (KHDA/ADEK/MoE). Chaque correspondance porte un **type d'alignement** et un **niveau de confiance** explicites. La couche moteur d'Atlas ne dépend d'aucun curriculum ; ce mapping est une **étiquette projetée** par-dessus le référentiel neutre (cf. DataModel §7).

---

## Légende — types d'alignement

| Type | Sens |
|---|---|
| **EXACT** | La compétence Atlas correspond directement à un standard officiel (même geste cognitif, même attente). |
| **PARTIAL** | La compétence Atlas couvre **une partie** d'un standard plus large. |
| **BROADER** | Un seul standard officiel **regroupe plusieurs** compétences Atlas (Atlas est plus fin → meilleure granularité de mesure). |
| **PREREQ** | Grain plus fin / prérequis cognitif non nommé explicitement par le standard, mais nécessaire pour l'atteindre. |
| **ENRICH** | Atlas place la compétence différemment du framework (avance de grade, ou exigence absente du standard). Voir notes. |

Confiance : **H** (haute — standard explicite et stable) · **M** (moyenne — mapping défendable mais à valider / divergence framework).

---

## Table de correspondance — 32 compétences

| # | Code Atlas | Compétence | G | CCSS-M | UK NC (year) | Type | Conf. | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | `NS.EQUAL_SHARES` | Partition shapes into equal shares | 2 | 2.G.A.3 (aussi 1.G.A.3) | Y1–Y2 fractions of a shape | EXACT | H | |
| 2 | `NS.HALVES_QUARTERS` | Identify halves and quarters | 2 | 2.G.A.3 | Y1 (half/quarter), Y2 | EXACT | H | |
| 3 | `NS.NAME_FRACTION_VISUAL` | Name the fraction of a shaded model | 2 | 2.G.A.3 → 3.NF.A.1 | Y2–Y3 | PARTIAL | H | Pont vers 3.NF. |
| 4 | `NF.ADD_SAME_NOSIMP` | Add fractions, same denom, no simplify | 3 | 4.NF.B.3a | **Y3** add/subtract same denom | ENRICH | H | UK introduit l'addition même-dénom en Y3 ; CCSS en G4. Atlas suit le grain UK. |
| 5 | `NF.COMPARE_SAME_DENOM` | Compare fractions, same denom | 3 | 3.NF.A.3d | Y3 compare same denom | EXACT | H | |
| 6 | `NF.COMPARE_SAME_NUM` | Compare fractions, same numerator | 3 | 3.NF.A.3d | Y3 compare unit fractions | EXACT | H | |
| 7 | `NF.EQUIVALENCE_VISUAL` | Recognise equivalent fractions (models) | 3 | 3.NF.A.3a / 3.NF.A.3b | Y3 equivalent fractions (diagrams) | EXACT | H | |
| 8 | `NF.FRACTION_AS_PART` | Represent a/b of a whole | 3 | 3.NF.A.1 | Y3 non-unit fractions | EXACT | H | |
| 9 | `NF.FRACTION_OF_SET` | Find a fraction of a set | 3 | 4.NF.B.4 (via mult.) / 3.OA | **Y3** fractions of a discrete set | PARTIAL | M | UK : standard explicite Y3. CCSS : pas de standard dédié G3 ; couvert plus tard via multiplication. |
| 10 | `NF.NUMBER_LINE_PLACE` | Place a fraction on a number line | 3 | 3.NF.A.2 (2a, 2b) | Y3 fractions as numbers | EXACT | H | CCSS très number-line-centric ; UK l'implique sans l'isoler. |
| 11 | `NF.SUB_SAME_NOSIMP` | Subtract fractions, same denom, no simplify | 3 | 4.NF.B.3a | Y3 add/subtract same denom | ENRICH | H | Même décalage de grade que #4. |
| 12 | `NF.UNIT_FRACTION` | Understand a unit fraction 1/b | 3 | 3.NF.A.1 | Y3 unit fractions | EXACT | H | |
| 13 | `NF.WHOLE_AS_FRACTION` | Whole numbers as fractions (b/b=1) | 3 | 3.NF.A.3c | Y3–Y5 (implicite) | EXACT | H | CCSS explicite (3.NF.A.3c). |
| 14 | `NS.MULT_FACTS` | Recall multiplication facts to 100 | 3 | 3.OA.C.7 | Y4 tables up to 12×12 | EXACT | H | UK formalise la mémorisation en Y4. |
| 15 | `NF.ADD_SAME_IMPROPER` | Add same denom, improper result | 4 | 4.NF.B.3b / 4.NF.B.3c | **Y5** statements > 1 as mixed number | EXACT | H | UK : ex. 2/5+4/5=6/5=1⅕ (Y5). |
| 16 | `NF.ADD_SAME_SIMPLIFY` | Add same denom, simplify result | 4 | 4.NF.B.3a (+ 4.NF.A.1) | Y5–Y6 | PARTIAL | H | La simplification relève de Y6 (UK) / non exigée par CCSS — cf. #23. |
| 17 | `NF.ADD_UNLIKE_LCM` | Add unlike denom, requiring LCM | 4 | 5.NF.A.1 | **Y6** add/subtract different denom | ENRICH | H | CCSS G5 / UK Y6 ; Atlas place en G4 (chaîne de prérequis). |
| 18 | `NF.ADD_UNLIKE_SIMPLE` | Add unlike, one denom multiple of other | 4 | 5.NF.A.1 (sous-cas) | **Y5** denom = multiples du même nombre | EXACT | H | UK Y5 exactement ce cas. |
| 19 | `NF.COMMON_DENOM` | Find a common denominator | 4 | 5.NF.A.1 (embarqué) | **Y6** common multiples for same denomination | EXACT | H | |
| 20 | `NF.COMPARE_BENCHMARK` | Compare using benchmarks (½, 1) | 4 | 4.NF.A.2 (benchmark fraction) | Y5–Y6 (implicite) | EXACT | H | CCSS nomme explicitement le benchmark ½. |
| 21 | `NF.COMPARE_DIFF_DENOM` | Compare different denominators | 4 | 4.NF.A.2 | Y5 (multiples) / Y6 (incl. >1) | EXACT | H | |
| 22 | `NF.EQUIVALENCE_COMPUTE` | Generate equivalent fractions (×) | 4 | 4.NF.A.1 | Y4 families / Y5 write equivalents | EXACT | H | |
| 23 | `NF.SIMPLIFY_FRACTION` | Simplify to lowest terms | 4 | (6.NS.B.4) | **Y6** use common factors to simplify | ENRICH | M | **CCSS n'exige pas la réduction** ; factorisation commune formalisée en G6. UK : exigence Y6 explicite. Voir §Divergences. |
| 24 | `NF.SUB_SAME_SIMPLIFY` | Subtract same denom, simplify | 4 | 4.NF.B.3a (+ 4.NF.A.1) | Y5–Y6 | PARTIAL | H | Idem #16. |
| 25 | `NS.FACTORS` | Find factors of a number | 4 | 4.OA.B.4 | Y5 multiples & factors, factor pairs | EXACT | H | |
| 26 | `NS.GCD` | Greatest common divisor | 4 | 6.NS.B.4 | Y5 common factors / Y6 simplify | ENRICH | H | CCSS formalise le PGCD en **G6** ; Atlas l'introduit en G4 comme prérequis de simplification. |
| 27 | `NS.LCM` | Least common multiple | 4 | 6.NS.B.4 | Y6 common multiples | ENRICH | H | CCSS formalise le PPCM en **G6** ; Atlas en G4 (prérequis dénom. commun). |
| 28 | `NF.ADD_MIXED` | Add mixed numbers | 5 | 4.NF.B.3c (like) / 5.NF.A.1 (unlike) | Y6 add mixed numbers | EXACT | H | |
| 29 | `NF.ADD_UNLIKE_FULL` | Add unlike, simplify + improper | 5 | 5.NF.A.1 | Y6 add/subtract different denom & mixed | EXACT | H | |
| 30 | `NF.IMPROPER_TO_MIXED` | Convert improper → mixed | 5 | 4.NF.B.3b (implicite) | **Y5** convert one form to the other | EXACT | H | UK Y5 explicite. |
| 31 | `NF.MIXED_TO_IMPROPER` | Convert mixed → improper | 5 | 4.NF.B.3c / 5.NF.A.1 (impl.) | **Y5** convert one form to the other | EXACT | H | UK Y5 explicite. |
| 32 | `NF.SUB_UNLIKE_LCM` | Subtract unlike denom, requiring LCM | 5 | 5.NF.A.1 | Y6 add/subtract different denom | EXACT | H | |

---

## Synthèse de couverture

| Framework | Compétences couvertes | EXACT | PARTIAL | ENRICH | Arc curriculaire couvert |
|---|---|---|---|---|---|
| **CCSS-M** | 32 / 32 | 22 | 5 | 5 | Partitioning (G1-2) → unlike-denominator + mixed numbers (G5) |
| **UK NC** | 32 / 32 | 24 | 2 | 4 | Y1 fractions of a shape → Y6 different-denominator & mixed numbers |
| **MoE UAE** | 32 / 32 | domaine *Numbers & Operations* (grain domaine + grade-band, pas de codes) | — | — | Cycle 1 (KG–G5), arc fractions complet |

**Lecture** : le référentiel Fractions couvre **l'intégralité de l'arc fractions du primaire** pour les trois frameworks, de la partition initiale jusqu'à l'arithmétique à dénominateurs différents avec nombres mixtes. Aucune compétence orpheline. CCSS-M et UK NC sont mappés au **code** ; MoE UAE au **domaine + grade-band + niveau cognitif** (le framework MoE n'expose pas de codes — cf. §MoE).

---

## Divergences notables (à connaître en RDV — ce sont des arguments, pas des faiblesses)

### 1. Le graphe Atlas est ordonné par **prérequis cognitifs**, pas par grade
Plusieurs compétences sont placées à un grade différent de celui d'un framework donné (ex. PGCD/PPCM en G4 chez Atlas, mais formellement G6 en CCSS ; addition à dénominateurs différents en G4 chez Atlas, G5/Y6 dans les frameworks). **C'est intentionnel** : Atlas mesure la *chaîne de dépendances cognitives*, puis la **couche de restitution ré-étiquette au grade de l'école**. Atlas ne remplace pas le découpage par grade de l'école — il **se projette dessus**.

### 2. CCSS n'exige pas la réduction des fractions ; UK Y6 oui
CCSS-M ne demande **pas** explicitement de réduire à la forme irréductible (un résultat non simplifié est correct). UK NC l'exige en Year 6 (« use common factors to simplify fractions »). La compétence `NF.SIMPLIFY_FRACTION` est donc :
- **EXACT** vis-à-vis d'UK Y6,
- **ENRICH** (au-delà du standard) vis-à-vis de CCSS.

Atlas mesure la compétence dans les deux cas ; la restitution peut l'afficher comme « cœur de programme » (UK) ou « enrichissement » (US) selon le curriculum de l'école.

### 3. « Fraction d'un ensemble » : explicite côté UK, indirect côté CCSS
`NF.FRACTION_OF_SET` est un standard Y3 explicite en UK NC, mais CCSS ne le traite pas comme un standard G3 dédié (il émerge plus tard via la multiplication d'une fraction par un entier). Mapping marqué PARTIAL / confiance M côté CCSS.

---

## MoE UAE — mapping par domaine + grade-band + niveau cognitif

### Note méthodologique (à lire avant la table)
Le curriculum maths du MoE UAE **ne publie pas de standards codés** comparables à CCSS-M (`4.NF.A.1`) ou aux objectifs annuels d'UK NC. Source officielle ([moe.gov.ae](https://www.moe.gov.ae/En/ImportantLinks/Pages/CurriculumFrameworks.aspx), guide de licence enseignant, encyclopédie TIMSS UAE) : le framework est organisé par **domaine de contenu**, **cycle/grade-band**, et **niveau cognitif TIMSS** (Knowing / Applying / Reasoning). Toutes les compétences fractions/théorie des nombres relèvent du domaine **Numbers & Operations**.

**Conséquence honnête** : on ne peut pas produire de « code MoE » par compétence — il n'en existe pas. Le mapping ci-dessous se fait au grain réel du framework : `domaine → sous-strand → grade-band → niveau cognitif`. Affirmer un code MoE serait faux et détruirait la crédibilité en due diligence.

**Pont utile** : le niveau cognitif MoE (Knowing/Applying/Reasoning) correspond 1:1 à l'enum `CognitiveLevel` d'Atlas (RECALL/APPLY/REASON) — l'étiquetage MoE est donc déjà à moitié natif dans le modèle de données.

Confiance : **domaine** = H (placement Numbers & Operations non ambigu) · **grade-band** = M (le document d'outcomes par grade n'est pas publié sous forme exploitable ; placement Cycle 1 estimé sur l'arc officiel).

### Table MoE

| # | Code Atlas | Domaine MoE | Sous-strand | Grade-band (Cycle 1) | Niveau cognitif | Conf. |
|---|---|---|---|---|---|---|
| 1 | `NS.EQUAL_SHARES` | Numbers & Operations | Fractions (parts égales) | G2 | Knowing | H/M |
| 2 | `NS.HALVES_QUARTERS` | Numbers & Operations | Fractions | G2 | Knowing | H/M |
| 3 | `NS.NAME_FRACTION_VISUAL` | Numbers & Operations | Fractions | G2–G3 | Knowing | H/M |
| 4 | `NF.ADD_SAME_NOSIMP` | Numbers & Operations | Fractions (opérations) | G3–G4 | Applying | H/M |
| 5 | `NF.COMPARE_SAME_DENOM` | Numbers & Operations | Fractions (comparaison) | G3 | Applying | H/M |
| 6 | `NF.COMPARE_SAME_NUM` | Numbers & Operations | Fractions (comparaison) | G3 | Reasoning | H/M |
| 7 | `NF.EQUIVALENCE_VISUAL` | Numbers & Operations | Fractions (équivalence) | G3 | Knowing | H/M |
| 8 | `NF.FRACTION_AS_PART` | Numbers & Operations | Fractions | G3 | Knowing | H/M |
| 9 | `NF.FRACTION_OF_SET` | Numbers & Operations | Fractions | G3–G4 | Applying | H/M |
| 10 | `NF.NUMBER_LINE_PLACE` | Numbers & Operations | Fractions (représentation) | G3 | Applying | H/M |
| 11 | `NF.SUB_SAME_NOSIMP` | Numbers & Operations | Fractions (opérations) | G3–G4 | Applying | H/M |
| 12 | `NF.UNIT_FRACTION` | Numbers & Operations | Fractions | G3 | Knowing | H/M |
| 13 | `NF.WHOLE_AS_FRACTION` | Numbers & Operations | Fractions | G3 | Knowing | H/M |
| 14 | `NS.MULT_FACTS` | Numbers & Operations | Opérations (faits) | G3 | Knowing | H/M |
| 15 | `NF.ADD_SAME_IMPROPER` | Numbers & Operations | Fractions (opérations) | G4 | Applying | H/M |
| 16 | `NF.ADD_SAME_SIMPLIFY` | Numbers & Operations | Fractions (opérations) | G4–G5 | Applying | H/M |
| 17 | `NF.ADD_UNLIKE_LCM` | Numbers & Operations | Fractions (opérations) | G5 | Applying | H/M |
| 18 | `NF.ADD_UNLIKE_SIMPLE` | Numbers & Operations | Fractions (opérations) | G4–G5 | Applying | H/M |
| 19 | `NF.COMMON_DENOM` | Numbers & Operations | Fractions (opérations) | G5 | Applying | H/M |
| 20 | `NF.COMPARE_BENCHMARK` | Numbers & Operations | Fractions (comparaison) | G4 | Reasoning | H/M |
| 21 | `NF.COMPARE_DIFF_DENOM` | Numbers & Operations | Fractions (comparaison) | G4 | Reasoning | H/M |
| 22 | `NF.EQUIVALENCE_COMPUTE` | Numbers & Operations | Fractions (équivalence) | G4 | Applying | H/M |
| 23 | `NF.SIMPLIFY_FRACTION` | Numbers & Operations | Fractions (équivalence) | G5 | Applying | H/M |
| 24 | `NF.SUB_SAME_SIMPLIFY` | Numbers & Operations | Fractions (opérations) | G4–G5 | Applying | H/M |
| 25 | `NS.FACTORS` | Numbers & Operations | Théorie des nombres | G4 | Knowing | H/M |
| 26 | `NS.GCD` | Numbers & Operations | Théorie des nombres | G5 | Applying | H/M |
| 27 | `NS.LCM` | Numbers & Operations | Théorie des nombres | G5 | Applying | H/M |
| 28 | `NF.ADD_MIXED` | Numbers & Operations | Fractions (opérations) | G5 | Applying | H/M |
| 29 | `NF.ADD_UNLIKE_FULL` | Numbers & Operations | Fractions (opérations) | G5 | Reasoning | H/M |
| 30 | `NF.IMPROPER_TO_MIXED` | Numbers & Operations | Fractions (formes) | G5 | Applying | H/M |
| 31 | `NF.MIXED_TO_IMPROPER` | Numbers & Operations | Fractions (formes) | G5 | Applying | H/M |
| 32 | `NF.SUB_UNLIKE_LCM` | Numbers & Operations | Fractions (opérations) | G5 | Applying | H/M |

> **Légende confiance** : `H/M` = domaine (H, certain) / grade-band (M, estimé). Le niveau cognitif est **indicatif** (proposé selon le geste, alignable sur l'enum `CognitiveLevel` d'Atlas).

---

## Provenance & versionnement

- **weight_source du mapping** : `expert` (crosswalk auteur, citant les frameworks publiés). Aucune ré-estimation empirique sur ce mapping (contrairement aux poids d'arêtes du graphe).
- **Frameworks** : CCSS-M 2010 (stable, non modifié depuis) · UK NC DfE 2013 (stable) · MoE UAE — *UAE National Curriculum Mathematics* (moe.gov.ae), grain domaine/grade-band/cognitif, **pas de codes publiés**.
- **À vérifier (MoE)** : le placement par grade-band est estimé (M). Si tu obtiens le document d'outcomes par grade du MoE (via une école pilote ou le coordinateur curriculum), affiner les grade-bands et confirmer les niveaux cognitifs. Le domaine *Numbers & Operations* est certain.
- **Maintenance** : à ré-auditer si un framework publie une révision, ou à l'ajout d'un nouveau curriculum (CBSE — non couvert en v1).
- **Données structurées** : ce crosswalk alimentera les tables `curriculum_standard` + `competency_curriculum_map` (DataModel §7) lors de l'implémentation DB.
