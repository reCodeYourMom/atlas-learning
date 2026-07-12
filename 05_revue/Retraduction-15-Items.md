# Retraduction des 15 items arabes en quarantaine — kit de validation linguiste

**Lot 2 du dossier de revue** · **Date** : 2026-07-12 · **Statut** : PROPOSITION — à valider
**Destinataire** : linguiste native AR · **Budget cible : 1 heure** (≈ 4 min/item)
**Source** : `04_code/atlas_bank.db`, items en statut `quarantined` · **Sortie machine** : `05_revue/retraductions_proposees.json`

> **Aucun item n'est réactivé par ce document.** Les propositions ci-dessous sont des **brouillons machine**. La réactivation passe **exclusivement** par le workflow `04_code/src/items/review.py` (`set_arabic` → `validate_arabic` → `promote_to_active`), déclenché par vous, après votre validation. Rien n'a été écrit en base.

---

## 1. Ce qui s'est passé, en une minute

15 items de la banque fractions ont été mis en quarantaine le 2026-07-12. Leur version **anglaise est intacte** ; leur version **arabe est corrompue** : les nombres du stem ont été remplacés par des **glyphes parasites** — grec (`π`, `α`, `ε`, `φ`, `τ`, `η`, `ς`), symboles (`±`, `Ⓒ`, `£`, `·`), fractions Unicode (`⅕`, `⅒`, `⅖`), diacritiques combinantes (`̄`, `̆`, `̈`). Un item a en plus un stem inintelligible (répétition parasite).

**Origine** : traduction machine (`allam`, cf. `provenance.ar_proposed_by`). **Détection** : `ar_content_suspect_glyphs()` (`src/items/arabic.py`), ajouté après la revue du 2026-07-12.

**Ce que vous faites** : pour chacun des 15 items, vous lisez l'anglais, le diagnostic, et **la proposition de retraduction**. Vous cochez **VALIDER** (la proposition part telle quelle) ou **CORRIGER** (vous récrivez, votre texte fait foi).

**Ce que débloque votre signature** : la réactivation des 15 items → la banque fractions repasse à 299 items actifs (contre 284 aujourd'hui).

---

## 2. Conventions appliquées à toutes les propositions

Reprises de `03_referentiel/Plan-Production-AR-Decimaux.md` §2–§4 :

| Règle | Appliqué |
|---|---|
| Arabe standard moderne (الفصحى), registre des manuels MoE | ✅ |
| **Chiffres occidentaux 0–9** (jamais `٠١٢٣٤٥٦٧٨٩`) | ✅ |
| **Fractions en notation ASCII** `a/b`, îlot LTR, identique à l'EN | ✅ |
| Texte RTL / expressions mathématiques LTR, **jamais** de caractère de contrôle bidi dans les données | ✅ (aucun U+200E/F, U+202A–E, U+2066–69 inséré) |
| Options : **même ordre** que l'EN ; `answer` AR = **copie exacte** de l'option correspondante, **au même index** que l'EN | ✅ vérifié sur les 15 |
| Terminologie : `كسر` (fraction), `عدد مختلط` (nombre mixte), `كسر غير صحيح` (fraction impropre) | ✅ |

### ⚠️ Deux arbitrages de terminologie que je vous laisse — ils dépassent ces 15 items

Le **glossaire** (§3.3 du Plan de production) et le **corpus actif** (284 items) ne disent pas la même chose :

| Concept | Glossaire §3.3 | Corpus actif (items sains) | Ce que j'ai retenu |
|---|---|---|---|
| *less than* | **أصغر من** | **أقل من** (majoritaire) | **أقل من** — cohérence avec les items frères servis dans la **même session** à l'élève |
| *equal to* | **يساوي** | **متساوي مع** / *ساوي* / *مساواة* (3 variantes en base !) | **متساوي مع** — forme majoritaire du corpus |
| *Compared to…* | — | **مقارنة ب 1/2** (sans le `ـ`) | **مقارنة بـ 1/2** (orthographe correcte) |

**Mon raisonnement** : ces 15 items seront servis **mélangés** aux items sains des mêmes compétences. Une divergence de vocabulaire entre deux items de la même compétence, dans la même session, est un bruit de mesure. J'ai donc privilégié la **cohérence avec le corpus**, pas avec le glossaire.

**Mais le corpus lui-même est incohérent** (trois formes pour « equal to »). C'est une décision d'harmonisation à part entière, qui touche ~30 items, pas 15 — **à ne pas trancher sur ce dossier**.

> **Arbitrage de terminologie (à cocher une fois, s'applique aux 15) :**
> - [ ] **OK, je suis le corpus** (أقل من / متساوي مع / مقارنة بـ) — recommandé
> - [ ] **Non, je suis le glossaire** (أصغر من / يساوي) — *et j'ouvre une tâche d'harmonisation du corpus, sinon on crée une 4ᵉ variante*
> - [ ] Autre : ____________________________________________________________

---

## 3. Les 15 fiches

Chaque fiche porte le résultat des **3 checks automatiques** rejoués sur ma proposition (`src/items/arabic.py`, exécutés le 2026-07-12) :

- **F1** `ar_math_preserved(en, proposition)` → doit être `True`
- **F2** `ar_content_latin_tokens(proposition)` → doit être `[]`
- **F3** `ar_content_suspect_glyphs(proposition)` → doit être `[]`

**Résultat global : 15/15 propositions passent les 3 checks.**

> 🔴 **Limite à garder en tête** : F1 ne compare que les **nombres** de `answer` et `options`. Il **ne lit pas le stem** et **ne détecte rien** sur les items à réponse textuelle (les 4 items `COMPARE_BENCHMARK` ci-dessous : « أكبر من / أقل من / متساوي مع » ne contiennent aucun chiffre). Sur ces items, **vous êtes le seul contrôle** (critère F5 : re-résoudre l'item en arabe). C'est exactement le trou par lequel la corruption est passée. Voir `Revue-Code-Findings.md`, finding **CRIT-1**.

---

### `MATH.G3.NF.COMPARE_SAME_NUM` — 1 item

#### Item 1/15 — `9db67291-c593-4f35-8a4b-6886c834055c`

**EN (intact, ne pas toucher)**
> **stem** : Which is greater: 1/2 or 1/6?
> **options** : `They are equal` · `2/2` · `1/2` · `1/6` — **answer** : `1/2` *(index 2)*

**AR corrompu (en base)**
> **stem** : أي أكبر بين ±̆ أو ±̄?
> **options** : `هما متساويان` · `±̆ ±̆` · `±̄` · `±̆` — **answer** : `±̄`

**Diagnostic** · glyphes relevés en provenance : **`±` `̆` `̄`** (`ar_suspect_glyphs`, `ar_math_broken: true`).
Les fractions `1/2` et `1/6` ont été remplacées par `±̆` et `±̄` **dans le stem ET dans les options**. La bonne réponse pointe vers `±̄`, c.-à-d. l'ancien `1/6` : **la clé de correction arabe désignait la mauvaise option.** Item le plus gravement atteint des 15.

**PROPOSITION — à valider**
> **stem** : أي أكبر بين 1/2 أو 1/6؟
> **options** : `هما متساويان` · `2/2` · `1/2` · `1/6` — **answer** : `1/2` *(index 2 ✓ = EN)*

*Style : calqué sur les items sains de la compétence (« أي أكبر بين 3/4 أو 3/8؟ »). Le distracteur textuel « هما متساويان » est la forme déjà utilisée en base.*

**Checks** : F1 `ar_math_preserved` = **True** ✅ · F2 `latin_tokens` = **[]** ✅ · F3 `suspect_glyphs` = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → votre version : ____________________________________________

---

### `MATH.G4.NF.COMPARE_BENCHMARK` — 4 items

> ⚠️ **Ces 4 items ont une réponse purement textuelle.** F1 est structurellement aveugle dessus (0 chiffre dans les options). Votre relecture est **le seul filet**. Vérifiez en particulier que la réponse cochée correspond bien à la comparaison mathématique.

#### Item 2/15 — `b8c11104-5ebb-4b1a-9c0d-4fbf0f43f62a`

**EN** · **stem** : Compared to 1/2, the fraction 3/8 is…
**options** : `equal to` · `less than` · `greater than` — **answer** : `less than` *(index 1)* — *(3/8 = 0.375 < 0.5 ✓)*

**AR corrompu** · **stem** : مقارنة بـ <⅕⅕⅕⅕⅕⅕⅕⅕ (1/2)، الجزء ⅕⅕⅕⅕⅕⅕⅕⅕⅕ هو…
**options** : `متساوي مع` · `أقل من` · `أكبر من` — **answer** : `أقل من`

**Diagnostic** · glyphe relevé : **`⅕`** (VULGAR FRACTION ONE FIFTH, U+2155), répété en rafale. Le nombre `3/8` du stem a disparu, remplacé par 9 occurrences de `⅕`. Le terme `الجزء` (la part) est employé au lieu de `الكسر` (la fraction). Les options sont saines ; la clé est correcte. **Seul le stem est à refaire.**

**PROPOSITION**
> **stem** : مقارنة بـ 1/2، الكسر 3/8 هو…
> **options** : `متساوي مع` · `أقل من` · `أكبر من` — **answer** : `أقل من` *(index 1 ✓)*

**Checks** : F1 = **True** ✅ *(vacuously — aucun chiffre dans les options)* · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 3/15 — `7a25bb9b-912a-4d89-a4df-a7d4b44a30a8`

**EN** · **stem** : Compared to 1/2, the fraction 5/6 is…
**options** : `greater than` · `less than` · `equal to` — **answer** : `greater than` *(index 0)* — *(5/6 ≈ 0.833 > 0.5 ✓)*

**AR corrompu** · **stem** : مقارنة بـ من الم/ناماية, الم/ناماية التالية الم/ناماية الم/ناماية الم/ناماية
**options** : `أكبر` · `أقل` · `متساوي` — **answer** : `أكبر`

**Diagnostic** · **pas de glyphe parasite** — c'est le seul item quarantainé pour `ar_stem_garbled` : *« stem AR inintelligible (répétition parasite), nombres 1/2 et 5/6 absents »*. Le stem est du **charabia** (`الم/ناماية` n'est pas un mot arabe) et les deux nombres ont disparu. Les options sont tronquées (`أكبر` sans `من`), incohérentes avec les items frères.
🔴 **Cet item ne portait AUCUN glyphe suspect : il a passé F1, F2 et F3.** Il n'a été attrapé que par une inspection humaine. Voir `Revue-Code-Findings.md`, **CRIT-1**.

**PROPOSITION**
> **stem** : مقارنة بـ 1/2، الكسر 5/6 هو…
> **options** : `أكبر من` · `أقل من` · `متساوي مع` — **answer** : `أكبر من` *(index 0 ✓)*

*Les options sont complétées (`أكبر من` au lieu de `أكبر`) pour s'aligner sur les 7 items sains de la compétence.*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 4/15 — `bc74bfa5-7fd2-4f77-b825-8a8f18f1d4b6`

**EN** · **stem** : Compared to 1/2, the fraction 2/6 is…
**options** : `greater than` · `equal to` · `less than` — **answer** : `less than` *(index 2)* — *(2/6 ≈ 0.333 < 0.5 ✓)*

**AR corrompu** · **stem** : مقارنة بـ ±Ⓒ، الكسر ⅒⅖ هو…
**options** : `أكبر من` · `ساوي` · `أقل من` — **answer** : `أقل من`

**Diagnostic** · glyphes : **`±` `Ⓒ` `⅒` `⅖`**. `1/2` → `±Ⓒ`, `2/6` → `⅒⅖`. Option 2 = `ساوي` (forme fautive/tronquée de `يساوي` / `متساوي مع`).

**PROPOSITION**
> **stem** : مقارنة بـ 1/2، الكسر 2/6 هو…
> **options** : `أكبر من` · `متساوي مع` · `أقل من` — **answer** : `أقل من` *(index 2 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 5/15 — `3deaf49a-00ff-4a7d-8559-dfbc5f40d3d5`

**EN** · **stem** : Compared to 1/2, the fraction 7/12 is…
**options** : `equal to` · `greater than` · `less than` — **answer** : `greater than` *(index 1)* — *(7/12 ≈ 0.583 > 0.5 ✓)*

**AR corrompu** · **stem** : مقارنة بـ ±Ⓒ، الكسر ·£ 7 £Ⓒ هو…
**options** : `يساوي` · `أكبر من` · `أقل من` — **answer** : `أكبر من`

**Diagnostic** · glyphes : **`±` `Ⓒ` `·` `£`**. `1/2` → `±Ⓒ` ; `7/12` → `·£ 7 £Ⓒ` (le `7` a survécu, le `/12` non). Option 1 = `يساوي` (4ᵉ variante d'« equal to » dans la banque…).

**PROPOSITION**
> **stem** : مقارنة بـ 1/2، الكسر 7/12 هو…
> **options** : `متساوي مع` · `أكبر من` · `أقل من` — **answer** : `أكبر من` *(index 1 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

### `MATH.G5.NF.ADD_MIXED` — 3 items

*Style de référence (items sains) : « ما هو مجموع 1 1/3 + 2 1/3؟ (عدد مختلط) », options identiques à l'EN octet pour octet.*

#### Item 6/15 — `0bb0221c-f1ea-4ff8-8a1d-c3ebca31d335`

**EN** · **stem** : What is 2 1/4 + 1 1/4? (mixed number)
**options** : `3 1/2` · `3 1/4` · `4 1/2` — **answer** : `3 1/2` *(index 0)*

**AR corrompu** · **stem** : ما هو مجموع 2πα + 1πα؟ (عدد مختلط)
**options** : `3πας` · `3πα` · `4πας` — **answer** : `3πας`

**Diagnostic** · glyphes : **`π` `α` `ς`** (grec). `1/4` → `πα`, `1/2` → `πας`. **Les options ET le stem sont atteints** : aucun nombre exploitable ne subsiste dans la version arabe. `ar_math_broken: true`.

**PROPOSITION**
> **stem** : ما هو مجموع 2 1/4 + 1 1/4؟ (عدد مختلط)
> **options** : `3 1/2` · `3 1/4` · `4 1/2` — **answer** : `3 1/2` *(index 0 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 7/15 — `d801c369-c4d3-453d-80c0-130b54df4f64`

**EN** · **stem** : What is 1 1/6 + 1 1/6? (mixed number)
**options** : `2 1/3` · `2 1/6` · `3 1/3` — **answer** : `2 1/3` *(index 0)*

**AR corrompu** · **stem** : ما هو مجموع 1 ±π + 1 ±π؟ (عدد مختلط)
**options** : `3 ±π±π` · `2 ±π±π` · `3 ±π±π` — **answer** : `3 ±π±π`

**Diagnostic** · glyphes : **`±` `π`**. ⚠️ **Le plus grave des 3 :** les options 1 et 3 sont devenues **identiques** (`3 ±π±π`), et l'`answer` pointe sur la **première** — alors que la bonne réponse EN (`2 1/3`) était à l'index 0. La version arabe servait donc à l'élève **un QCM avec deux options identiques et une clé fausse**. `ar_math_broken: true`.

**PROPOSITION**
> **stem** : ما هو مجموع 1 1/6 + 1 1/6؟ (عدد مختلط)
> **options** : `2 1/3` · `2 1/6` · `3 1/3` — **answer** : `2 1/3` *(index 0 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 8/15 — `feb1bcc9-2028-4968-9ca4-0a77eb9ae368`

**EN** · **stem** : What is 1 3/4 + 2 1/4? (mixed number)
**options** : `5` · `4` · `3 1/2` — **answer** : `4` *(index 1)*

**AR corrompu** · **stem** : ما هو مجموع 1πη + 2πη؟ (عدد مختلط)
**options** : `5` · `4` · `3πη` — **answer** : `4`

**Diagnostic** · glyphes : **`π` `η`**. `3/4` → `πη`, `1/4` → `πη` (les deux fractions **différentes** de l'EN ont été mappées sur le **même** glyphe : l'énoncé arabe demandait `1x + 2x`). Les entiers `5` et `4` ont survécu, donc la clé est restée correcte — mais l'énoncé était insoluble. `ar_math_broken: true`.

**PROPOSITION**
> **stem** : ما هو مجموع 1 3/4 + 2 1/4؟ (عدد مختلط)
> **options** : `5` · `4` · `3 1/2` — **answer** : `4` *(index 1 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

### `MATH.G5.NF.MIXED_TO_IMPROPER` — 7 items

*Style de référence (items sains) : « تحويل 3 2/5 إلى كسر غير صحيح. », options identiques à l'EN.*
*Note : le corpus utilise le **masdar** (`تحويل`, « conversion de… ») là où le guide de style §4.1 prescrit l'impératif (`حوِّل`). J'ai suivi le corpus. **Si vous préférez l'impératif, cochez ici une fois — je l'appliquerai aux 7 :*** ☐ `حوِّل` au lieu de `تحويل`.

#### Item 9/15 — `a7806c35-16b4-44f6-9b1a-5ac04b13d813`

**EN** · **stem** : Convert 2 1/3 to an improper fraction.
**options** : `7/3` · `2/3` · `3/3` · `7/5` — **answer** : `7/3` *(index 0)*

**AR corrompu** · **stem** : تحويل 2πα إلى كسر غير صحيح.
**options** : `7/3` · `2/3` · `3/3` · `7/5` — **answer** : `7/3`

**Diagnostic** · glyphes : **`π` `α`**. `1/3` → `πα` **dans le stem seulement** ; les options sont intactes. L'élève arabophone voyait donc « convertir 2πα » — énoncé insoluble, mais QCM à 4 options plausibles : **il répondait au hasard, et l'Elo enregistrait un échec de compétence**. *(Ce profil — stem cassé, options saines — concerne 6 des 7 items de cette compétence.)*

**PROPOSITION**
> **stem** : تحويل 2 1/3 إلى كسر غير صحيح.
> **options** : `7/3` · `2/3` · `3/3` · `7/5` — **answer** : `7/3` *(index 0 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 10/15 — `dbc4f1af-d29f-4965-b23c-dcf1a20a3afe`

**EN** · **stem** : Convert 1 3/4 to an improper fraction.
**options** : `3/4` · `4/4` · `7/5` · `7/4` — **answer** : `7/4` *(index 3)*

**AR corrompu** · **stem** : تحويل 1τ إلى كسر غير صحيح.
**options** : `τ` · `1` · `7/5` · `7/4` — **answer** : `7/4`

**Diagnostic** · glyphe : **`τ`**. Ici **les options aussi sont touchées** : `3/4` → `τ` et `4/4` → `1` (!). L'option `1` est mathématiquement *vraie* comme valeur de 4/4, mais ce n'est plus le distracteur prévu. `ar_math_broken: true`.

**PROPOSITION**
> **stem** : تحويل 1 3/4 إلى كسر غير صحيح.
> **options** : `3/4` · `4/4` · `7/5` · `7/4` — **answer** : `7/4` *(index 3 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 11/15 — `8a4f50b5-7983-4c88-8dca-6445fecac9ec`

**EN** · **stem** : Convert 1 1/2 to an improper fraction.
**options** : `3/2` · `1/2` · `2/2` · `3/3` — **answer** : `3/2` *(index 0)*

**AR corrompu** · **stem** : تحويل 1πε إلى كسر غير صحيح. — *options intactes*

**Diagnostic** · glyphes : **`π` `ε`**. `1/2` → `πε` dans le stem. Options et clé saines.

**PROPOSITION**
> **stem** : تحويل 1 1/2 إلى كسر غير صحيح.
> **options** : `3/2` · `1/2` · `2/2` · `3/3` — **answer** : `3/2` *(index 0 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 12/15 — `5e17f032-755c-40f9-8171-ec8043a41a4e`

**EN** · **stem** : Convert 4 1/3 to an improper fraction.
**options** : `4/3` · `5/3` · `13/7` · `13/3` — **answer** : `13/3` *(index 3)*

**AR corrompu** · **stem** : تحويل 4πα إلى كسر غير صحيح. — *options intactes*

**Diagnostic** · glyphes : **`π` `α`** (`1/3` → `πα`). Options et clé saines.

**PROPOSITION**
> **stem** : تحويل 4 1/3 إلى كسر غير صحيح.
> **options** : `4/3` · `5/3` · `13/7` · `13/3` — **answer** : `13/3` *(index 3 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 13/15 — `89af0fae-edd4-426b-b635-9e7a5d45e53d`

**EN** · **stem** : Convert 2 3/8 to an improper fraction.
**options** : `5/8` · `19/10` · `19/8` · `6/8` — **answer** : `19/8` *(index 2)*

**AR corrompu** · **stem** : تحويل 2̈ **وثلثا** إلى كسر غير صحيح. — *options intactes*

**Diagnostic** · glyphe : **`̈`** (COMBINING DIAERESIS, U+0308). ⚠️ **Cas le plus vicieux des 15** : la fraction `3/8` n'a pas seulement disparu — elle a été **remplacée par un mot arabe faux**, `وثلثا` (« et deux tiers »). L'énoncé arabe demandait donc de convertir **2 2/3**, dont la réponse serait `8/3` — absente des options. C'est une **erreur mathématique lisible**, pas un charabia : un élève arabophone la lit sans se douter de rien et échoue systématiquement.

**PROPOSITION**
> **stem** : تحويل 2 3/8 إلى كسر غير صحيح.
> **options** : `5/8` · `19/10` · `19/8` · `6/8` — **answer** : `19/8` *(index 2 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 14/15 — `a1fa86c2-f012-4379-9daf-4cdb3d1343f9`

**EN** · **stem** : Convert 3 1/4 to an improper fraction.
**options** : `13/7` · `13/4` · `3/4` · `4/4` — **answer** : `13/4` *(index 1)*

**AR corrompu** · **stem** : تحويل 3̄ إلى كسر غير صحيح. — *options intactes*

**Diagnostic** · glyphe : **`̄`** (COMBINING MACRON, U+0304). `1/4` a purement disparu (le stem demande de convertir « 3 »).

**PROPOSITION**
> **stem** : تحويل 3 1/4 إلى كسر غير صحيح.
> **options** : `13/7` · `13/4` · `3/4` · `4/4` — **answer** : `13/4` *(index 1 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

#### Item 15/15 — `ab2b2e68-e991-4ed6-9402-45777e92de3d`

**EN** · **stem** : Convert 1 5/6 to an improper fraction.
**options** : `11/6` · `5/6` · `6/6` · `11/7` — **answer** : `11/6` *(index 0)*

**AR corrompu** · **stem** : تحويل 1φε إلى كسر غير صحيح. — *options intactes*

**Diagnostic** · glyphes : **`φ` `ε`** (`5/6` → `φε`). Options et clé saines.

**PROPOSITION**
> **stem** : تحويل 1 5/6 إلى كسر غير صحيح.
> **options** : `11/6` · `5/6` · `6/6` · `11/7` — **answer** : `11/6` *(index 0 ✓)*

**Checks** : F1 = **True** ✅ · F2 = **[]** ✅ · F3 = **[]** ✅

- [ ] **VALIDER** · [ ] **CORRIGER** → ______________________________________________________

---

## 4. ⚠️ Ce que la revue a trouvé EN PLUS — 5 items **ACTIFS** à retirer du service

En vérifiant les 15 items quarantainés, j'ai scanné les **284 items actifs** de la banque. **Cinq d'entre eux sont servis en arabe avec un énoncé mathématiquement différent de l'anglais** — et **aucun** n'est détecté par F1/F2/F3 (aucun glyphe, aucun token latin, les options sont intactes donc les nombres sont « préservés »).

| ID | Compétence | EN | AR (traduit) | Défaut |
|---|---|---|---|---|
| `4ace2985` | `NF.FRACTION_OF_SET` | *A set has 12 objects. **3/4** of them are red.* → 9 | « **ثلث** هذه الأجسام حمراء » = **un tiers** | **1/3 de 12 = 4**, la clé dit 9 |
| `7037c1cc` | `NF.FRACTION_OF_SET` | *16 objects. **3/8** are red.* → 6 | « **ثلث** » = **un tiers** | **1/3 de 16 ≈ 5,33**, la clé dit 6 |
| `547997f0` | `NF.FRACTION_OF_SET` | *30 objects. **4/5** are red.* → 24 | « **ربعها** » = **un quart** | **1/4 de 30 = 7,5**, la clé dit 24 |
| `2dd2318f` | `NF.FRACTION_OF_SET` | *28 objects. **3/7** are red.* → 12 | « ثلث وسبعون » = **charabia** | énoncé insoluble |
| `5302e9e7` | `NF.EQUIVALENCE_COMPUTE` | *Find the missing **numerator**: 1/4 = x/20* → 5 | « اوجد **المقام المشترك**… » = *trouver le **dénominateur commun*** | **question différente** ; la clé (5) est un numérateur |

*(Un 6ᵉ, `d3515317` / `NF.COMPARE_BENCHMARK`, a un stem partiellement inintelligible — « مقارنة بـ **مور المارات** 1/2، **النسبة** المارات 1/2 » — mais reste mathématiquement soluble : moins urgent.)*

**Pourquoi c'est passé** : ces items écrivent le nombre **en toutes lettres** dans le stem arabe. `ar_math_preserved()` ne compare **que** `answer` et `options` — jamais le stem — et sa docstring le dit explicitement : *« un nombre écrit en toutes lettres (« ثمانية ») n'est volontairement pas comparé »*. Le trou est **connu et documenté**. Ces 5 items en sont l'exploitation.

**Impact mesure** : un élève arabophone échoue systématiquement ces items → son Elo baisse sur `FRACTION_OF_SET` / `EQUIVALENCE_COMPUTE` → le **diagnostic causal** lui attribue une lacune qu'il n'a pas. C'est un **biais de langue (DIF)** injecté directement dans la mesure — exactement ce que la colonne `response.language` (C-0) sert à détecter, mais qui ici n'est pas un biais psychométrique : c'est un **item faux**.

**Action recommandée — hors périmètre de ce dossier, à décider par le fondateur** :
1. Mettre ces 5 items en **quarantaine immédiate** (`run_quarantine.py`), avant toute session pilote en arabe.
2. Les ajouter à votre file de retraduction (même workflow que les 15).
3. Outiller le check manquant : *« tout token numérique du stem EN doit apparaître dans le stem AR »* — 5 lignes dans `check_ar_fidelity.py`. Voir `Revue-Code-Findings.md`, **CRIT-1**.

**Scan complémentaire** : **28 items actifs sur 284** perdent au moins un nombre du stem EN dans le stem AR (chiffre écrit en lettres). Les 23 autres sont **mathématiquement corrects** (ex. « quatre parts » pour « 4 parts ») mais violent la convention E7 (chiffres occidentaux 0–9). Non bloquant, à harmoniser.

> - [ ] J'ai pris connaissance des 5 items actifs défectueux · Fondateur notifié le : ____________

---

## 5. Procédure de clôture (après votre validation)

1. **Vous** cochez VALIDER/CORRIGER sur les 15 fiches + l'arbitrage terminologie (§2). Vous signez ci-dessous.
2. **Le fondateur** reporte vos corrections dans `05_revue/retraductions_proposees.json`
   *(format : `[{"id": "<uuid>", "content_ar": {"stem": …, "options": […], "answer": …}}]`)*.
3. **Le fondateur** rejoue les 3 checks sur le JSON final (`ar_math_preserved`, `ar_content_latin_tokens`, `ar_content_suspect_glyphs`) — **doivent tous passer**.
4. **Le fondateur** importe via le workflow, item par item : `set_arabic(by="<votre nom>")` → **vous** : `validate_arabic(linguist="<votre nom>")` → `promote_to_active()`.
   ⚠️ **Aucun raccourci** : `set_arabic` remet `ar_validated=False` ; la garde `TRANSITION_GUARDS` exige `ar_validated=True` pour sortir de quarantaine. C'est voulu.
5. **Contrôle final** : `ar_coverage()` doit remonter **299 items actifs** avec `ar_validated=True`.

**Ce que débloque cette signature** : réactivation des 15 items → banque fractions complète pour le pilote.

---

## Signature

| | |
|---|---|
| **Nom de la linguiste** | ____________________________________________ |
| **Date** | ____________________ |
| **Items validés tels quels** | ______ / 15 |
| **Items corrigés** | ______ / 15 |
| **Verdict** | ☐ Les 15 propositions sont exploitables ☐ Exploitables après mes corrections ☐ À refaire |
| **Signature** | ____________________________________________ |

*Les propositions de ce document sont des traductions machine relues, non validées. Aucune n'est « validée linguiste » tant que `ar_validated=True` n'a pas été posé par vous via `validate_arabic()`.*
