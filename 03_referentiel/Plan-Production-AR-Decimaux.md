# Plan de production arabe — Décimaux (G4–G5)

**Livrable** : A6 (Cadrage Lot A §3/A6) · **Version** : v0.2 DRAFT · **Date** : 2026-07-12
**Statut** : à valider par la linguiste native AR avant le démarrage de la production A-6.
**À lire avec** : `01_strategie/Cadrage-LotA-Extension-Contenu.md` (§3/A6, errata E7–E8), `03_referentiel/referentiel_decimals_draft.json` (A3), `03_referentiel/referentiel_fractions.json` (terminologie existante), `04_code/src/items/arabic.py`, `04_code/src/items/review.py`, `04_code/scripts/check_ar_fidelity.py`, `04_code/scripts/translate_bank_ar.py`.

---

## 1. Objet et périmètre

Ce plan cadre la production et la validation de la version arabe (MSA) des ~140 items décimaux, en parité stricte avec l'anglais (contrainte transverse du Lot A : bilingue EN/AR à parité, gate G3 bloquant). Il fixe :

1. la **convention de notation** (chiffres et séparateur décimal) — formalisée, pas re-débattue (errata E7) ;
2. le **glossaire MSA décimaux** (terme canonique unique par concept, aligné usage scolaire EAU/MoE et sur les `label_ar` existants) ;
3. le **guide de style** (registre, RTL/LTR) ;
4. la **charge de validation chiffrée** ;
5. les **critères de fidélité** (gate G3, y compris détection de tokens latins — errata E8) ;
6. le **workflow linguiste** adossé à la machine à états de `src/items/review.py`.

**Hors périmètre** : la traduction de l'UI produit (chrome), le mapping curriculaire (Lot B), la calibration des items (Lot C).

---

## 2. Convention de notation — FORMALISÉE (errata E7)

> **Décision (constat de banque, pas un débat) : dans tout `content_ar` (stem, options, answer), les nombres s'écrivent en chiffres occidentaux 0–9 et le séparateur décimal est le point « . » (U+002E).**

C'est la convention **constatée dans la banque fractions existante** (300 items AR actifs). On la formalise pour les décimaux — où elle devient critique, puisque le séparateur décimal apparaît dans quasiment chaque item.

Conséquences normatives :

| Règle | Prescrit | Proscrit |
|---|---|---|
| Chiffres | `0 1 2 3 4 5 6 7 8 9` | chiffres arabes orientaux `٠١٢٣٤٥٦٧٨٩` dans toute nouvelle production |
| Séparateur décimal | `.` (point, U+002E) | `٫` (séparateur décimal arabe U+066B), `,` (virgule) |
| Terme désignant le séparateur | **النقطة العشرية** (« le point décimal ») | **الفاصلة العشرية** (« la virgule décimale ») — voir glossaire §3.1 |
| Écriture d'une expression | `2.5 + 0.35` identique à l'EN, symboles `× ÷ + − = < >` inchangés | traduction/translittération des symboles |

**Arbitrage الفاصلة العشرية vs النقطة العشرية — tranché pour le point.** Les manuels MoE (traductions arabes de curricula US) emploient majoritairement الفاصلة العشرية avec le séparateur ٫, mais **notre banque écrit le point** : nommer « virgule » un signe rendu « . » à l'écran créerait une dissonance énoncé/notation pour l'élève. On retient donc النقطة العشرية, cohérent avec la notation servie. La linguiste documente ce choix dans son guide de validation ; الفاصلة العشرية est acceptée en compréhension (l'élève peut la connaître) mais **interdite dans les stems**.

**Note d'audit — labels de nœuds fractions.** Deux `label_ar` du référentiel fractions contiennent des chiffres orientaux (`١/ب` dans `MATH.G3.NF.UNIT_FRACTION`, `١٠٠` dans `MATH.G3.NS.MULT_FACTS`). Ce sont des métadonnées de nœuds, pas du contenu servi : non bloquant, mais à harmoniser à l'occasion (tâche cosmétique, hors chemin critique). Les `label_ar` du draft décimaux ne contiennent aucun chiffre : conformes.

**Note outillage.** `ar_math_preserved()` (`src/items/arabic.py`) **normalise** les chiffres orientaux vers 0–9 avant comparaison : le check de fidélité math (F1) ne détecte donc **pas** une dérive de jeu de chiffres. Le lint de tokens latins (F2, **implémenté** — `ar_latin_tokens()`) ne la détecte pas non plus (les chiffres orientaux ne sont pas des lettres latines). La détection `[٠-٩]` relève du lint lexical de proscription (§6, F3) — **reste à outiller**.

---

## 3. Glossaire MSA décimaux

Principes : **un concept = un terme canonique** (pas de synonymes dans les items) ; registre scolaire MSA (فصحى) ; continuité stricte avec les `label_ar` fractions (`referentiel_fractions.json`) et décimaux (`referentiel_decimals_draft.json`), qui sont la source d'autorité en cas de doute. Translittération simplifiée (DIN allégé).

### 3.1 Nombres, structure décimale et valeur de position

| Terme EN | Terme AR canonique | Translittération | Note d'usage EAU/MoE |
|---|---|---|---|
| decimal number | عدد عشري | ʿadad ʿasharī | Conforme draft (`جمع الأعداد العشرية`…). Pluriel : أعداد عشرية. |
| decimal point | **النقطة العشرية** | an-nuqṭa al-ʿashariyya | **Tranché §2.** الفاصلة العشرية (al-fāṣila al-ʿashariyya) = variante MoE fréquente, **proscrite dans les stems** (cohérence avec la notation « . » de la banque). |
| decimal places | المنازل العشرية | al-manāzil al-ʿashariyya | « nombre de décimales » = عدد المنازل العشرية. |
| place value | القيمة المكانية | al-qīma al-makāniyya | Standard MoE. |
| place (position) | منزلة | manzila | Conforme draft (`منزلة الأعشار`…). |
| adjacent places | المنازل المتجاورة | al-manāzil al-mutajāwira | Conforme draft (relation ×10 entre منازل, G5 `PLACE_VALUE_THOUSANDTHS`). |
| tenths | الأعشار | al-aʿshār | Conforme draft (`منزلة الأعشار`). Singulier : عُشر (ʿushr) = un dixième ; forme fractionnaire : جزء من عشرة. |
| hundredths | أجزاء المئة | ajzāʾ al-miʾa | **Forme canonique = celle du draft** (`منزلة أجزاء المئة`). La variante MoE أجزاء من مئة (citée au cadrage §3/A6) est un synonyme accepté en prose, pas dans les labels/stems. Singulier : جزء من مئة. |
| thousandths | أجزاء الألف | ajzāʾ al-alf | Idem : forme du draft (`منزلة أجزاء الألف`) ; variante أجزاء من ألف acceptée en prose seulement. Singulier : جزء من ألف. |
| digit | رقم | raqm | **≠ عدد.** رقم = chiffre (symbole 0–9), عدد = nombre. Distinction à tenir rigoureusement (« la valeur du chiffre 7 dans 3.75 » = قيمة الرقم 7). |
| number | عدد | ʿadad | — |
| whole number | عدد صحيح | ʿadad ṣaḥīḥ | Conforme fractions (`التعرف على العدد الصحيح ككسر`) et draft (`ضرب عدد عشري في عدد صحيح`). |
| value of a digit | قيمة الرقم | qīmat ar-raqm | — |
| placeholder zero | الصفر الحافظ للمنزلة | aṣ-ṣifr al-ḥāfiẓ lil-manzila | Contexte `zero as placeholder` (draft). |
| trailing / non-significant zero | صفر غير مؤثر | ṣifr ghayr muʾaththir | Piège 0.5 = 0.50 (misconception A4) ; utilisé dans les stems du contexte `trailing zero`. |

### 3.2 Formes et représentations

| Terme EN | Terme AR canonique | Translittération | Note d'usage EAU/MoE |
|---|---|---|---|
| standard form | الصورة القياسية | aṣ-ṣūra al-qiyāsiyya | MoE. |
| expanded form | الصورة الممتدة | aṣ-ṣūra al-mumtadda | Contexte `expanded form` (draft). Variante الصيغة الموسعة à ne pas utiliser. |
| word form | الصورة اللفظية | aṣ-ṣūra al-lafẓiyya | Contextes `words to numeral` / `numeral to words`. |
| read / write (a decimal) | قراءة / كتابة | qirāʾa / kitāba | Conforme draft (`قراءة الأعداد العشرية وكتابتها`). |
| number line | خط الأعداد | khaṭṭ al-aʿdād | Conforme fractions et draft. Verbe : تمثيل … على خط الأعداد (draft décimaux) ; les fractions emploient تحديد موضع — les deux existent en base, **canonique décimaux = تمثيل** (label du nœud `DECIMAL_NUMBER_LINE`). |
| convert (decimal ↔ fraction) | التحويل بين | at-taḥwīl bayna | Conforme draft (`التحويل بين الأعداد العشرية والكسور`) et fractions (`تحويل العدد الكسري…`). |
| fraction | كسر | kasr | Glossaire fractions existant (repris tel quel). |
| numerator / denominator | بسط / مقام | basṭ / maqām | Glossaire fractions existant. |
| equivalent | مكافئ | mukāfiʾ | Conforme fractions (`الكسور المتكافئة`). |
| mixed number | عدد كسري | ʿadad kasrī | Conforme fractions. |

### 3.3 Comparaison, ordre, arrondi

| Terme EN | Terme AR canonique | Translittération | Note d'usage EAU/MoE |
|---|---|---|---|
| compare | مقارنة | muqārana | Conforme fractions et draft. |
| order (v.) | ترتيب | tartīb | Conforme draft (`مقارنة الأعداد العشرية وترتيبها`). Croissant/décroissant : تصاعديًا / تنازليًا. |
| greater than | أكبر من | akbar min | Symbole `>` inchangé (LTR). |
| less than | أصغر من | aṣghar min | Symbole `<` inchangé. |
| equal to | يساوي | yusāwī | — |
| round (v.) | تقريب | taqrīb | Conforme draft (`تقريب عدد عشري`). Impératif de consigne : قرِّب. |
| to the nearest whole / tenth / hundredth | إلى أقرب عدد صحيح / عُشر / جزء من مئة | ilā aqrab… | Contextes `to nearest whole/tenths/hundredths`. |
| estimate | تقدير | taqdīr | Contexte `estimation check` ; verbe : قدِّر. |

### 3.4 Opérations

| Terme EN | Terme AR canonique | Translittération | Note d'usage EAU/MoE |
|---|---|---|---|
| add / addition | جمع | jamʿ | Conforme fractions/draft. |
| subtract / subtraction | طرح | ṭarḥ | Conforme fractions/draft. |
| multiply / multiplication | ضرب | ḍarb | **Régime : ضرب X في Y** (conforme draft `ضرب عدد عشري في عدد صحيح`). |
| divide / division | قسمة | qisma | **Régime : قسمة X على Y** (conforme draft `قسمة عدد عشري على عدد صحيح`). |
| sum | المجموع | al-majmūʿ | Variante ناتج الجمع acceptée ; une seule forme par item. |
| difference | الفرق | al-farq | — |
| product | ناتج الضرب | nātij aḍ-ḍarb | — |
| quotient | ناتج القسمة | nātij al-qisma | — |
| powers of ten | قوى العدد عشرة | quwā al-ʿadad ʿashara | Conforme draft (`…قوى العدد عشرة`). |
| regrouping (carry / borrow) | إعادة التجميع | iʿādat at-tajmīʿ | Terminologie MoE (curricula d'origine US) : couvre la retenue (جمع) et l'emprunt (طرح). Éviter حمل / استلاف. |

### 3.5 Contextes EAU (money model)

| Terme EN | Terme AR canonique | Translittération | Note d'usage EAU/MoE |
|---|---|---|---|
| dirham (AED) | درهم | dirham | Monnaie des items `money model` ; pluriel دراهم. |
| fils | فلس | fils | 1 درهم = 100 فلس → support naturel des أجزاء المئة. Pluriel فلوس. |
| change (money) | الباقي | al-bāqī | Contexte `money change` (soustraction). |

**Gate glossaire** : ce glossaire doit être **validé par la linguiste** (jalon A-4 du cadrage : « glossaire validé linguiste ; convention chiffres/point formalisée ») avant toute traduction de masse. Toute modification post-validation est versionnée dans ce fichier.

---

## 4. Guide de style

### 4.1 Registre et rédaction

- **MSA scolaire (الفصحى)**, registre des manuels MoE. Aucun dialectal, aucun calque de l'anglais.
- **Un terme canonique par concept** (§3) — pas de variation synonymique à l'intérieur d'un item ni entre items d'une même compétence.
- Consignes à l'impératif standard des manuels : قرِّب، قارن، رتِّب، احسب، اكتب، مثِّل.
- Ponctuation arabe dans la prose : virgule `،` (U+060C), point d'interrogation `؟` (U+061F). **Jamais** de ponctuation arabe à l'intérieur d'une expression mathématique.
- Cohérence avec le corpus fractions : les 300 items AR existants sont le référentiel de ton. En cas de doute stylistique, s'aligner sur eux.

### 4.2 RTL texte / LTR expressions mathématiques

Règle générale : **le texte arabe est RTL ; toute expression mathématique (nombres, opérations, comparaisons) reste un îlot LTR strictement identique à la version EN.**

1. **Ne jamais traduire ni réordonner** une expression : `2.5 + 0.35`, `0.4 × 0.6`, `3 − 0.45`, `1.2 ÷ 4`, `0.3 < 0.25` s'écrivent à l'identique dans le stem AR. Symboles : `× ÷ + − = < >` (mêmes points de code que l'EN).
2. **Laisser l'algorithme bidi Unicode travailler** : les chiffres 0–9 et les opérateurs sont gérés nativement dans un paragraphe RTL. On n'insère **pas** de caractères de contrôle bidi (LRM U+200E, LRI U+2066, PDI U+2069…) par défaut.
3. **Si** un problème de rendu est constaté (typique : séquences mixtes `a < b` ou expressions commençant/finissant par un opérateur), le correctif est **côté rendu UI** (isolation CSS/`dir`), **jamais** dans les données. Interdiction stricte de caractères de contrôle invisibles dans `stem`, `options`, `answer` : ils casseraient la comparaison déterministe de `ar_math_preserved()` (comparaison d'ensembles de chaînes normalisées chiffres seulement) — d'où le scan de points de code invisibles prévu en F4.
4. Rédiger les stems pour que l'expression mathématique soit **un bloc continu** (ne pas éclater `2.5 + 0.35` de part et d'autre d'un segment arabe).
5. Monnaie : `3.75 درهم` (nombre LTR suivi de l'unité arabe) — usage conforme aux manuels.
6. Les fractions héritent des conventions du corpus existant (notation `a/b` LTR préservée).

### 4.3 Options et réponse (contrainte pipeline)

- MCQ : mêmes options, même ordre que l'EN (le prompt système de `translate_to_arabic()` l'impose déjà : *« Preserve the order of options »*).
- `answer` AR = copie exacte de l'option correspondante (garde-fou MCQ de `translate_to_arabic()`).
- Les options purement numériques (`0.45`, `2.85`…) sont **identiques octet pour octet** entre EN et AR.

---

## 5. Charge de validation chiffrée

Base : volumétrie A7 — **14 nœuds × ~10 items/langue = ~140 items AR** (banque cible décimaux : ~280 items, 140 EN + 140 AR).

| Poste | Volume | Hypothèse | Charge |
|---|---|---|---|
| Validation du glossaire + guide de style (ce document) | 1 doc | relecture + arbitrages avec linguiste | **0,5 j** |
| Traduction machine (ALLaM via `translate_bank_ar.py`) | 140 items | automatique, idempotent, retries | ~0 (coût API marginal) |
| Checks automatiques pré-file (fidélité math + tokens latins) | 140 items | `check_ar_fidelity.py` (F1 + F2 **déjà implémentés**) | ~0 (reste optionnel : lint F3/F4, cf. §6) |
| **Validation linguiste — 1ʳᵉ passe** | 140 items | ~4 min/item (lecture stem + options + glossaire + décision) | **~9,5 h ≈ 1,2 j** |
| **Reprises** (items recalés : correction `set_arabic` + re-validation) | ~15–20 % ≈ 21–28 items | ~6 min/item (réécriture) | **~2,5 h ≈ 0,3 j** |
| Échantillon de contrôle final avant `active` (10 %) | 14 items | seconde lecture rapide | **~1 h** |
| **Total linguiste** | | | **≈ 2 j** |

Cohérent avec le cadrage §5 (A6 : 2 j linguiste + Claude) ; la validation de production s'étale dans la fenêtre A-6 (~5–8 j). Les items flagués par les checks automatiques (`ar_math_broken`, tokens latins) remontent **en tête de file** : le temps linguiste se concentre sur les cas à risque.

**Débit de référence** : ~70 items/jour en rythme soutenu → la file complète des 140 items se traite en 2 jours pleins ou 4 demi-journées.

---

## 6. Critères de fidélité (gate G3)

Un item AR ne peut être `ar_validated=true` que si **F1–F5** passent. F1–F2 sont automatiques et s'exécutent **avant** la file linguiste ; F3–F5 relèvent de la validation humaine.

| # | Critère | Vérification | Outillage |
|---|---|---|---|
| **F1** | **Nombres préservés** : `answer` et l'ensemble des `options` AR identiques à l'EN après normalisation des chiffres | Automatique, déterministe | `ar_math_preserved()` (`src/items/arabic.py`) via `scripts/check_ar_fidelity.py` ; `--flag` pose `provenance.ar_math_broken=true` → tête de file linguiste |
| **F2** | **Aucun token latin résiduel** dans `stem`, `options` et `answer` AR (hors notation mathématique : chiffres et symboles, qui ne contiennent aucune lettre — zéro faux positif ; une lettre isolée, ex. variable « x », est tolérée) | Automatique — **implémenté (errata E8)** : regex `[A-Za-z]{2,}`, dédoublonné, ordre d'apparition conservé ; `--flag` pose `provenance.ar_latin_tokens=[…]` → tête de file linguiste | `ar_latin_tokens()` / `ar_content_latin_tokens()` (`src/items/arabic.py`) via `scripts/check_ar_fidelity.py`. Motivation : un item fractions **actif** contient le mot anglais « ONE » non traduit, invisible au check numérique F1. **Rattrapage banque fractions** : exécuter `check_ar_fidelity.py --flag` sur la banque existante et purger la file avant production A-6. |
| **F3** | **Terminologie glossaire** : les termes du §3 sont utilisés à l'exclusion de tout synonyme ; en particulier الفاصلة العشرية est absent des stems | Linguiste (systématique) + lint lexical **à outiller** (liste de termes proscrits : الفاصلة العشرية، الصيغة الموسعة، حمل، استلاف، chiffres orientaux `[٠-٩]`) | Revue linguiste ; lint proscrit = petite extension de `check_ar_fidelity.py` (~0,25 j), non bloquante (la revue linguiste couvre F3 en attendant) |
| **F4** | **RTL/LTR corrects** : stem lisible RTL, expressions mathématiques intactes LTR, aucun caractère de contrôle bidi dans les données | Linguiste (spot-check rendu UI sur échantillon) + scan automatique **à outiller** des points de code invisibles (U+200E/F, U+202A–E, U+2066–69) dans `stem/options/answer` | Scan intégrable à la même extension que le lint F3 |
| **F5** | **Équivalence sémantique** : l'énoncé AR conduit exactement à la même réponse mathématique que l'EN (F1 ne compare que answer/options, pas le sens du stem) | Linguiste : re-résolution mentale de l'item en AR avant validation | Revue linguiste (critère central de la 1ʳᵉ passe) |

**Règle gate G3 (rappel cadrage/A8)** : fidélité math ✅ **et** détection tokens latins ✅ **et** validation linguiste ✅ **et** `ar_validated=true` — sinon l'item ne devient jamais `active` (garde câblée dans le code, cf. §7).

---

## 7. Workflow linguiste (machine à états `src/items/review.py`)

### 7.1 Cycle de vie d'un item (aucun saut d'étape)

```
ai_generated ──approve()──▶ human_reviewed ──validate_arabic()──▶ linguist_validated ──promote_to_active()──▶ active ⇄ quarantined
                                   │                                                            ▲
                                   └── set_arabic() propose/corrige l'AR (ar_validated=False) ──┘ (garde : ar_validated=True exigé)
```

États (`ItemStatus`) : `ai_generated → human_reviewed → linguist_validated → active` (+ `quarantined ⇄ active`). Les transitions sont verrouillées par `ALLOWED_TRANSITIONS` ; la garde `TRANSITION_GUARDS` exige `ar_validated and content_ar` pour atteindre `linguist_validated`, et `promote_to_active()` re-vérifie `ar_validated`. **La parité AR est donc structurellement bloquante** : aucun item décimal ne sera servi sans validation linguiste (mitigation du risque n°4 du cadrage, « rupture de parité AR »).

### 7.2 Déroulé opérationnel (production A-6)

| Étape | Qui | Action | Outil / fonction |
|---|---|---|---|
| 1. Génération EN | déterministe (A5) | items décimaux persistés `ai_generated` | `insert_generated_items()` |
| 2. Revue EN | fondateur | `approve()` → `human_reviewed` (ou `reject(reason)` = soft delete tracé, ou `edit()`) | `scripts/review_items.py` |
| 3. Proposition AR machine | pipeline | ALLaM (`allam-2-7b`) traduit chaque item sans `content_ar` ; sortie validée `ItemContent` + règle MCQ ; persistée avec `ar_validated=False` | `scripts/translate_bank_ar.py` → `translate_to_arabic()` + `set_arabic(by="allam")` |
| 4. Checks automatiques | pipeline | F1 fidélité math + F2 tokens latins, `--flag` pose `ar_math_broken` / `ar_latin_tokens` dans `provenance` ; items flagués priorisés | `scripts/check_ar_fidelity.py` (**opérationnel** ; lint F3/F4 optionnel à ajouter) |
| 5. File linguiste | linguiste | worklist = items `human_reviewed` avec `ar_validated=False` ; contrôle F3/F4/F5 contre glossaire §3 et style §4 | `list_pending_arabic()` |
| 6a. AR conforme | linguiste | validation → `ar_validated=True` puis promotion `linguist_validated` (traçée : `provenance.ar_validated_by`) | `validate_arabic(linguist=…)` |
| 6b. AR à corriger | linguiste | correction du `content_ar` (l'EN n'est **jamais** altéré) ; **toute modification remet `ar_validated=False`** → repasse en 5 | `set_arabic(by=linguiste)` |
| 7. Activation | fondateur | promotion `active` (garde `ar_validated`) — franchit G3 | `promote_to_active()` |
| 8. Suivi de couverture | fondateur | métriques : `with_ar`, `ar_validated`, `math_preserved`, `pct_validated` — la « descente » de l'AR reste mesurable pendant toute la production | `ar_coverage()` |

**Traçabilité** : chaque action écrit `provenance` (`reviewer`, `reviewed_at`, `ar_proposed_by`, `ar_validated_by`, `rejected/reject_reason`) — l'audit trail exigé par la doctrine du référentiel s'applique aussi à l'AR.

**Onboarding** : la linguiste est provisionnée via `scripts/onboard_linguist.py` (déjà en place depuis le MVP fractions).

---

## 8. Points ouverts et risques propres à l'AR décimaux

| # | Point | Traitement |
|---|---|---|
| 1 | **Lint F2 (tokens latins) : implémenté** (`ar_latin_tokens`, `check_ar_fidelity.py`) ; **restent à outiller** : lint lexical F3 (termes proscrits + chiffres orientaux) et scan bidi F4 | F2 : rattrapage à exécuter sur la banque fractions (cas « ONE » connu, errata E8) avant production A-6. F3/F4 : petite extension (~0,25 j), non bloquante (couverte par la revue linguiste en attendant) |
| 2 | Chiffres orientaux dans 2 `label_ar` fractions (`١/ب`, `١٠٠`) | Harmonisation cosmétique, hors chemin critique (labels ≠ items servis) |
| 3 | Sensibilité de la traduction machine au séparateur décimal (risque : ALLaM réécrit `0.5` en `0,5` ou `٠٫٥`) | F1 + lint F2 l'attrapent ; si taux d'échec élevé, durcir le prompt système de `translate_to_arabic()` (mention explicite « keep the period as decimal separator ») |
| 4 | Variantes MoE (الفاصلة العشرية, أجزاء من مئة) connues des élèves | Tranché §2/§3 : compréhension acceptée, production interdite ; à confirmer par la linguiste et par l'enseignant EAU lors de la double lecture A1.8 |
| 5 | Le mot عشري/أعشار prête à confusion entre « décimal » (عشري) et « dixièmes » (أعشار) dans certaines formulations | Guide linguiste : toujours accoler منزلة pour la position (منزلة الأعشار) ; revue F3 |

---

*Priors, glossaire et conventions de ce plan sont des choix experts — validés par la linguiste puis figés avant production ; toute évolution est versionnée ici.*

**Historique** : v0.1 (2026-07-11) rédaction initiale · v0.2 (2026-07-12) mise à jour outillage — le lint tokens latins F2 (errata E8) est **implémenté** (`src/items/arabic.py` : `ar_latin_tokens`/`ar_content_latin_tokens` ; `scripts/check_ar_fidelity.py` : détection + `--flag` → `provenance.ar_latin_tokens`) ; restent à outiller le lint lexical F3 et le scan bidi F4 (non bloquants).
