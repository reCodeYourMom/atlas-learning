# Spécification des générateurs déterministes — Décimaux (Livrable A5)

**Version** : DRAFT v0.2 (harmonisée avec le catalogue A4 livré) · **Date** : 2026-07-12 · **Auteur** : cadrage produit (Nassim + Claude)
**Livrable** : A5 du `01_strategie/Cadrage-LotA-Extension-Contenu.md` (§3/A5, errata E6).
**À lire avec** :
- `02_technique/Architecture-Matiere-Pluggable.md` — le contrat que ce document instancie ;
- `03_referentiel/referentiel_decimals_draft.json` — A3, les 14 compétences cibles (priors de nœud utilisés ci-dessous) ;
- `03_referentiel/Misconceptions-Decimaux.md` — A4 **livré**, catalogue `MC-*`/`D-*` : ses §3 (notation), §4 (specs par compétence) et §5 (règles communes) sont **contractuels** pour ce document ;
- `04_code/src/items/deterministic.py` — l'implémentation fractions dont ce module est le **miroir exact** ;
- `04_code/src/items/difficulty.py` — couche générique, **inchangée**.

**Statut** : spécification exécutable par un dev + un expert (niveau exigé par la DoD du Lot A).
Les poids de complexité sont **indicatifs, experts, non calibrés** — ré-estimation empirique en Lot C.

**Changelog v0.1 → v0.2** : les références de distracteurs pointent désormais vers le catalogue A4 livré
(`Misconceptions-Decimaux.md`, familles `MC-*` et specs `D-*`) au lieu de la taxonomie provisoire M1–M12 ;
les règles communes A4 §5 (collision, paires diagnostiques, traçabilité) sont absorbées en §2 ;
l'exemple `SUB_DECIMALS` est aligné sur `D-SUB-02`/`D-SUB-03`. Les 14 exemples chiffrés et leurs
calculs de complexité sont inchangés (re-vérifiés numériquement contre `weighted_score` le 2026-07-12).

---

## 1. Conformité au contrat « matière pluggable »

`Architecture-Matiere-Pluggable.md` impose, pour brancher un domaine, **trois choses — rien d'autre** :
générateurs de contenu, extracteur de features, fonction de complexité. Le présent document
spécifie ces trois livrables pour les décimaux, en nommage miroir de la matière fractions :

| Contrat (générique) | Fractions (`src/items/deterministic.py`) | Décimaux (ce document → `src/items/decimals.py`) |
|---|---|---|
| Générateurs `{stem, options, answer}` | `GENERATORS` | `DECIMAL_GENERATORS` |
| `features(content) → context_tags` | `fraction_features(code, content)` | `decimal_features(code, content)` |
| Poids (savoir-métier) | `FRACTION_FEATURE_WEIGHTS` | `DECIMAL_FEATURE_WEIGHTS` |
| `complexity(features) → [0,1]` | `fraction_complexity(feats)` | `decimal_complexity(feats)` |

**Ce qui ne change pas** (et que ce module n'a PAS le droit de toucher) :
- `src/items/difficulty.py` : `difficulty_from_score(base, complexity, band=250)` et `weighted_score(features, weights)` sont consommés tels quels.
- Le modèle `Item` / `ItemContent` (`stem: str`, `options: List[str]` pour MCQ, `answer: str` ; `extra="allow"` — ce qui permet la métadonnée de traçabilité §2.5 sans migration).
- Le workflow de revue/validation AR/quarantaine, la sélection d'items, le moteur Elo.
- La formule de dérivation : `prior_item = prior_compétence + (decimal_complexity − 0.5) × 2 × 250`,
  arrondi à 0.1, borné à ± 250 du prior de compétence (et à l'échelle globale [0, 4000]).

**Module cible** : `src/items/decimals.py`. Registre par décorateur, identique au module fractions :

```python
DECIMAL_GENERATORS: Dict[str, Callable[[], List[dict]]] = {}

def _register(code: str):
    def deco(fn):
        DECIMAL_GENERATORS[code] = fn
        return fn
    return deco
```

Fonctions d'accès miroir : `generate_for(code, count=0)`, `all_codes()`,
`bank_items(code, base_prior)` (assemble `content + context_tags + difficulty_prior` par item).

*Note de signature* : le cadrage écrit `decimal_features(content)` ; le miroir exact de
`fraction_features(code, content)` impose de conserver le paramètre `code` (réservé aux surcharges
par compétence, non utilisé par l'extraction de base) — même parité de signature que les fractions.

---

## 2. Règles transverses de génération

### 2.1 Arithmétique exacte : `decimal.Decimal`, JAMAIS de `float`

Toute valeur numérique d'item est construite et calculée en `decimal.Decimal` **instancié depuis une chaîne**
(`Decimal("2.5")`, jamais `Decimal(2.5)` ni littéral flottant). Motif : `0.1 + 0.2 == 0.30000000000000004`
en float ; pire, `round(3.45, 1) == 3.4` en float (représentation binaire + arrondi bancaire) —
exactement le genre d'item qui détruirait la garantie « correction calculée, jamais devinée ».

Règles :
- **Addition/soustraction/multiplication** : `Decimal` natif (exact par construction).
- **Division** : uniquement quand le quotient est exact (vérification par construction des données,
  ex. dividende multiple du diviseur à la précision voulue). Jamais de quotient périodique dans un MCQ décimal.
- **Arrondi** : `Decimal.quantize(exp, rounding=ROUND_HALF_UP)` — convention scolaire explicite
  (le « 5 à la frontière » monte). Interdiction de `round()` builtin sur autre chose qu'un `Decimal`.
- **Affichage** : helper `ds(x: Decimal) -> str` — notation positionnelle via `format(x, "f")`
  (jamais de notation scientifique : piège connu, `Decimal("360").normalize()` → `3.6E+2`),
  zéros terminaux retirés **sauf** quand le piège pédagogique exige de les garder (ex. « 0.50 »,
  « 3.600 ») — dans ce cas le générateur passe la chaîne littérale voulue.
- Les `concat(…)` des specs A4 (§3 de `Misconceptions-Decimaux.md`) sont des opérations de chaîne
  relues via `Decimal(str)` — même discipline anti-float que les valeurs correctes.

### 2.2 Assemblage MCQ : miroir de `_mcq`, dédup par VALEUR exacte

Le module réutilise la logique `_mcq(stem, correct, distractors, salt)` du module fractions
(3 à 4 options, rotation déterministe `salt % len(opts)` pour varier la position de la réponse),
avec un parseur de valeur `_dvalue(s)` étendu : il reconnaît les décimaux (`"2.85"`), les entiers
et les fractions (`"n/d"`), et normalise tout en `Fraction` exacte. Conséquence :
- `"0.50"` et `"0.5"` sont la même valeur → jamais ensemble dans une liste d'options
  (sauf item dont la QUESTION est précisément l'égalité 0.5 = 0.50, où la comparaison redevient
  **textuelle** — règle A4 §5.1, cas `D-RWD-03`, `D-CMP-03`, `D-P10-01`) ;
- pour `DECIMAL_AS_FRACTION`, `"5/10"` ou `"50/100"` sont rejetés comme distracteurs de `"1/2"`
  (même valeur) — le rejet par valeur traverse les représentations (garde-fou A4 §4.4).

**Collision et régénération (A4 §5.1)** : un distracteur de même valeur que la réponse est écarté
(comme le filtre fractions) ; mais quand la spec `D-*` l'exige via ses « contraintes d'opérandes »,
on **régénère les opérandes** plutôt que d'écarter — le codage de la misconception prime sur la
commodité du tirage. Exemple : `D-ADD-01` (alignement à droite) impose `p(x) ≠ p(y)`, sinon la
procédure erronée produit la bonne réponse et ne diagnostique rien.

### 2.3 Distracteurs = catalogue A4 (`Misconceptions-Decimaux.md`)

Chaque distracteur est **calculé** (procédure erronée codée en dur, jamais arbitraire) et référencé
au catalogue A4 livré : 20 familles `MC-*` sourcées en didactique, 50 specs `D-{SKILL}-{nn}` couvrant
les 14 compétences (≥ 3 par compétence). Les specs `D-*` — formules de construction ET contraintes
d'opérandes — sont la source de vérité ; ce document ne les recopie pas, il les **instancie** par
générateur (§3) et n'en cite que les identifiants.

Familles mobilisées ici : `MC-L`, `MC-S` (longer/shorter-is-larger), `MC-ZERO` (comportement du zéro),
`MC-2INT` (décimal lu comme deux entiers), `MC-MIRROR` (symétrie miroir des places), `MC-DIGIT`
(chiffre nu), `MC-FRACLINK` (liaison fraction↔décimal), `MC-ALIGN` (alignement à droite), `MC-BUGSUB`
(bugs d'emprunt), `MC-TRUNC`, `MC-CARRY`, `MC-ADD0` (« ×10 ajoute un zéro »), `MC-SHIFT` (décalage de
virgule), `MC-SEP` (parties opérées séparément), `MC-MULTBIG`, `MC-DIVSMALL`, `MC-REST`, `MC-PLACES`,
`MC-DENSE`, `MC-MONEY`.

**Continuité v0.1** : la taxonomie provisoire M1–M12 de la v0.1 de ce document est absorbée par le
catalogue A4 — M1→`MC-L`, M2→`MC-S`, M3→`MC-ZERO`/`MC-ADD0`, M4→`MC-ALIGN`, M5→`MC-2INT`,
M6→`MC-MULTBIG`, M7→`MC-PLACES`, M8→`MC-FRACLINK`, M9→`MC-2INT` (variante calculatoire),
M10→`MC-BUGSUB`, M11→`MC-SHIFT`, M12→`MC-TRUNC`/`MC-REST`. Toute référence M* résiduelle est caduque.

**Attribution corrigée** : l'errata A4 §4.6 corrige le noyau du cadrage (l'exemple « 0.3 < 0.25 »
relève de `MC-L`, pas de `MC-S` ; l'archétype S est « 0.3 > 0.45 »). Les générateurs de ce document
suivent l'attribution corrigée.

**Paires diagnostiques (A4 §5.3, principe DCT)** : les opérandes ne sont pas tirés au hasard puis
habillés — ils sont **contraints pour que chaque règle erronée diverge de la bonne réponse** (et,
autant que possible, que deux règles erronées divergent entre elles). Un item où *longer-is-larger*
donne la bonne réponse ne détecte pas *longer-is-larger*. Les colonnes « Contrainte » des specs
`D-*` sont partie intégrante de la présente spec, pas des options.

**Cible** : 3 distracteurs par MCQ, chacun tagué d'au moins un `MC-*`. Si le catalogue de la
compétence ne fournit que 2 distracteurs valides pour les opérandes tirés, compléter par un
distracteur de magnitude (`shift(correct, ±1)`) tagué `MC-SHIFT` — jamais par du bruit aléatoire
(règle A4 §5.2). Le taux d'attractivité de chaque distracteur est suivi en analyse d'items (Lot C4,
seuils et actions : A4 §6).

### 2.4 Autres invariants

- **1 item = 1 compétence** (strict, gate G2). Un item de `ADD_DECIMALS` ne teste pas l'arrondi.
- **~10 items par générateur** (volumétrie A7 : 14 × 10 × 2 langues ≈ 280 items), données en dur
  (listes de tuples, comme les fractions) — déterminisme total, pas de RNG.
- **Difficultés étalées** : les données de chaque générateur doivent couvrir une plage de complexité
  large (viser ≥ 200 points Elo d'étendue intra-compétence) — c'est la matière première de
  l'adaptativité intra-compétence (cf. Architecture-Matiere-Pluggable §« objet adaptatif »).
- Items « visuels » (droite numérique, modèle monétaire) : rendus vérifiables par description
  verbale du modèle, comme les fractions (`NUMBER_LINE_PLACE`).
- L'EN est la source ; l'AR suit le plan A6 (glossaire MSA, chiffres 0–9 et point décimal — errata E7).

### 2.5 Traçabilité des distracteurs (A4 §5.5)

Chaque option générée transporte sa métadonnée : `distractor_id` (`D-…-nn`) et
`misconception_ids: ["MC-…", …]`, portées dans le `content` via le champ additionnel
`distractor_meta` (permis par `extra="allow"` d'`ItemContent` — aucun changement du modèle générique).
La rotation `_mcq(salt)` doit **préserver le mapping option→tags**. Quand deux formules coïncident
sur les opérandes tirés (ex. `D-MDD-01`/`D-MDD-02`), l'option porte **tous** les tags ; la
désambiguïsation se fait au niveau cohorte (A4 §6.1). C'est le prérequis du monitoring
d'attractivité C4 et du rapport enseignant par misconception.

---

## 3. `DECIMAL_GENERATORS` — un générateur par compétence (14)

Pour chaque générateur : signature, types d'items (couvrant les `item_contexts` du draft A3),
contraintes de génération, distracteurs (référencés `D-*`/`MC-*` du catalogue A4), **un exemple EN
produit**, l'extraction de features sur cet exemple, le calcul de `decimal_complexity` et le
`prior_item` résultant.

Rappel des formules utilisées dans tous les calculs ci-dessous (cf. §4–§5 pour les définitions) :
`c = weighted_score(norm, DECIMAL_FEATURE_WEIGHTS)` (normalisé sur les features présentes),
`prior_item = round(prior_compétence + (c − 0.5) × 2 × 250, 1)`.

---

### 3.1 `MATH.G4.NBT.PLACE_VALUE_TENTHS` — prior 1520 (RECALL)

```python
@_register("MATH.G4.NBT.PLACE_VALUE_TENTHS")
def _pv_tenths() -> List[dict]: ...
```

**Types d'items** (contexts A3 : identify digit place / tenths as 1/10 / expanded form / money model) :
identifier le chiffre des dixièmes ; « quelle est la valeur du chiffre d ? » (d/10) ; forme développée
(`3.7 = 3 + 7/10`) ; modèle monétaire dirhams/fils (`D-PVT-04`, `MC-MONEY`).

**Contraintes** : nombres à exactement 1 décimale, `Decimal(str)` ; chiffre des dixièmes ≠ 0 et
≠ chiffre des unités (pas d'ambiguïté de lecture) ; partie entière ∈ [1, 9] pour la famille de base ;
famille haute avec ≥ 2 chiffres entiers et `digit_tens(x) ≠ digit(x,1)` (contrainte `D-PVT-01`).

**Distracteurs** : chiffre des unités — et, sur la famille haute, chiffre des **dizaines**
(`D-PVT-01`, `MC-MIRROR`) ; la valeur `0.d` au lieu du chiffre (confusion chiffre/valeur, réciproque
de `D-PVT-02`, `MC-DIGIT` ; en *expanded form* : `d × 10`, `D-PVT-03`) ; lecture entière `ud`
(`MC-2INT`).

**Exemple** :
- stem : `In the number 3.7, which digit is in the tenths place?`
- options : `["7", "3", "0.7", "70"]` · answer : `"7"`
  (tags : `3` → `MC-MIRROR` [place adjacente] ; `0.7` → `MC-DIGIT` ; `70` → `MC-2INT`)

**Features** : `{decimal_places: 1, zero_trap: false, max_value: 3.7}`
**Normalisation** : `places_norm = 1/3 ≈ 0.3333` (poids 0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 3.7/100 = 0.037` (0.10). Poids présents = 0.45.
**Complexité** : `c = (0.25×0.3333 + 0.10×0 + 0.10×0.037) / 0.45 = 0.0870 / 0.45 = 0.1934`
**Prior item** : `1520 + (0.1934 − 0.5) × 500 = 1520 − 153.3 = **1366.7**`

*Leviers de variation vers le haut* : magnitude (dizaines : 47.3, active `D-PVT-01` plein),
forme développée, registre monétaire (`D-PVT-04`).

---

### 3.2 `MATH.G4.NBT.PLACE_VALUE_HUNDREDTHS` — prior 1580 (APPLY)

```python
@_register("MATH.G4.NBT.PLACE_VALUE_HUNDREDTHS")
def _pv_hundredths() -> List[dict]: ...
```

**Types d'items** (identify digit place / hundredths as 1/100 / expanded form / zero as placeholder) :
identifier le chiffre des centièmes ; valeur d/100 ; forme développée ; **zéro intercalaire**
(`4.05` — le levier de difficulté propre à cette compétence, `D-PVH-02`).

**Contraintes** : 2 décimales exactement ; une moitié des données avec zéro intercalaire ou terminal ;
chiffres dixièmes/centièmes distincts (contrainte `D-PVH-01` : `digit(x,1) ≠ digit(x,2)`).

**Distracteurs** : chiffre des dixièmes (`D-PVH-01`, `MC-MIRROR` — attractivité maximale quand le
zéro intercalaire est présent), chiffre des unités, valeur `0.0d` au lieu du chiffre (`MC-DIGIT`) ;
en *expanded form* : tous les chiffres sur 10 (`D-PVH-03`, `MC-DIGIT`) ; en écriture :
« 5 centièmes » → 0.5 (`D-PVH-02`, `MC-ZERO`).

**Exemple** :
- stem : `In the number 4.05, which digit is in the hundredths place?`
- options : `["5", "0", "4", "0.05"]` · answer : `"5"`
  (tags : `0` → `MC-MIRROR` [`D-PVH-01`] ; `4` → `MC-MIRROR` [unités] ; `0.05` → `MC-DIGIT`)

**Features** : `{decimal_places: 2, zero_trap: true, max_value: 4.05}`
**Normalisation** : `places_norm = 2/3 ≈ 0.6667` (0.25) ; `zero_trap = 1` (0.10) ; `magnitude_norm = 0.0405` (0.10). Poids présents = 0.45.
**Complexité** : `c = (0.1667 + 0.10 + 0.0041) / 0.45 = 0.6016`
**Prior item** : `1580 + (0.6016 − 0.5) × 500 = 1580 + 50.8 = **1630.8**`

---

### 3.3 `MATH.G4.NBT.READ_WRITE_DECIMAL` — prior 1600 (APPLY)

```python
@_register("MATH.G4.NBT.READ_WRITE_DECIMAL")
def _read_write_decimal() -> List[dict]: ...
```

**Types d'items** (words to numeral / numeral to words / trailing zero 0.5 vs 0.50 / money notation) :
dictée verbale → écriture chiffrée ; écriture chiffrée → mots (piège de la lecture « deux entiers »,
`D-RWD-01`) ; équivalence d'écritures (`0.5` = `0.50`, `D-RWD-03` en stem) ; notation monétaire.

**Contraintes** : la formulation verbale EN suit la convention scolaire « six and thirty-two hundredths »
(le mot-place est la vérité de la position) ; réponses générées par `Decimal(str)` ; pour les items
`D-RWD-03`, les zéros terminaux sont affichés littéralement (§2.1) et la comparaison de collision est
textuelle (§2.2) ; les items mots→nombre à zéro cache-place respectent la contrainte `D-RWD-02`
(`b̄` commence par 0).

**Distracteurs** : mauvaise place (`thirty-two` posé aux millièmes → `6.032`, rang confondu,
`MC-MIRROR`), virgule ignorée (`632`, `MC-2INT`), virgule décalée (`63.2`, `MC-SHIFT`) ;
sur les items à zéro cache-place : zéro omis (`3.05` → `3.5`, `D-RWD-02`, `MC-ZERO`).

**Exemple** :
- stem : `Write "six and thirty-two hundredths" as a decimal number.`
- options : `["6.32", "6.032", "632", "63.2"]` · answer : `"6.32"`
  (tags : `6.032` → `MC-MIRROR` ; `632` → `MC-2INT` ; `63.2` → `MC-SHIFT`)

**Features** — *règle de repli* : le stem ne contient aucun nombre (dictée verbale) → extraction sur
`content["answer"]` (§4). `{decimal_places: 2, zero_trap: false, max_value: 6.32}`
**Normalisation** : `places_norm = 0.6667` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.0632` (0.10). Poids présents = 0.45.
**Complexité** : `c = (0.1667 + 0 + 0.0063) / 0.45 = 0.3844`
**Prior item** : `1600 + (0.3844 − 0.5) × 500 = 1600 − 57.8 = **1542.2**`

---

### 3.4 `MATH.G4.NBT.DECIMAL_AS_FRACTION` — prior 1660 (REASON)

```python
@_register("MATH.G4.NBT.DECIMAL_AS_FRACTION")
def _decimal_as_fraction() -> List[dict]: ...
```

**Types d'items** (tenths / hundredths / simplifiable 0.5 = 1/2 / greater than one 1.25) :
décimal → fraction (réduite ou sur 10/100), fraction → décimal (`D-DAF-01`), cas > 1
(`1.25 = 5/4` ou `1 1/4`, `D-DAF-04`). Compétence-pont (3 arêtes HARD entrantes depuis les
fractions) : distracteurs doublement diagnostiques (faille fractions vs faille décimaux).

**Contraintes** : la vérité est établie par conversion exacte `Fraction(Decimal("0.5")) == Fraction(1, 2)` ;
seuls des dénominateurs 10/100 (et leurs réduits) sont utilisés — pas de tiers périodiques.
Le dédup par valeur (§2.2) est critique ici : `5/10`, `50/100` sont REJETÉS comme distracteurs de
`1/2` — sauf si la consigne exige explicitement la forme irréductible (garde-fou A4 §4.4).
Contrainte `D-DAF-02` : `d ≥ 2`.

**Distracteurs** : association réciproque `0.d → 1/d` (`D-DAF-02`, `MC-FRACLINK` — réciproque du
« 1/2 = 0.2 » du noyau, `D-DAF-01`), puissance de dix erronée (`5/100`, `D-DAF-03`, `MC-FRACLINK`),
inversion numérateur/dénominateur (`5/1`, complément tagué `MC-FRACLINK`) ; cas > 1 : partie entière
absorbée (`1.25 → 25/100`, `D-DAF-04`, `MC-2INT`).

**Exemple** :
- stem : `Write 0.5 as a fraction in lowest terms.`
- options : `["1/2", "1/5", "5/100", "5/1"]` · answer : `"1/2"`
  (tags : `1/5` → `MC-FRACLINK` [`D-DAF-02`] ; `5/100` → `MC-FRACLINK` [`D-DAF-03`] ; `5/1` → `MC-FRACLINK`)

**Features** : `{decimal_places: 1, zero_trap: false, max_value: 0.5}`
**Normalisation** : `places_norm = 0.3333` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.005` (0.10). Poids présents = 0.45.
**Complexité** : `c = (0.0833 + 0 + 0.0005) / 0.45 = 0.1863`
**Prior item** : `1660 + (0.1863 − 0.5) × 500 = 1660 − 156.9 = **1503.1**`

*Leviers* : centièmes simplifiables (`0.75 → 3/4`), cas > 1 (`D-DAF-04`), sens fraction → décimal
(`D-DAF-01` : `1/2 → 0.2` et `1.2`).

---

### 3.5 `MATH.G4.NBT.DECIMAL_NUMBER_LINE` — prior 1640 (APPLY)

```python
@_register("MATH.G4.NBT.DECIMAL_NUMBER_LINE")
def _decimal_number_line() -> List[dict]: ...
```

**Types d'items** (tenths line / hundredths zoom / between two marks / estimate position) :
droite décrite verbalement (même convention vérifiable que `NUMBER_LINE_PLACE` fractions) ;
zoom centièmes (droite de 0.3 à 0.4 en 10 intervalles) ; encadrement entre deux graduations
(`D-DNL-03`, `MC-DENSE` : « aucun nombre entre 0.3 et 0.4 »).

**Contraintes** : la position est calculée en `Decimal` (`k × pas`), le pas étant `0.1` ou `0.01`
exactement ; jamais de position estimée non calculable ; contraintes `D-DNL-01` (`shift(x, ±1)`
doit tomber sur la ligne) et `D-DNL-02` (`b̄ ≠ reverse(b̄)`).

**Distracteurs** : confusion d'échelle ×10 (`0.07` pour `0.7`, `D-DNL-01`, `MC-SHIFT`), lecture
entière du rang (`7`, `MC-2INT`), décalage d'une graduation (« off-by-one », complément §2.3) ;
lecture miroir des décimales sur le zoom centièmes (`0.35` placé en `0.53`, `D-DNL-02`, `MC-MIRROR`).

**Exemple** :
- stem : `A number line from 0 to 1 is split into 10 equal intervals. What number is at the 7th tick after 0?`
- options : `["0.7", "0.07", "7", "0.8"]` · answer : `"0.7"`
  (tags : `0.07` → `MC-SHIFT` [`D-DNL-01`] ; `7` → `MC-2INT` ; `0.8` → complément off-by-one)

**Features** — repli sur `answer` (aucun décimal dans le stem) : `{decimal_places: 1, zero_trap: false, max_value: 0.7}`
**Normalisation** : `places_norm = 0.3333` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.007` (0.10). Poids présents = 0.45.
**Complexité** : `c = (0.0833 + 0 + 0.0007) / 0.45 = 0.1867`
**Prior item** : `1640 + (0.1867 − 0.5) × 500 = 1640 − 156.6 = **1483.4**`

*Leviers* : zoom centièmes (2 décimales), bornes non entières (droite 2.3 → 2.4), items `MC-DENSE`.

---

### 3.6 `MATH.G4.NBT.COMPARE_DECIMALS` — prior 1700 (REASON)

```python
@_register("MATH.G4.NBT.COMPARE_DECIMALS")
def _compare_decimals() -> List[dict]: ...
```

**Types d'items** (same number of places / different places = longer-is-larger trap / trailing zero
trap / ordering 3+) : comparaison à 2 nombres (même nombre de places, puis places différentes),
piège du zéro terminal (`0.7` vs `0.70`, `D-CMP-03`), ordonnancement de 3 nombres
(options = permutations, `D-CMP-05`).

**Contraintes — paires diagnostiques (le cœur du DCT, A4 §4.6 et §5.3)** : la vérité est la
comparaison `Decimal` exacte ; les données à places différentes sont construites pour que `MC-L`
ET `MC-S` produisent chacun une réponse fausse identifiable — paire L : `p(x) > p(y)` et `x < y`
(`D-CMP-01`, ex. 0.45 vs 0.5) ; paire S : `p(x) < p(y)` et `x < y` (`D-CMP-02`, ex. 0.3 vs 0.45) ;
les items « trailing zero » posent l'égalité comme option correcte possible ; ordering : triple
divergence exigée entre tri correct, tri L (`strip()` croissant) et tri S (`p()` décroissant).

**Distracteurs** : le perdant du piège L (`D-CMP-01`, `MC-L` : 0.45 déclaré > 0.5) ou S (`D-CMP-02`,
`MC-S`), « They are equal » (neutralise le hasard ; diagnostique `MC-ZERO` sur les items à zéro
terminal, `D-CMP-03`, et `MC-MONEY` sur les paires tronquées, `D-CMP-04`), lecture « deux entiers »
sur les items type `3.12` vs `3.5` (`MC-2INT`).

**Exemple** :
- stem : `Which is greater: 0.5 or 0.45?`
- options : `["0.5", "0.45", "They are equal"]` · answer : `"0.5"`
  (tags : `0.45` → `MC-L` [`D-CMP-01`] ; `They are equal` → `MC-ZERO`)

**Features** : `{decimal_places: 2, alignment_gap: 1, zero_trap: false, max_value: 0.5}`
(comparaison à places différentes → `alignment_gap` émis, cf. §4)
**Normalisation** : `places_norm = 0.6667` (0.25) ; `alignment_norm = min(1,2)/2 = 0.5` (0.20) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.005` (0.10). Poids présents = 0.65.
**Complexité** : `c = (0.1667 + 0.10 + 0 + 0.0005) / 0.65 = 0.4110`
**Prior item** : `1700 + (0.4110 − 0.5) × 500 = 1700 − 44.5 = **1655.5**`

---

### 3.7 `MATH.G5.NBT.PLACE_VALUE_THOUSANDTHS` — prior 1820 (APPLY)

```python
@_register("MATH.G5.NBT.PLACE_VALUE_THOUSANDTHS")
def _pv_thousandths() -> List[dict]: ...
```

**Types d'items** (identify digit place / adjacent places ×10 relation / expanded form / zero as
placeholder) : identifier le chiffre des millièmes ; relation entre places adjacentes
(« le 4 de 0.4 vaut combien de fois le 4 de 0.04 ? » → 10, `D-PVM-01`) ; forme développée à 3
places ; zéros intercalaires (`D-PVM-03`).

**Contraintes** : 3 décimales exactement ; les items « relation ×10 » comparent le même chiffre à
deux places (réponse ∈ {10, 100, 1/10, 1/100} exacts) ; famille miroir avec ≥ 4 chiffres entiers et
`digit_thousands(x) ≠ digit(x,3)` (contrainte `D-PVM-02`).

**Distracteurs** : chiffre des centièmes (place adjacente, `MC-MIRROR`), chiffre des dixièmes,
partie décimale lue comme entier (`407`, `MC-2INT`) ; items relation ×10 : `1/10` (inversion) et
`100` (saut de rang) (`D-PVM-01`, `MC-MIRROR`) ; millièmes ↔ milliers (`D-PVM-02`) ;
« 52 centièmes » pour 0.052 (`D-PVM-03`, `MC-ZERO`).

**Exemple** :
- stem : `In the number 2.407, which digit is in the thousandths place?`
- options : `["7", "0", "4", "407"]` · answer : `"7"`
  (tags : `0` → `MC-MIRROR` [centièmes] ; `4` → `MC-MIRROR` [dixièmes] ; `407` → `MC-2INT`)

**Features** : `{decimal_places: 3, zero_trap: true, max_value: 2.407}` (zéro intercalaire présent)
**Normalisation** : `places_norm = 3/3 = 1.0` (0.25) ; `zero_trap = 1` (0.10) ; `magnitude_norm = 0.0241` (0.10). Poids présents = 0.45.
**Complexité** : `c = (0.25 + 0.10 + 0.0024) / 0.45 = 0.7831`
**Prior item** : `1820 + (0.7831 − 0.5) × 500 = 1820 + 141.6 = **1961.6**`

---

### 3.8 `MATH.G5.NBT.ADD_DECIMALS` — prior 1840 (APPLY)

```python
@_register("MATH.G5.NBT.ADD_DECIMALS")
def _add_decimals() -> List[dict]: ...
```

**Types d'items** (same places / different places = alignment / carrying / crossing a whole / money) :
addition même nombre de places ; places différentes (alignement requis) ; avec retenue ;
traversée d'unité (`0.75 + 0.68`) ; habillage monétaire (AED).

**Contraintes** : somme exacte `Decimal + Decimal` ; les données couvrent les 4 croisements
{alignement requis ou non} × {retenue ou non} pour étaler la difficulté ; contrainte `D-ADD-01` :
`p(x) ≠ p(y)` sur les items visant `MC-ALIGN` (sinon la formule erronée donne la bonne réponse).

**Distracteurs (calculés)** :
- `D-ADD-02` (`MC-SEP`/`MC-2INT`) : parties additionnées séparément — `concat(a+c, ".", b+d)`
  (`2.5 + 0.35` → `2.40`, le distracteur du noyau A4) ; en régime *crossing a whole*
  (`b + d ≥ 10^max(p)`), la même formule produit la non-traversée de l'unité → double tag `MC-CARRY` ;
- `D-ADD-01` (`MC-ALIGN`) : tout aligné à droite, virgule replacée au max des places
  (`shift(strip(x)+strip(y), −max(p))` : `25+35=60` → `0.60`) ;
- `D-ADD-03` (`MC-DIGIT`) : virgule perdue (`strip(x+y)` : `285`) — réservé aux items *money* ;
  hors money, complément `MC-SHIFT` (`28.5`).

**Exemple** :
- stem : `What is 2.5 + 0.35?`
- options : `["2.85", "2.40", "0.60", "28.5"]` · answer : `"2.85"`
  (tags : `2.40` → `MC-SEP`, `MC-2INT` [`D-ADD-02`] ; `0.60` → `MC-ALIGN` [`D-ADD-01`] ; `28.5` → `MC-SHIFT`)

**Features** : `{decimal_places: 2, alignment_gap: 1, carry: false, zero_trap: false, crosses_unit: false, max_value: 2.5, operation: "add"}`
(retenue : test colonne par colonne sur les opérandes quantifiés à 2 décimales — `2.50 + 0.35`,
aucune colonne ≥ 10 ; traversée : `floor(2.85) == floor(2.5)` → false)
**Normalisation** : `places_norm = 0.6667` (0.25) ; `alignment_norm = 0.5` (0.20) ; `carry_borrow = 0` (0.15) ; `zero_trap = 0` (0.10) ; `crosses_unit = 0` (0.10) ; `magnitude_norm = 0.025` (0.10). Poids présents = 0.90.
**Complexité** : `c = (0.1667 + 0.10 + 0 + 0 + 0 + 0.0025) / 0.90 = 0.2991`
**Prior item** : `1840 + (0.2991 − 0.5) × 500 = 1840 − 100.5 = **1739.5**`

*Leviers* : retenue + traversée d'unité (`0.75 + 0.68 = 1.43` → c ≈ 0.46), magnitude monétaire.

---

### 3.9 `MATH.G5.NBT.ROUND_DECIMAL` — prior 1860 (APPLY)

```python
@_register("MATH.G5.NBT.ROUND_DECIMAL")
def _round_decimal() -> List[dict]: ...
```

**Types d'items** (to nearest whole / to tenths / to hundredths / digit 5 at boundary) :
arrondi à l'unité, au dixième, au centième ; cas frontière « chiffre 5 » (`D-RND-03`).

**Contraintes** : `Decimal.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)` — OBLIGATOIRE.
C'est LE générateur où le float est interdit de manière démontrable : `round(3.45, 1)` float → `3.4`
(binaire + arrondi bancaire) alors que la convention scolaire exige `3.5`. Contrainte `D-RND-01` :
`digit(x, p+1) ≥ 5` (sinon troncature = arrondi, collision → régénérer). Tag de contexte
`round_boundary_5: true` sur les cas frontière (non pondéré, exploitable en analyse).

**Distracteurs** : troncature (`D-RND-01`/`D-RND-03`, `MC-TRUNC` : `3.4`), rang confondu — arrondi
un rang trop tôt/trop tard (`D-RND-02`, `MC-MIRROR` : `3`), non-opération (`3.45`, complément) ;
familles hautes : retenue non propagée à la frontière (`3.96` → « 3.10 », `D-RND-04`, `MC-CARRY`),
double arrondi (`0.148 → 0.15 → 0.2`, `D-RND-05`, `MC-CARRY`).

**Exemple** :
- stem : `Round 3.45 to the nearest tenth.`
- options : `["3.5", "3.4", "3", "3.45"]` · answer : `"3.5"`
  (tags : `3.4` → `MC-TRUNC` [`D-RND-03`] ; `3` → `MC-MIRROR` [`D-RND-02`] ; `3.45` → complément non-opération)

**Features** : `{decimal_places: 2, zero_trap: false, max_value: 3.45, round_boundary_5: true}`
**Normalisation** : `places_norm = 0.6667` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.0345` (0.10). Poids présents = 0.45.
**Complexité** : `c = (0.1667 + 0 + 0.0035) / 0.45 = 0.3780`
**Prior item** : `1860 + (0.3780 − 0.5) × 500 = 1860 − 61.0 = **1799.0**`

---

### 3.10 `MATH.G5.NBT.SUB_DECIMALS` — prior 1880 (APPLY)

```python
@_register("MATH.G5.NBT.SUB_DECIMALS")
def _sub_decimals() -> List[dict]: ...
```

**Types d'items** (same places / different places = alignment / borrowing / from a whole 3 − 0.45 /
money change) : soustraction même places ; alignement requis ; avec emprunt ; **depuis un entier**
(le cas le plus discriminant) ; rendu de monnaie.

**Contraintes** : différence exacte `Decimal − Decimal`, résultat ≥ 0 ; les données « from a whole »
imposent la chaîne d'emprunts complète ; contraintes `D-SUB-01` : `p(x) ≠ p(y)` et
`strip(x) > strip(y)` sur les items visant `MC-ALIGN`.

**Distracteurs (calculés)** :
- `D-SUB-02` (`MC-BUGSUB` *smaller-from-larger*) : colonne par colonne, `|digit_x − digit_y|` sans
  emprunt après alignement et padding (`3.00 − 0.45` → `3.45`) ;
- `D-SUB-03` (`MC-BUGSUB` *borrow-no-decrement*) : décimales justes, entier non décrémenté —
  `concat(a−c, ".", 10^m − d)` (`3.00 − 0.45` → `3.55`) ;
- emprunt sur-propagé (`2.45`, complément tagué `MC-BUGSUB`) ;
- sur les items à places différentes hors « from a whole » : `D-SUB-01` (`MC-ALIGN` :
  `4.7 − 0.24` → `0.23`).

**Exemple** :
- stem : `What is 3 − 0.45?`
- options : `["2.55", "3.45", "3.55", "2.45"]` · answer : `"2.55"`
  (tags : `3.45` → `MC-BUGSUB` [`D-SUB-02`] ; `3.55` → `MC-BUGSUB` [`D-SUB-03`] ; `2.45` → `MC-BUGSUB`)

**Features** : `{decimal_places: 2, alignment_gap: 2, borrow: true, zero_trap: false, crosses_unit: true, max_value: 3, operation: "sub"}`
(`places(3) = 0` pour l'opérande entier → écart d'alignement 2 ; emprunt requis sur `3.00 − 0.45` ;
traversée : `floor(2.55) = 2 ≠ floor(3) = 3`)
**Normalisation** : `places_norm = 0.6667` (0.25) ; `alignment_norm = min(2,2)/2 = 1.0` (0.20) ; `carry_borrow = 1` (0.15) ; `zero_trap = 0` (0.10) ; `crosses_unit = 1` (0.10) ; `magnitude_norm = 0.03` (0.10). Poids présents = 0.90.
**Complexité** : `c = (0.1667 + 0.20 + 0.15 + 0 + 0.10 + 0.003) / 0.90 = 0.6885`
**Prior item** : `1880 + (0.6885 − 0.5) × 500 = 1880 + 94.3 = **1974.3**`

---

### 3.11 `MATH.G5.NBT.MULT_DIV_POW10` — prior 1900 (APPLY)

```python
@_register("MATH.G5.NBT.MULT_DIV_POW10")
def _mult_div_pow10() -> List[dict]: ...
```

**Types d'items** (×10 ×100 ×1000 / ÷10 ÷100 ÷1000 / shift direction reasoning / unit conversion) :
multiplication et division par 10/100/1000 ; raisonnement sur le sens du décalage
(« pour passer de 3.6 à 0.036, on… ») ; conversions d'unités (m ↔ cm, AED ↔ fils).

**Contraintes** : calcul `Decimal × Decimal("100")` exact ; affichage via `ds()` (jamais `3.6E+2`) ;
sur les items ÷, le résultat garde ≤ 3 décimales (borne du domaine) ; contrainte `D-P10-03` :
`k ≥ 2` ; l'option `D-P10-01` est affichée **avec ses zéros** (comparaison textuelle, §2.2).

**Distracteurs** : « ×10 ajoute un zéro » — zéros accolés sans décaler (`D-P10-01`, `MC-ADD0` :
`3.600`), sens du décalage inversé (`D-P10-02`, `MC-SHIFT` : `0.036`), nombre de rangs erroné
(`D-P10-03`, `MC-SHIFT` : `36`).

**Exemple** :
- stem : `What is 3.6 × 100?`
- options : `["360", "3.600", "0.036", "36"]` · answer : `"360"`
  (tags : `3.600` → `MC-ADD0` [`D-P10-01`] ; `0.036` → `MC-SHIFT` [`D-P10-02`] ; `36` → `MC-SHIFT` [`D-P10-03`])

**Features** : `{decimal_places: 1, zero_trap: false, max_value: 100, point_shift: true, operation: "mult"}`
**Normalisation** : `places_norm = 0.3333` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = min(100,100)/100 = 1.0` (0.10) ; `point_shift = 1` (0.10). Poids présents = 0.55.
**Complexité** : `c = (0.0833 + 0 + 0.10 + 0.10) / 0.55 = 0.5152`
**Prior item** : `1900 + (0.5152 − 0.5) × 500 = 1900 + 7.6 = **1907.6**`

---

### 3.12 `MATH.G5.NBT.MULT_DECIMAL_WHOLE` — prior 1920 (APPLY)

```python
@_register("MATH.G5.NBT.MULT_DECIMAL_WHOLE")
def _mult_decimal_whole() -> List[dict]: ...
```

**Types d'items** (single-digit whole / two-digit whole / point placement / estimation check) :
décimal × entier à 1 chiffre, puis 2 chiffres ; items « où va la virgule ? » ; vérification par
estimation (« 0.35 × 4 est proche de… », `D-MDW-03`).

**Contraintes** : produit exact `Decimal × int` ; affichage du résultat normalisé (`1.40` → `1.4`)
sauf item zéro-terminal explicite ; contrainte `D-MDW-01` : le distracteur « parties séparées »
n'est retenu que s'il diffère du produit correct (vérifier, sinon écarter — sa formule est fausse
dès que `b × n ≥ 10^p(x)` ou qu'il y a retenue).

**Distracteurs** : virgule décalée d'un rang dans chaque sens (`D-MDW-02`, `MC-SHIFT` : `14` et
`0.14` — pour cet exemple, `0.14` coïncide avec la formule `MC-SEP`, double tag §2.5), erreur de
fait multiplicatif (`1.2`, complément) ; famille `2.5 × 3` : parties multipliées séparément
(`6.15`, `D-MDW-01`, `MC-SEP`) ; *estimation check* avec `x < 1` : magnitude « rassurante » > n
(`D-MDW-03`, `MC-MULTBIG`).

**Exemple** :
- stem : `What is 0.35 × 4?`
- options : `["1.4", "14", "0.14", "1.2"]` · answer : `"1.4"`
  (tags : `14` → `MC-SHIFT` [`D-MDW-02`] ; `0.14` → `MC-SHIFT`, `MC-SEP` ; `1.2` → complément fait multiplicatif)

**Features** : `{decimal_places: 2, zero_trap: false, max_value: 4, point_shift: true, operation: "mult"}`
**Normalisation** : `places_norm = 0.6667` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.04` (0.10) ; `point_shift = 1` (0.10). Poids présents = 0.55.
**Complexité** : `c = (0.1667 + 0 + 0.004 + 0.10) / 0.55 = 0.4921`
**Prior item** : `1920 + (0.4921 − 0.5) × 500 = 1920 − 3.9 = **1916.1**`

---

### 3.13 `MATH.G5.NBT.DIV_DECIMAL_WHOLE` — prior 1950 (REASON)

```python
@_register("MATH.G5.NBT.DIV_DECIMAL_WHOLE")
def _div_decimal_whole() -> List[dict]: ...
```

**Types d'items** (exact quotient / quotient needs added zero / point placement / sharing model) :
quotient direct exact ; quotient exigeant un zéro poussé (`0.6 ÷ 4 = 0.15`, `D-DDW-02`) ;
placement de virgule ; modèle de partage (habillage : partager 0.6 L entre 4 verres).

**Contraintes** : le quotient est exact PAR CONSTRUCTION (dividende choisi tel que
`Fraction(dividende) / diviseur` ait un dénominateur en 2^a·5^b, ≤ 3 décimales) ; division
réalisée en `Decimal` avec précision suffisante puis vérifiée par re-multiplication exacte
(`quotient × diviseur == dividende`) — garde-fou anti-float dans les tests. Contrainte `D-DDW-01` :
`r ≠ 0` ; contrainte `D-DDW-02` : `x ÷ n` a strictement plus de `p(x)` décimales.

**Distracteurs** : quotient tronqué avant le zéro à pousser (`D-DDW-02`, `MC-TRUNC` : `0.1`),
virgule du quotient décalée ×10 / ÷10 (`D-DDW-04`, `MC-SHIFT` : `1.5` et `0.015`) ;
familles hautes : reste accolé comme décimale (`7.3 ÷ 5` → « 1.43 », `D-DDW-01`, `MC-REST`) ;
quand `x < n` : opérandes inversés et option « impossible » (`D-DDW-03`, `MC-DIVSMALL`).

**Exemple** :
- stem : `What is 0.6 ÷ 4?`
- options : `["0.15", "0.1", "1.5", "0.015"]` · answer : `"0.15"`
  (tags : `0.1` → `MC-TRUNC` [`D-DDW-02`] ; `1.5` → `MC-SHIFT` [`D-DDW-04`] ; `0.015` → `MC-SHIFT` [`D-DDW-04`])

**Features** : `{decimal_places: 1, zero_trap: false, max_value: 4, point_shift: true, operation: "div", quotient_added_zero: true}`
(le tag `quotient_added_zero` est contextuel, non pondéré)
**Normalisation** : `places_norm = 0.3333` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.04` (0.10) ; `point_shift = 1` (0.10). Poids présents = 0.55.
**Complexité** : `c = (0.0833 + 0 + 0.004 + 0.10) / 0.55 = 0.3406`
**Prior item** : `1950 + (0.3406 − 0.5) × 500 = 1950 − 79.7 = **1870.3**`

---

### 3.14 `MATH.G5.NBT.MULT_DECIMAL_DECIMAL` — prior 1960 (REASON)

```python
@_register("MATH.G5.NBT.MULT_DECIMAL_DECIMAL")
def _mult_decimal_decimal() -> List[dict]: ...
```

**Types d'items** (tenths × tenths / counting decimal places / product smaller than factors /
estimation check) : dixièmes × dixièmes ; « combien de décimales au produit ? » ; items dont la
réponse correcte est PLUS PETITE que les deux facteurs (attaque frontale de `MC-MULTBIG`, la
misconception la plus robuste de la littérature — A4 §4.14) ; estimation.

**Contraintes** : produit exact `Decimal × Decimal` (≤ 3 décimales au produit — borne domaine) ;
au moins la moitié des données avec produit < min(facteurs) ; contrainte `D-MDD-03` : opérandes > 1 ;
contrainte `D-MDD-04` : produit brut ≡ 0 mod 10.

**Distracteurs** : comptage des places = max au lieu de la somme (`D-MDD-01`, `MC-PLACES` : `2.4` —
le distracteur du noyau A4 ; sur les facteurs < 1, il coïncide avec `D-MDD-02` `MC-MULTBIG`
« produit rassurant » → double tag §2.5), comptage +1 décimale (`0.024`, `MC-PLACES`),
virgule ignorée (`24`, `MC-2INT`) ; familles hautes : parties multipliées séparément
(`1.2 × 1.3 → 1.6`, `D-MDD-03`, `MC-SEP`), zéro final du produit brut escamoté avant comptage
(`0.5 × 0.4` → « 0.02 », `D-MDD-04`, `MC-PLACES`/`MC-ZERO`).

**Exemple** :
- stem : `What is 0.4 × 0.6?`
- options : `["0.24", "2.4", "0.024", "24"]` · answer : `"0.24"`
  (tags : `2.4` → `MC-PLACES`, `MC-MULTBIG` [`D-MDD-01`+`D-MDD-02`] ; `0.024` → `MC-PLACES` ; `24` → `MC-2INT`)

**Features** : `{decimal_places: 1, zero_trap: false, max_value: 0.6, point_shift: true, operation: "mult", product_smaller_than_factors: true}`
**Normalisation** : `places_norm = 0.3333` (0.25) ; `zero_trap = 0` (0.10) ; `magnitude_norm = 0.006` (0.10) ; `point_shift = 1` (0.10). Poids présents = 0.55.
**Complexité** : `c = (0.0833 + 0 + 0.0006 + 0.10) / 0.55 = 0.3344`
**Prior item** : `1960 + (0.3344 − 0.5) × 500 = 1960 − 82.8 = **1877.2**`

*Leviers* : dixièmes × centièmes (3 décimales au produit), facteurs > 1 mixtes (`1.2 × 0.5`).

---

## 4. `decimal_features(code, content) → context_tags`

Miroir exact de `fraction_features(code, content)` : extraction depuis `content["stem"]`
(regex décimaux `(\d+)\.(\d+)` + entiers isolés), parsing en `Decimal(str)` — jamais float.
Le paramètre `code` est conservé pour parité de signature (réservé aux surcharges par compétence,
non utilisé par l'extraction de base). Les tags sont **porteurs de sens**, lisibles par l'humain,
exploitables par le moteur (patterns de difficulté par contexte, sans fragmenter le graphe — règle A1.6).

**Règle de repli** : si le stem ne contient AUCUN nombre décimal (dictée verbale, droite numérique
décrite en entiers), les features numériques sont extraites de `content["answer"]`.

| context_tag | Type | Émis quand | Définition exacte |
|---|---|---|---|
| `decimal_places` | int | ≥ 1 décimal parsé | max du nombre de décimales des opérandes affichés (opérande entier → 0) |
| `alignment_gap` | int | ≥ 2 nombres ET item d'addition/soustraction/comparaison | max des écarts \|places(a) − places(b)\| entre opérandes |
| `carry` / `borrow` | bool | opération `+` / `−` détectée dans le stem | test colonne par colonne sur les opérandes quantifiés au max des places : une colonne ≥ 10 (add) / nécessitant un emprunt (sub) |
| `zero_trap` | bool | ≥ 1 décimal parsé | un chiffre `0` figure dans la partie décimale affichée d'un opérande (zéro intercalaire `4.05`, `2.407` ou terminal `0.50`) |
| `crosses_unit` | bool | opération `+` / `−` | `floor(résultat) ≠ floor(premier opérande)` (calcul exact `Decimal`) |
| `max_value` | Decimal→float | ≥ 1 nombre parsé | max des valeurs absolues des opérandes |
| `point_shift` | bool | opération `×` / `÷` détectée | l'item exige un placement de virgule (≥ 1 opérande décimal, ou opérande ∈ {10, 100, 1000}) |
| `operation` | str | opérateur détecté | `"add"` / `"sub"` / `"mult"` / `"div"` |
| tags libres | — | selon générateur | `round_boundary_5`, `quotient_added_zero`, `product_smaller_than_factors`, `money_context`… (contextuels, NON pondérés — même statut que `operation` chez les fractions) |

Comme chez les fractions, une feature non pertinente pour la famille d'items est **absente**
(pas `false` par défaut, sauf les booléens réellement évalués) : `weighted_score` renormalise
sur les features présentes — les familles n'ont pas toutes les mêmes leviers.

*Nota bene* : la métadonnée `distractor_meta` (§2.5) vit dans `content`, pas dans les
`context_tags` — les features de difficulté décrivent la charge cognitive de l'item, la traçabilité
des distracteurs décrit son pouvoir diagnostique. Ne pas mélanger les deux canaux.

---

## 5. `DECIMAL_FEATURE_WEIGHTS` et `decimal_complexity(features) → [0,1]`

Poids repris du Cadrage-LotA §3/A5 (indicatifs, à calibrer en Lot C) :

```python
DECIMAL_FEATURE_WEIGHTS = {
    "places_norm":    0.25,  # nb de décimales (max des opérandes) : thousandths > hundredths > tenths
    "alignment_norm": 0.20,  # nb de places différentes entre opérandes : source majeure d'erreur
    "carry_borrow":   0.15,  # retenue / emprunt requis : charge procédurale
    "zero_trap":      0.10,  # zéro non significatif / intercalaire : active la misconception
    "crosses_unit":   0.10,  # le résultat traverse une unité entière : rupture de magnitude
    "magnitude_norm": 0.10,  # magnitude des nombres : charge de calcul
    "point_shift":    0.10,  # placement de virgule non trivial (× / ÷) : raisonnement sur la magnitude
}
```

Somme = 1.00. Normalisations (miroir de `fraction_complexity` : bornage puis division par le cap) :

```python
def decimal_complexity(feats: dict) -> float:
    """Complexité [0,1] d'un item décimal, à partir de ses features."""
    norm = {
        "places_norm":    (min(feats["decimal_places"], 3) / 3) if "decimal_places" in feats else None,
        "alignment_norm": (min(feats["alignment_gap"], 2) / 2) if "alignment_gap" in feats else None,
        "carry_borrow":   feats.get("carry", feats.get("borrow")),
        "zero_trap":      feats.get("zero_trap"),
        "crosses_unit":   feats.get("crosses_unit"),
        "magnitude_norm": (min(feats["max_value"], 100) / 100) if "max_value" in feats else None,
        "point_shift":    feats.get("point_shift"),
    }
    return weighted_score(norm, DECIMAL_FEATURE_WEIGHTS)
```

Caps justifiés : 3 décimales = borne du domaine G4–G5 (millièmes) ; écart d'alignement ≥ 2 =
le cas maximal utile (entier vs centièmes) ; magnitude 100 = même cap que les fractions
(`min(max_number, 100) / 100`). Les clés absentes ne comptent ni au numérateur ni au dénominateur
(comportement de `weighted_score`, inchangé).

---

## 6. Chaîne de difficulté et `bank_items`

```python
def bank_items(code: str, base_prior: float) -> List[dict]:
    out = []
    for content in generate_for(code):
        feats = decimal_features(code, content)
        diff = difficulty_from_score(base_prior, decimal_complexity(feats))  # band = 250
        out.append({"content": content, "context_tags": feats, "difficulty_prior": diff})
    return out
```

`prior_item = round(prior_compétence + (c − 0.5) × 2 × 250, 1)`, borné à ± 250 du prior de
compétence par construction (`clamp01` sur c), et à l'échelle globale [0, 4000]. Le moteur Elo
(Epic 3) affine ensuite `difficulty_elo` avec le trafic réel — identiquement à toutes les matières.

### Récapitulatif des 14 exemples travaillés (vérifiés numériquement contre `weighted_score`, 2026-07-12)

| Compétence | Prior nœud | c (exemple) | prior_item |
|---|---:|---:|---:|
| `MATH.G4.NBT.PLACE_VALUE_TENTHS` | 1520 | 0.1934 | 1366.7 |
| `MATH.G4.NBT.PLACE_VALUE_HUNDREDTHS` | 1580 | 0.6016 | 1630.8 |
| `MATH.G4.NBT.READ_WRITE_DECIMAL` | 1600 | 0.3844 | 1542.2 |
| `MATH.G4.NBT.DECIMAL_AS_FRACTION` | 1660 | 0.1863 | 1503.1 |
| `MATH.G4.NBT.DECIMAL_NUMBER_LINE` | 1640 | 0.1867 | 1483.4 |
| `MATH.G4.NBT.COMPARE_DECIMALS` | 1700 | 0.4110 | 1655.5 |
| `MATH.G5.NBT.PLACE_VALUE_THOUSANDTHS` | 1820 | 0.7831 | 1961.6 |
| `MATH.G5.NBT.ADD_DECIMALS` | 1840 | 0.2991 | 1739.5 |
| `MATH.G5.NBT.ROUND_DECIMAL` | 1860 | 0.3780 | 1799.0 |
| `MATH.G5.NBT.SUB_DECIMALS` | 1880 | 0.6885 | 1974.3 |
| `MATH.G5.NBT.MULT_DIV_POW10` | 1900 | 0.5152 | 1907.6 |
| `MATH.G5.NBT.MULT_DECIMAL_WHOLE` | 1920 | 0.4921 | 1916.1 |
| `MATH.G5.NBT.DIV_DECIMAL_WHOLE` | 1950 | 0.3406 | 1870.3 |
| `MATH.G5.NBT.MULT_DECIMAL_DECIMAL` | 1960 | 0.3344 | 1877.2 |

Tous les priors d'items restent dans la bande ± 250 de leur compétence (max observé : ± 156.9). Les
exemples choisis sont volontairement des entrées de gamme pour la plupart : chaque générateur DOIT
aussi produire les variantes hautes décrites dans ses « leviers » pour couvrir la plage (règle §2.4).

---

## 7. Critères d'acceptation (alimentent le gate G2 du Lot A)

1. **Parsing** : 100 % des items produits valident `ItemContent` (stem + options + answer).
2. **Correction** : pour chaque item, la réponse est recalculée en `Decimal`/`Fraction` par le test
   et confrontée à `answer` ; pour les divisions, re-multiplication exacte quotient × diviseur.
3. **Zéro float** : aucun littéral flottant ni conversion `float()` dans le chemin de génération des
   valeurs d'items (lint dédié sur le module ; `decimal_complexity` peut retourner un `float`, la
   restriction porte sur la fabrication des contenus).
4. **Distracteurs** : chaque item porte ≥ 2 distracteurs référencés au catalogue A4 (`D-*`/`MC-*`) ;
   aucun distracteur de même valeur exacte que la réponse (dédup cross-représentation `_dvalue`,
   comparaison textuelle sur les items d'écriture — §2.2) ; aucune option dupliquée.
5. **Paires diagnostiques** : les contraintes d'opérandes des specs `D-*` sont vérifiées par les
   tests (chaque formule erronée diverge de la bonne réponse sur les données retenues) — A4 §5.3.
6. **Traçabilité** : chaque option erronée porte `distractor_id` + `misconception_ids` dans
   `distractor_meta` ; la rotation préserve le mapping (§2.5) — prérequis du monitoring C4 (A4 §6).
7. **Couverture** : les 14 codes du draft A3 ont un générateur ; chaque générateur couvre ses
   `item_contexts` ; ~10 items/générateur.
8. **Étalement** : par compétence, plage de `difficulty_prior` ≥ 200 points Elo, aucun prior hors bande ± 250.
9. **1 item = 1 compétence** : strict.
10. **Rotation** : la position de la réponse varie (miroir du test fractions).
11. **Tests** : miroir de `tests/test_deterministic.py` (variation intra-compétence + correction math)
    et compatibilité prouvée avec `tests/test_difficulty.py` (neutralité matière de la couche générique).

## 8. Limites assumées

- Les poids de `DECIMAL_FEATURE_WEIGHTS` sont des **priors experts, non mesurés** (avertissement
  honnêteté A1.4) ; ré-estimation sur trafic réel en Lot C. Aucun artefact issu de cette spec ne
  doit être présenté comme « calibré ».
- `zero_trap` agrège zéro intercalaire et zéro terminal sous un seul booléen — granularité à
  réévaluer si l'analyse d'items (C4) montre des attractivités divergentes.
- Le repli stem → answer (items verbaux) fait dépendre les features de la réponse, pas de l'énoncé —
  acceptable (la réponse EST la charge cognitive de l'item) mais documenté pour la revue experte.
- Les compléments hors catalogue (off-by-one de graduation, erreur de fait multiplicatif,
  non-opération d'arrondi) sont tagués à la famille `MC-*` la plus proche mais sans `D-*` propre —
  à faire entrer au catalogue A4 s'ils s'avèrent attractifs en C4 (invariant de couverture, A4 §6.2).
- L'attribution corrigée L/S (errata A4 §4.6) est appliquée ici mais reste **à confirmer par le
  didacticien** en revue A4.
- L'AR n'est pas traité ici : plan A6 (glossaire MSA, chiffres 0–9, point décimal, gate G3 avec
  détection de tokens latins — errata E8).
