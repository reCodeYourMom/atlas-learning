# Crosswalk curriculaire — Fractions (CCSS-M ↔ UK NC ↔ MoE UAE) — vue générée

> **GÉNÉRÉ — ne pas éditer.** Vue produite par `scripts/generate_crosswalk_md.py` depuis `crosswalk_fractions_draft.json` (source de vérité) ; remplacera l'authored (`Crosswalk-Curriculum-Fractions.md`) après confirmation expert (`reconciliation.expert_confirmation_pending`). Toute correction se fait dans le pivot JSON, puis régénération.

**Statut pivot** : 0.2-reconciled · **Généré depuis** : pivot du 2026-07-11 · **Périmètre** : 32 compétences
**État** : RECONCILED + décisions fondateur 2026-07-12 — B-0 (2026-07-11) : types d'alignement fixés par framework, cognitifs MoE alignés sur l'enum du référentiel, synthèse recalculée ; en attente de confirmation expert (reconciliation.expert_confirmation_pending).

**Frameworks mappés** :
- **CCSS_M** — *Common Core State Standards for Mathematics*, NGA Center / CCSSO, édition 2010. Grain : coded standards (e.g. 4.NF.A.1). Stabilité : stable, non modifié depuis 2010.
- **UK_NC** — *Mathematics programmes of study: key stages 1 and 2 — National curriculum in England*, DfE, édition 2013 (DFE-00180-2013). Grain : year-group programmes of study (Y1–Y6). Stabilité : stable depuis 2013.
- **MOE_UAE** — *UAE National Curriculum — Mathematics*, Ministry of Education (moe.gov.ae), édition courante — pas de standards codés publiés. Grain : domaine de contenu + grade-band (Cycle 1 = KG–G5) + niveau cognitif TIMSS (Knowing/Applying/Reasoning). Stabilité : à ré-auditer si publication d'outcomes par grade.

---

## Légende — types d'alignement

| Type | Sens |
|---|---|
| **EXACT** | La compétence Atlas correspond directement à un standard officiel (même geste cognitif, même attente). |
| **PARTIAL** | La compétence Atlas couvre une partie d'un standard plus large. |
| **BROADER** | Un seul standard officiel regroupe plusieurs compétences Atlas (Atlas plus fin). |
| **PREREQ** | Grain plus fin / prérequis cognitif non nommé explicitement par le standard. |
| **ENRICH** | Atlas place la compétence différemment du framework (avance de grade, ou exigence absente du standard). |

Confiance : **H** (haute — standard explicite et stable) · **M** (moyenne — mapping défendable mais à valider / divergence framework).

---

## Table de correspondance — 32 compétences

Types et confiances **par framework** (réconciliation B-0 du 2026-07-11).

| # | Code Atlas | Compétence | G | CCSS-M | Align. CCSS | UK NC (year) | Align. UK | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | `NS.EQUAL_SHARES` | Partition shapes into equal shares | 2 | 2.G.A.3, 1.G.A.3 | EXACT (H) | Y1-Y2 fractions of a shape | EXACT (H) | CCSS : 1.G.A.3 aussi |
| 2 | `NS.HALVES_QUARTERS` | Identify halves and quarters | 2 | 2.G.A.3 | EXACT (H) | Y1-Y2 half/quarter (Y1), Y2 | EXACT (H) |  |
| 3 | `NS.NAME_FRACTION_VISUAL` | Name the fraction shown by a shaded model | 2 | 2.G.A.3, 3.NF.A.1 | PARTIAL (H) | Y2-Y3 name fraction of a shaded model | PARTIAL (H) | CCSS : Pont vers 3.NF. |
| 4 | `NF.ADD_SAME_NOSIMP` | Add fractions, same denominator, no simplifying | 3 | 4.NF.B.3a | ENRICH (H) | Y3 add/subtract same denom | EXACT (H) | CCSS : CCSS introduit en G4 ; Atlas G3 (suit le grain UK). · UK : UK introduit l'addition même-dénom en Y3. |
| 5 | `NF.COMPARE_SAME_DENOM` | Compare fractions with same denominator | 3 | 3.NF.A.3d | EXACT (H) | Y3 compare same denom | EXACT (H) |  |
| 6 | `NF.COMPARE_SAME_NUM` | Compare fractions with same numerator | 3 | 3.NF.A.3d | EXACT (H) | Y3 compare unit fractions | EXACT (H) |  |
| 7 | `NF.EQUIVALENCE_VISUAL` | Recognize equivalent fractions with models | 3 | 3.NF.A.3a, 3.NF.A.3b | EXACT (H) | Y3 equivalent fractions (diagrams) | EXACT (H) |  |
| 8 | `NF.FRACTION_AS_PART` | Represent a fraction a/b of a whole | 3 | 3.NF.A.1 | EXACT (H) | Y3 non-unit fractions | EXACT (H) |  |
| 9 | `NF.FRACTION_OF_SET` | Find a fraction of a set of objects | 3 | 4.NF.B.4, 3.OA | PARTIAL (M) | Y3 fractions of a discrete set | EXACT (H) | CCSS : Pas de standard dédié G3 ; couvert plus tard via multiplication. · UK : UK : standard explicite Y3. |
| 10 | `NF.NUMBER_LINE_PLACE` | Place a fraction on a number line | 3 | 3.NF.A.2 | EXACT (H) | Y3 fractions as numbers | PARTIAL (H) | CCSS : 2a, 2b ; CCSS très number-line-centric. · UK : UK l'implique sans l'isoler. Réconcilié (R1) : UK Y3 englobe le placement sur la droite numérique dans 'fractions as numbers' sans l'isoler (note : 'UK l'implique sans l'isoler') — correspondance implicite, pas directe ⇒ PARTIAL ; l'EXACT de la ligne venait de CCSS 3.NF.A.2 explicite. |
| 11 | `NF.SUB_SAME_NOSIMP` | Subtract fractions, same denominator, no simplifying | 3 | 4.NF.B.3a | ENRICH (H) | Y3 add/subtract same denom | EXACT (H) | CCSS : Même décalage de grade que #4. |
| 12 | `NF.UNIT_FRACTION` | Understand a unit fraction 1/b | 3 | 3.NF.A.1 | EXACT (H) | Y3 unit fractions | EXACT (H) |  |
| 13 | `NF.WHOLE_AS_FRACTION` | Recognize whole numbers as fractions (b/b=1) | 3 | 3.NF.A.3c | EXACT (H) | Y3-Y5 whole numbers as fractions (implicite) | PREREQ (H) | CCSS : CCSS explicite. · UK : Décision fondateur 2026-07-12 (Q1, cohérence #30/#31) : PARTIAL → PREREQ. Descriptor UK 'implicite', b/b=1 non nommé → 'building block for'. À confirmer didacticien. |
| 14 | `NS.MULT_FACTS` | Recall multiplication facts to 100 | 3 | 3.OA.C.7 | EXACT (H) | Y4 tables up to 12x12 | EXACT (H) | UK : UK formalise la mémorisation en Y4. |
| 15 | `NF.ADD_SAME_IMPROPER` | Add fractions, same denominator, improper result | 4 | 4.NF.B.3b, 4.NF.B.3c | EXACT (H) | Y5 statements > 1 as mixed number | EXACT (H) | UK : UK : ex. 2/5+4/5=6/5=1 1/5 (Y5). |
| 16 | `NF.ADD_SAME_SIMPLIFY` | Add fractions, same denominator, simplify result | 4 | 4.NF.B.3a, 4.NF.A.1 | PARTIAL (H) | Y5-Y6 add same denom + simplify | PARTIAL (H) | CCSS : Simplification non exigée par CCSS — cf. #23. · UK : La simplification relève de Y6. |
| 17 | `NF.ADD_UNLIKE_LCM` | Add fractions, unlike denom, requiring LCM | 4 | 5.NF.A.1 | ENRICH (H) | Y6 add/subtract different denom | ENRICH (H) | CCSS : CCSS G5 ; Atlas G4 (chaîne de prérequis). · UK : UK Y6 ; Atlas G4. |
| 18 | `NF.ADD_UNLIKE_SIMPLE` | Add fractions, unlike denom, one is multiple of other | 4 | 5.NF.A.1 | ENRICH (H) | Y5 denom = multiples du même nombre | EXACT (H) | CCSS : Sous-cas. Réconcilié (R3) : 5.NF.A.1 est un standard G5 ; Atlas place la compétence en G4 — avance d'un grade (Divergence 1), même standard et même situation que #17 ⇒ ENRICH côté CCSS (le 'sous-cas' va en nuance, pas en type) ; l'EXACT de la ligne venait d'UK Y5, exactement ce cas à l'âge (G4≈Y5). · UK : UK Y5 exactement ce cas. |
| 19 | `NF.COMMON_DENOM` | Find a common denominator for two fractions | 4 | 5.NF.A.1 | ENRICH (H) | Y6 common multiples for same denomination | ENRICH (H) | CCSS : Embarqué dans 5.NF.A.1. Réconcilié (R3) : compétence embarquée dans 5.NF.A.1 (G5) ; Atlas G4 = avance d'un grade (Divergence 1), cohérent avec #17/#18 sur le même standard. · UK : Réconcilié (R2) : descriptor Y6 ('use common multiples to express fractions in the same denomination') pour un nœud Atlas G4 (âge exact = Y5) — Y6 ⇒ ENRICH, cohérent avec #17 (même situation Y6/G4). |
| 20 | `NF.COMPARE_BENCHMARK` | Compare fractions using benchmarks (1/2, 1) | 4 | 4.NF.A.2 | EXACT (H) | Y5-Y6 compare using benchmarks (implicite) | PARTIAL (H) | CCSS : CCSS nomme explicitement le benchmark 1/2. · UK : Réconcilié (R1) : descriptor marqué 'implicite' — UK NC n'exige pas la stratégie benchmark que CCSS 4.NF.A.2 nomme ; la compétence couvre une partie des objectifs 'compare and order' Y5–Y6 ⇒ PARTIAL. |
| 21 | `NF.COMPARE_DIFF_DENOM` | Compare fractions with different denominators | 4 | 4.NF.A.2 | EXACT (H) | Y5-Y6 Y5 (multiples) / Y6 (incl. >1) | PARTIAL (H) | UK : Réconcilié (R2) : couverture répartie — Y5 ne couvre que le cas 'dénominateurs multiples du même nombre' (à l'âge, G4≈Y5) ; la généralisation (incl. fractions > 1) relève de Y6 ⇒ couverture partielle à l'âge, PARTIAL. |
| 22 | `NF.EQUIVALENCE_COMPUTE` | Generate equivalent fractions by multiplication | 4 | 4.NF.A.1 | EXACT (H) | Y4-Y5 Y4 families / Y5 write equivalents | EXACT (H) |  |
| 23 | `NF.SIMPLIFY_FRACTION` | Simplify a fraction to lowest terms | 4 | 6.NS.B.4 | ENRICH (M) | Y6 use common factors to simplify | EXACT (H) | CCSS : CCSS n'exige pas la réduction ; factorisation commune formalisée en G6. Cf. §Divergences 2. · UK : Exigence Y6 explicite. |
| 24 | `NF.SUB_SAME_SIMPLIFY` | Subtract fractions, same denominator, simplify result | 4 | 4.NF.B.3a, 4.NF.A.1 | PARTIAL (H) | Y5-Y6 subtract same denom + simplify | PARTIAL (H) | CCSS : Idem #16. |
| 25 | `NS.FACTORS` | Find factors of a number | 4 | 4.OA.B.4 | EXACT (H) | Y5 multiples & factors, factor pairs | EXACT (H) |  |
| 26 | `NS.GCD` | Find greatest common divisor | 4 | 6.NS.B.4 | ENRICH (H) | Y5-Y6 Y5 common factors / Y6 simplify | EXACT (H) | CCSS : CCSS formalise le PGCD en G6 ; Atlas G4 (prérequis de simplification). · UK : À réconcilier : Y5 common factors ≈ G4 (équivalence d'âge UK Year = Grade+1). Réconcilié (R2, levée du flag 'À réconcilier' de la note) : Y5 'common factors of two numbers' est à l'âge du nœud Atlas G4 (Year≈Grade+1) — l'ENRICH de la ligne venait du côté CCSS (PGCD formalisé G6) ⇒ EXACT côté UK. |
| 27 | `NS.LCM` | Find least common multiple | 4 | 6.NS.B.4 | ENRICH (H) | Y6 common multiples | ENRICH (H) | CCSS : CCSS formalise le PPCM en G6 ; Atlas G4 (prérequis dénom. commun). |
| 28 | `NF.ADD_MIXED` | Add mixed numbers | 5 | 4.NF.B.3c, 5.NF.A.1 | EXACT (H) | Y6 add mixed numbers | EXACT (H) | CCSS : 4.NF.B.3c (like) / 5.NF.A.1 (unlike). |
| 29 | `NF.ADD_UNLIKE_FULL` | Add fractions, unlike denom, with simplify + improper | 5 | 5.NF.A.1 | EXACT (H) | Y6 add/subtract different denom & mixed | EXACT (H) |  |
| 30 | `NF.IMPROPER_TO_MIXED` | Convert improper fraction to mixed number | 5 | 4.NF.B.3b | PREREQ (H) | Y5 convert one form to the other | EXACT (H) | CCSS : Implicite. Décision fondateur 2026-07-12 (Q1) : PARTIAL → PREREQ. CCSS ne nomme jamais la conversion (implicite dans 4.NF.B.3b/c) → 'building block for', plus défendable que 'covers part of'. À confirmer didacticien. · UK : UK Y5 explicite. |
| 31 | `NF.MIXED_TO_IMPROPER` | Convert mixed number to improper fraction | 5 | 4.NF.B.3c, 5.NF.A.1 | PREREQ (H) | Y5 convert one form to the other | EXACT (H) | CCSS : Implicite. Décision fondateur 2026-07-12 (Q1) : PARTIAL → PREREQ. CCSS ne nomme jamais la conversion (implicite dans 4.NF.B.3b/c) → 'building block for', plus défendable que 'covers part of'. À confirmer didacticien. · UK : UK Y5 explicite. |
| 32 | `NF.SUB_UNLIKE_LCM` | Subtract fractions, unlike denom, requiring LCM | 5 | 5.NF.A.1 | EXACT (H) | Y6 add/subtract different denom | EXACT (H) |  |

---

## Synthèse de couverture (calculée depuis les lignes — jamais saisie)

| Framework | Compétences couvertes | EXACT | PARTIAL | BROADER | PREREQ | ENRICH |
|---|---|---|---|---|---|---|
| **CCSS_M** | 32 / 32 | 18 | 4 | 0 | 2 | 8 |
| **UK_NC** | 32 / 32 | 22 | 6 | 0 | 1 | 3 |
| **MOE_UAE** | 32 / 32 | grain domaine + grade-band (pas de types — cognitif : Applying 18 · Knowing 2 · Reasoning 12) | | | | |

---

## MoE UAE — mapping par domaine + grade-band + niveau cognitif

Le framework MoE **ne publie pas de standards codés** : le mapping se fait au grain réel `domaine → sous-strand → grade-band → niveau cognitif` (clé composée en base, ex. `NUM_OPS.G4-G5` — jamais un pseudo-code inventé). Le niveau cognitif est aligné 1:1 sur l'enum `CognitiveLevel` d'Atlas (RECALL→Knowing, APPLY→Applying, REASON→Reasoning) ; les propositions originales divergentes sont conservées en « authored » pour audit.

| # | Code Atlas | Domaine MoE | Sous-strand | Grade-band (Cycle 1) | Niveau cognitif | Conf. | Cognitif authored |
|---|---|---|---|---|---|---|---|
| 1 | `NS.EQUAL_SHARES` | Numbers & Operations | Fractions (parts égales) | G2 | Applying | H/M | Knowing |
| 2 | `NS.HALVES_QUARTERS` | Numbers & Operations | Fractions | G2 | Knowing | H/M | — |
| 3 | `NS.NAME_FRACTION_VISUAL` | Numbers & Operations | Fractions | G2-G3 | Applying | H/M | Knowing |
| 4 | `NF.ADD_SAME_NOSIMP` | Numbers & Operations | Fractions (opérations) | G3-G4 | Applying | H/M | — |
| 5 | `NF.COMPARE_SAME_DENOM` | Numbers & Operations | Fractions (comparaison) | G3 | Applying | H/M | — |
| 6 | `NF.COMPARE_SAME_NUM` | Numbers & Operations | Fractions (comparaison) | G3 | Reasoning | H/M | — |
| 7 | `NF.EQUIVALENCE_VISUAL` | Numbers & Operations | Fractions (équivalence) | G3 | Reasoning | H/M | Knowing |
| 8 | `NF.FRACTION_AS_PART` | Numbers & Operations | Fractions | G3 | Applying | H/M | Knowing |
| 9 | `NF.FRACTION_OF_SET` | Numbers & Operations | Fractions | G3-G4 | Applying | H/M | — |
| 10 | `NF.NUMBER_LINE_PLACE` | Numbers & Operations | Fractions (représentation) | G3 | Applying | H/M | — |
| 11 | `NF.SUB_SAME_NOSIMP` | Numbers & Operations | Fractions (opérations) | G3-G4 | Applying | H/M | — |
| 12 | `NF.UNIT_FRACTION` | Numbers & Operations | Fractions | G3 | Reasoning | H/M | Knowing |
| 13 | `NF.WHOLE_AS_FRACTION` | Numbers & Operations | Fractions | G3 | Reasoning | H/M | Knowing |
| 14 | `NS.MULT_FACTS` | Numbers & Operations | Opérations (faits) | G3 | Knowing | H/M | — |
| 15 | `NF.ADD_SAME_IMPROPER` | Numbers & Operations | Fractions (opérations) | G4 | Reasoning | H/M | Applying |
| 16 | `NF.ADD_SAME_SIMPLIFY` | Numbers & Operations | Fractions (opérations) | G4-G5 | Applying | H/M | — |
| 17 | `NF.ADD_UNLIKE_LCM` | Numbers & Operations | Fractions (opérations) | G5 | Reasoning | H/M | Applying |
| 18 | `NF.ADD_UNLIKE_SIMPLE` | Numbers & Operations | Fractions (opérations) | G4-G5 | Reasoning | H/M | Applying |
| 19 | `NF.COMMON_DENOM` | Numbers & Operations | Fractions (opérations) | G5 | Applying | H/M | — |
| 20 | `NF.COMPARE_BENCHMARK` | Numbers & Operations | Fractions (comparaison) | G4 | Reasoning | H/M | — |
| 21 | `NF.COMPARE_DIFF_DENOM` | Numbers & Operations | Fractions (comparaison) | G4 | Reasoning | H/M | — |
| 22 | `NF.EQUIVALENCE_COMPUTE` | Numbers & Operations | Fractions (équivalence) | G4 | Applying | H/M | — |
| 23 | `NF.SIMPLIFY_FRACTION` | Numbers & Operations | Fractions (équivalence) | G5 | Applying | H/M | — |
| 24 | `NF.SUB_SAME_SIMPLIFY` | Numbers & Operations | Fractions (opérations) | G4-G5 | Applying | H/M | — |
| 25 | `NS.FACTORS` | Numbers & Operations | Théorie des nombres | G4 | Applying | H/M | Knowing |
| 26 | `NS.GCD` | Numbers & Operations | Théorie des nombres | G5 | Applying | H/M | — |
| 27 | `NS.LCM` | Numbers & Operations | Théorie des nombres | G5 | Applying | H/M | — |
| 28 | `NF.ADD_MIXED` | Numbers & Operations | Fractions (opérations) | G5 | Reasoning | H/M | Applying |
| 29 | `NF.ADD_UNLIKE_FULL` | Numbers & Operations | Fractions (opérations) | G5 | Reasoning | H/M | — |
| 30 | `NF.IMPROPER_TO_MIXED` | Numbers & Operations | Fractions (formes) | G5 | Applying | H/M | — |
| 31 | `NF.MIXED_TO_IMPROPER` | Numbers & Operations | Fractions (formes) | G5 | Applying | H/M | — |
| 32 | `NF.SUB_UNLIKE_LCM` | Numbers & Operations | Fractions (opérations) | G5 | Reasoning | H/M | Applying |

> **Légende confiance** : `H/M` = domaine (H, certain) / grade-band (M, estimé — fiabilisation B7 en attente du document d'outcomes par grade du MoE).

---

## Provenance

- **Source** : `data/crosswalk_fractions_draft.json` (pivot 0.2-reconciled, généré le 2026-07-11) — lui-même issu de Crosswalk-Curriculum-Fractions.md v1 (2026-06-23).
- **weight_source** : `expert` (crosswalk auteur, citant les frameworks publiés).
- **Validation** : 0 erreur au validateur CI B6 (`scripts/validate_crosswalk.py`).
