# Catalogue de misconceptions — Décimaux (G4–G5) → spec de distracteurs

**Livrable** : A4 (Cadrage-LotA §3/A4) · **Version** : DRAFT v0.1 · **Date** : 2026-07-11
**Référentiel couvert** : `03_referentiel/referentiel_decimals_draft.json` (14 nœuds NBT, livré A3)
**À lire avec** : `01_strategie/Cadrage-LotA-Extension-Contenu.md` (§3/A4, §3/A5, §3/A8), `04_code/src/items/deterministic.py` (conventions MCQ fractions à répliquer), Lot C (C4, analyse d'items).
**Statut** : sourcé en didactique, **à valider par le didacticien** (revue 0,5 j prévue au plan de ressources §5 du cadrage). Jalon A-3 : chaque compétence a ≥ 2 misconceptions spécifiées — **couvert, cf. §7**.

---

## 1. Rôle du document

Un distracteur n'est pas une « mauvaise réponse plausible » : c'est le **codage d'une méprise précise**, documentée dans la recherche en didactique. Si l'élève choisit ce distracteur, le système apprend *quelle* règle erronée il applique — c'est ce qui transforme un MCQ en instrument de diagnostic. Ce document :

1. recense, **par compétence du draft décimaux**, ≥ 2 misconceptions sourcées ;
2. spécifie pour chacune la **formule de construction déterministe** du distracteur (à partir des opérandes de l'item, codable en dur dans `DECIMAL_GENERATORS`, miroir de la banque fractions) ;
3. définit le **monitoring d'attractivité** (un distracteur jamais choisi est inutile) et son branchement sur le Lot C4.

Il **étend** le noyau du tableau A4 du cadrage (8 lignes) à la couverture complète des 14 compétences, et corrige au passage une attribution du noyau (cf. encadré errata, §4.6).

---

## 2. Familles de misconceptions : la base documentaire

La littérature sur les décimaux est l'une des mieux établies de la didactique des mathématiques. Les familles ci-dessous servent de registre transversal ; chaque entrée du catalogue (§4) y renvoie par son identifiant `MC-*`.

| ID | Famille | Description | Sources principales |
|---|---|---|---|
| `MC-L` | *Longer-is-larger* (règle du nombre entier) | Plus la partie décimale a de chiffres, plus le nombre est jugé grand : 0.45 > 0.5. L'élève traite la partie décimale comme un entier. | Sackur-Grisvard & Léonard (1985, « règle 1 ») ; Resnick, Nesher, Leonard, Magone, Omanson & Peled (1989, *whole number rule*) ; Steinle & Stacey (1998, 2004, comportement L) |
| `MC-S` | *Shorter-is-larger* (règle de la fraction) | Moins de chiffres = plus grand : 0.3 jugé > 0.45, « parce que les centièmes sont plus petits que les dixièmes ». Sur-généralisation d'un savoir fractionnaire correct. | Sackur-Grisvard & Léonard (1985, « règle 2 ») ; Resnick et al. (1989, *fraction rule*) ; Steinle & Stacey (2004, comportement S) |
| `MC-ZERO` | Comportement du zéro | Le zéro cache-place est ignoré (0.05 lu 0.5) ou le zéro final est jugé significatif (0.50 ≠ 0.5, 0.50 > 0.5). | Sackur-Grisvard & Léonard (1985, « règle 3 ») ; Steinle & Stacey (2004) ; Brousseau (1980, obstacles sur les décimaux) |
| `MC-2INT` | Décimal lu comme deux entiers | 3.12 lu « trois virgule douze » et traité comme le couple (3, 12) : 3.12 > 3.5 ; parties additionnées/multipliées séparément. | Hiebert & Wearne (1985) ; Resnick et al. (1989) ; Roche (2005) |
| `MC-MIRROR` | Symétrie miroir autour de la virgule | L'élève construit la partie décimale en miroir de la partie entière (avec une place des « unièmes » fantôme) : dixièmes ↔ dizaines, millièmes ↔ milliers, ordre des places inversé. | Resnick et al. (1989) ; Hiebert & Wearne (1986) |
| `MC-DIGIT` | Valeur du chiffre = chiffre nu | « Le 7 de 3.7 vaut 7 » ; forme développée fausse (0.7 = 7 × 10). Manipulation syntaxique sans sémantique de position. | Hiebert & Wearne (1985, 1986) ; Hart (1981, CSMS) |
| `MC-FRACLINK` | Liaison fraction↔décimal erronée | 1/2 = 0.2 (dénominateur posé après la virgule), 0.3 = 1/3 (association réciproque), puissance de dix fausse (0.25 = 25/10). | Moss & Case (1999) ; Resnick et al. (1989) ; Steinle & Stacey (2004) |
| `MC-ALIGN` | Alignement à droite | En posant l'addition/soustraction, alignement sur le dernier chiffre au lieu de la virgule. | Hiebert & Wearne (1985) |
| `MC-BUGSUB` | Bugs de soustraction transférés | Plus-petit-du-plus-grand par colonne (pas d'emprunt) ; emprunt sans décrément. | Brown & VanLehn (1980, *repair theory*) ; Resnick et al. (1989) |
| `MC-TRUNC` | Troncature / arrêt prématuré | Tronquer au lieu d'arrondir ; quotient arrêté avant le zéro à ajouter. | Hiebert & Wearne (1986) ; Steinle & Stacey (2004) |
| `MC-CARRY` | Retenue / frontière mal gérée | 3.96 arrondi au dixième → « 3.10 » ; double arrondi (0.148 → 0.15 → 0.2). | Brown & VanLehn (1980) ; Hiebert & Wearne (1985) |
| `MC-ADD0` | « ×10 ajoute un zéro » | Règle mémorisée sur les entiers, fausse sur les décimaux : 2.5 × 10 = 2.50. | Hart (1981, CSMS) ; Steinle & Stacey (2004) |
| `MC-SHIFT` | Décalage de virgule erroné | Sens du décalage inversé (÷10 décale à droite) ou nombre de rangs faux (×100 décale d'un rang). | Hiebert & Wearne (1986) ; Hart (1981) |
| `MC-SEP` | Parties opérées séparément | (a.b) op (c.d) = (a op c).(b op d) : 2.5 × 3 = 6.15 ; 2.5 + 0.35 = 2.40. Cas particulier calculatoire de `MC-2INT`. | Hiebert & Wearne (1985) |
| `MC-MULTBIG` | « La multiplication agrandit toujours » | Modèle implicite de la multiplication comme addition répétée : un produit plus petit que les facteurs est rejeté. | Fischbein, Deri, Nello & Marino (1985) ; Bell, Swan & Taylor (1981) ; Graeber, Tirosh & Glover (1989) |
| `MC-DIVSMALL` | « Le diviseur doit être plus petit » | Division partitive implicite : si dividende < diviseur, l'élève inverse les opérandes ou déclare l'opération impossible. | Fischbein et al. (1985) ; Graeber & Tirosh (1990) |
| `MC-REST` | Reste accolé comme décimale | 73 ÷ 5 = « 14.3 » (14 reste 3) : le reste est écrit après la virgule. | Hart (1981) ; Hiebert & Wearne (1986) |
| `MC-PLACES` | Comptage des décimales du produit | p(produit) = max des places au lieu de la somme (transfert de la règle d'alignement de l'addition) : 0.4 × 0.6 = 2.4. | Hiebert & Wearne (1985, 1986) |
| `MC-DENSE` | Discrétude des décimaux | « Il n'y a pas de nombre entre 0.3 et 0.4 » ; le successeur de 0.3 est 0.4. | Vamvakoussi & Vosniadou (2004) |
| `MC-MONEY` | Pensée monétaire | Le décimal est tronqué mentalement à 2 places (modèle dirhams/fils) : 4.4502 = 4.45. Le contexte monétaire aide en G4 mais plafonne en G5. | Steinle & Stacey (2004, *money thinkers*) ; Irwin (2001) |

**Point d'appui longitudinal.** Steinle & Stacey (2004, suivi de 3 204 élèves) montrent que ces comportements sont **persistants** (L domine tôt, S persiste tard, y compris chez des élèves de secondaire) et que l'« expertise apparente » (réussir les items faciles avec une règle fausse) est fréquente. Conséquence de design : les opérandes de nos items doivent être des **paires diagnostiques** (cf. §5.3) — c'est le principe du *Decimal Comparison Test* de Steinle & Stacey, transposé à la génération.

---

## 3. Notation des specs déterministes

Toutes les formules ci-dessous s'appliquent aux **opérandes de l'item** au moment de la génération, en arithmétique exacte `decimal.Decimal` (jamais de flottant — contrainte A5). Conventions :

- `x`, `y` : opérandes décimaux ; `n` : opérande entier ; `k` : exposant de la puissance de dix.
- `a` = partie entière de `x` ; `b̄` = chaîne des chiffres décimaux de `x` (zéros conservés : pour 3.05, `b̄` = "05") ; `b` = `b̄` lue comme entier (5) ; idem `c`, `d̄`, `d` pour `y`.
- `p(x)` = nombre de décimales de `x` (longueur de `b̄`).
- `strip(x)` = entier obtenu en supprimant la virgule (2.5 → 25 ; 3.05 → 305).
- `shift(v, k)` = virgule décalée de `k` rangs vers la droite (`k` < 0 : vers la gauche).
- `trunc(v, p)` = troncature à `p` décimales ; `round(v, p)` = arrondi scolaire (5 → au-dessus).
- `concat(…)` = collage de chaînes, relu ensuite comme nombre (« 6 » + « . » + « 15 » → 6.15).
- `digit(x, i)` = i-ème chiffre après la virgule ; `digit_tens(x)`, `digit_thousands(x)` : chiffres de la partie entière.

Chaque distracteur porte un identifiant `D-{SKILL}-{nn}` et est **tagué** du ou des `MC-*` qu'il code (métadonnée transportée dans l'item, cf. §6.1).

---

## 4. Catalogue par compétence

### 4.1 `MATH.G4.NBT.PLACE_VALUE_TENTHS` — G4 · RECALL · prior 1520

Compétence d'entrée du domaine (racine locale, pont fraction entrant). Les méprises dominantes sont la **symétrie miroir** (dixièmes confondus avec dizaines, car l'élève cherche une place des « unièmes » à droite de la virgule) et la **valeur nue du chiffre**.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-PVT-01` | Dixièmes confondus avec dizaines (miroir) : dans 47.3, « le chiffre des dixièmes est 4 » | `MC-MIRROR` · Resnick et al. (1989) | Item « quel chiffre occupe la place des dixièmes de x ? » → distracteur = `digit_tens(x)`. **Contrainte d'opérandes** : générer `x` avec ≥ 2 chiffres entiers et `digit_tens(x) ≠ digit(x,1)` |
| `D-PVT-02` | Valeur du chiffre = chiffre nu : « le 7 de 3.7 vaut 7 » | `MC-DIGIT` · Hiebert & Wearne (1985) | Item « que vaut le chiffre `digit(x,1)` dans x ? » (réponse `digit(x,1)/10`) → distracteur = `digit(x,1)` (l'entier nu) |
| `D-PVT-03` | Forme développée inversée : 0.7 = 7 × 10 | `MC-DIGIT` · Resnick et al. (1989) | Même item en contexte *expanded form* → distracteur = `digit(x,1) × 10` |
| `D-PVT-04` | Modèle monétaire mal converti : 0.5 AED lu « 5 fils » | `MC-MONEY` · Irwin (2001) | Contexte *money model (dirhams/fils)* : « x AED = ? fils » (réponse `x × 100`) → distracteur = `b` fils (chiffres décimaux lus tels quels : 0.5 → 5 fils) |

### 4.2 `MATH.G4.NBT.PLACE_VALUE_HUNDREDTHS` — G4 · APPLY · prior 1580

Le zéro cache-place entre en scène (contexte `zero as placeholder` du draft) : c'est ici que se joue la distinction 0.05 / 0.5.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-PVH-01` | Lecture miroir de l'ordre des places : dans 0.35, « le chiffre des centièmes est 3 » | `MC-MIRROR` · Resnick et al. (1989) | Item « chiffre des centièmes de x ? » → distracteur = `digit(x, 1)`. **Contrainte** : `digit(x,1) ≠ digit(x,2)` |
| `D-PVH-02` | Zéro cache-place ignoré : 0.05 = « 5 dixièmes » (= 0.5) | `MC-ZERO` · Sackur-Grisvard & Léonard (1985) | Item « écris 5 centièmes » (réponse 0.05) → distracteur = `0.d` sans le zéro cache-place (0.5). Réciproque : « que vaut le 5 de 0.05 ? » → distracteur = `5/10` |
| `D-PVH-03` | Forme développée à dénominateur unique : 0.35 = 3/10 + 5/10 | `MC-DIGIT` · Hiebert & Wearne (1986) | Contexte *expanded form* : distracteur = `Σ digit(x,i)/10` (tous les chiffres sur 10) |

### 4.3 `MATH.G4.NBT.READ_WRITE_DECIMAL` — G4 · APPLY · prior 1600

La lecture « deux entiers » (« trois virgule douze ») est le prédicteur le plus direct des comportements L en comparaison (Roche, 2005) : le nom oral du nombre fabrique la misconception.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-RWD-01` | Lecture « deux entiers » : 3.12 = « trois virgule douze » validé comme lecture en unités de numération | `MC-2INT` · Roche (2005) ; Steinle & Stacey (2004) | Item nombre→mots « comment se lit x ? » (réponse « a unités et b̄ centièmes », p(x)=2) → distracteur = « `a` virgule `b` » présenté comme équivalent à « `a` unités et `b` **dixièmes** » (3.12 → « trois unités et douze dixièmes ») |
| `D-RWD-02` | Zéro cache-place omis à l'écriture : « trois unités et cinq centièmes » → 3.5 | `MC-ZERO` · Hiebert & Wearne (1985, item historique) | Item mots→nombre avec `b̄` commençant par 0 (réponse `a.b̄`) → distracteur = `concat(a, ".", b)` (zéros de tête supprimés : 3.05 → 3.5) |
| `D-RWD-03` | Zéro final significatif : 0.5 ≠ 0.50 | `MC-ZERO` · Steinle & Stacey (2004) ; Brousseau (1980) | Item « quelle écriture vaut x ? » → distracteur = assertion « `x` et `concat(x, "0")` sont deux nombres différents » ; en money notation, « 2.50 AED > 2.5 AED » |

### 4.4 `MATH.G4.NBT.DECIMAL_AS_FRACTION` — G4 · REASON · prior 1660

Compétence-pont (3 arêtes HARD entrantes depuis les fractions) : les distracteurs y sont doublement diagnostiques, car ils discriminent une faille côté fractions d'une faille côté décimaux.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-DAF-01` | Dénominateur posé après la virgule : 1/2 = 0.2 (et a/b = « a.b ») | `MC-FRACLINK` · Moss & Case (1999) ; noyau A4 | Item fraction→décimal `u/v` → distracteur = `0.v` (1/2 → 0.2) ; variante = `concat(u, ".", v)` (1/2 → 1.2). Générer les deux si ≠ |
| `D-DAF-02` | Association réciproque : 0.3 = 1/3 | `MC-FRACLINK` · Resnick et al. (1989) | Item décimal→fraction `0.d` (p=1) → distracteur = `1/d` (0.3 → 1/3). **Contrainte** : `d ≥ 2` |
| `D-DAF-03` | Puissance de dix erronée : 0.25 = 25/10 ; 0.5 = 5/100 | `MC-FRACLINK` · Hiebert & Wearne (1986) | Item décimal→fraction → distracteur = `strip_frac(x) / 10^(p(x)−1)` et/ou `… / 10^(p(x)+1)` |
| `D-DAF-04` | Partie entière absorbée : 1.25 = 1/25 ou 25/100 | `MC-2INT` · Hiebert & Wearne (1986) | Contexte *greater than one* : item `a.b̄` → fraction (réponse `strip(x)/10^p(x)`) → distracteur = `b/10^p(x)` (partie entière jetée : 1.25 → 25/100) |

*Garde-fou* : pour les items « donne la fraction **irréductible** », la fraction non simplifiée (5/10 pour 0.5) est numériquement égale — elle ne peut servir de distracteur **que** si la consigne exige explicitement la forme irréductible ; sinon collision avec la bonne réponse (règle §5.1).

### 4.5 `MATH.G4.NBT.DECIMAL_NUMBER_LINE` — G4 · APPLY · prior 1640

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-DNL-01` | Erreur de magnitude ×10 : 0.35 placé comme 3.5 (échelle de la graduation ignorée) | `MC-SHIFT` · Hart (1981, items ligne numérique CSMS) | Item « où se place x ? » sur ligne dépassant 1 → distracteur = position de `shift(x, +1)`. **Contrainte** : `shift(x, +1)` doit tomber sur la ligne |
| `D-DNL-02` | Lecture miroir des décimales : 0.35 placé en 0.53 | `MC-MIRROR` · Resnick et al. (1989) | Distracteur = position de `concat(a, ".", reverse(b̄))`. **Contrainte** : `b̄ ≠ reverse(b̄)` |
| `D-DNL-03` | Discrétude : « aucun nombre entre 0.3 et 0.4 » | `MC-DENSE` · Vamvakoussi & Vosniadou (2004) | Contexte *between two marks* : « quel nombre est entre `x` et `x + 10^-p` ? » → distracteurs = « aucun » et l'interpolation entière `concat(strip(x), ".5")` relue à l'échelle des entiers (entre 0.3 et 0.4 → « 3.5 ») |

### 4.6 `MATH.G4.NBT.COMPARE_DECIMALS` — G4 · REASON · prior 1700

Le cœur historique de la littérature (comportements L/S/A/U de Steinle & Stacey). **La règle de génération capitale est le choix de paires diagnostiques** : une paire où la règle fausse donne la bonne réponse (ex. 0.75 > 0.5 sous L) ne détecte rien.

> **Errata sur le noyau du cadrage (§3/A4).** La ligne *shorter-is-larger* du noyau donne comme exemple « 0.3 < 0.25 » : cette assertion est en réalité produite par **longer-is-larger** (0.25 a plus de chiffres, donc jugé plus grand). L'archétype S est l'assertion inverse sur une paire où le plus court est le plus **petit** : « 0.3 > 0.45 ». Les specs ci-dessous utilisent l'attribution corrigée ; à faire confirmer par le didacticien en revue.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-CMP-01` | *Longer-is-larger* : 0.45 jugé > 0.5 | `MC-L` · Resnick et al. (1989) ; Steinle & Stacey (2004) ; Sackur-Grisvard & Léonard règle 1 | Item « le plus grand de {x, y} ? » — **contrainte d'opérandes** : `p(x) > p(y)` **et** `x < y` (paire diagnostique L : 0.45 vs 0.5) → distracteur = `x` |
| `D-CMP-02` | *Shorter-is-larger* : 0.3 jugé > 0.45 | `MC-S` · Resnick et al. (1989) ; Steinle & Stacey (2004) ; Sackur-Grisvard & Léonard règle 2 | Contrainte : `p(x) < p(y)` **et** `x < y` (paire diagnostique S : 0.3 vs 0.45) → distracteur = `x` |
| `D-CMP-03` | Zéro final significatif : « 0.50 > 0.5 » | `MC-ZERO` · Sackur-Grisvard & Léonard (1985) règle 3 | Item de comparaison {x, concat(x,"0")} avec options { < , = , > } (réponse =) → distracteur clé = « > » |
| `D-CMP-04` | Pensée monétaire : 4.4502 = 4.45 | `MC-MONEY` · Steinle & Stacey (2004) ; Irwin (2001) | Paire {x, trunc(x, 2)} avec `p(x) ≥ 3` et `digit(x,3) ≠ 0` → distracteur = « égaux » |
| `D-CMP-05` | Ordre L/S sur 3+ nombres | `MC-L`, `MC-S` · Moloney & Stacey (1997) | Contexte *ordering 3+* : distracteur L = liste triée par `strip()` croissant ; distracteur S = liste triée par `p()` décroissant. **Contrainte** : chaque tri erroné ≠ tri correct ≠ l'autre tri erroné (triple divergence) |

### 4.7 `MATH.G5.NBT.PLACE_VALUE_THOUSANDTHS` — G5 · APPLY · prior 1820

Le contexte clé du draft est la **relation ×10 entre places adjacentes** (CCSS 5.NBT.A.1) : c'est là que la symétrie miroir et l'inversion de la relation font le plus de dégâts.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-PVM-01` | Relation adjacente inversée : « le 4 de 0.04 vaut 10 fois le 4 de 0.4 » | `MC-MIRROR` · Resnick et al. (1989) ; Hiebert & Wearne (1986) | Item « le `d` de `shift(u,−i)` vaut ___ fois le `d` de `shift(u,−i−1)` » (réponse 10) → distracteurs = `1/10` (inversion) et `100` (saut de rang) |
| `D-PVM-02` | Millièmes ↔ milliers (miroir) | `MC-MIRROR` · Resnick et al. (1989) | Item « chiffre des millièmes de x ? » avec `x` ayant ≥ 4 chiffres entiers → distracteur = `digit_thousands(x)`. **Contrainte** : `digit_thousands(x) ≠ digit(x,3)` |
| `D-PVM-03` | Zéro cache-place : 0.052 = « 52 centièmes » | `MC-ZERO` · Sackur-Grisvard & Léonard (1985) | Item « x = ___ millièmes » (réponse `strip_frac(x)`) → distracteur = « `b` centièmes » (nom de place compté à partir du premier chiffre non nul) |

### 4.8 `MATH.G5.NBT.ADD_DECIMALS` — G5 · APPLY · prior 1840

Hiebert & Wearne (1985) documentent que la quasi-totalité des erreurs d'addition décimale relèvent de **deux règles syntaxiques** — alignement à droite, et traitement séparé des deux « entiers ». Le noyau du cadrage donne « 2.5 + 0.35 = 2.40 » : c'est la variante *parties séparées* (5 + 35 = 40) ; l'alignement à droite strict donne, lui, 0.60. Les deux sont spécifiées.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-ADD-01` | Alignement à droite : 2.5 + 0.35 → 25 + 35 = 60 → 0.60 | `MC-ALIGN` · Hiebert & Wearne (1985) | Distracteur = `shift(strip(x) + strip(y), −max(p(x), p(y)))`. **Contrainte d'opérandes** : `p(x) ≠ p(y)` (sinon la formule donne la bonne réponse — collision §5.1) |
| `D-ADD-02` | Parties additionnées séparément : 2.5 + 0.35 = 2.40 | `MC-SEP`/`MC-2INT` · Hiebert & Wearne (1985) ; Resnick et al. (1989) | Distracteur = `concat(a + c, ".", b + d)` (2.5 + 0.35 → 2.40 ; noyau A4). Régime *crossing a whole* : quand `b + d ≥ 10^max(p)`, la même formule produit la non-traversée de l'unité (1.8 + 0.4 → « 1.12 ») — taguer aussi `MC-CARRY` |
| `D-ADD-03` | Virgule perdue au résultat | `MC-DIGIT` · Hiebert & Wearne (1985) | Distracteur = `strip(x + y)` (résultat correct écrit sans virgule : 2.5 + 0.35 → 285). À réserver aux items *money* où la magnitude rend le piège plausible |

### 4.9 `MATH.G5.NBT.ROUND_DECIMAL` — G5 · APPLY · prior 1860

L'arrondi hérite des misconceptions de comparaison (il faut savoir *où* est le rang et *si* on est au-dessus ou en dessous de la borne) — d'où l'arête HARD `COMPARE_DECIMALS → ROUND_DECIMAL` du draft.

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-RND-01` | Troncature au lieu d'arrondi : 3.87 au dixième → 3.8 | `MC-TRUNC` · Hiebert & Wearne (1986) | Distracteur = `trunc(x, p)`. **Contrainte** : `digit(x, p+1) ≥ 5` (sinon troncature = arrondi, collision) |
| `D-RND-02` | Rang confondu (off-by-one, dixième ↔ unité/centième) | `MC-MIRROR` · Resnick et al. (1989) | Distracteurs = `round(x, p−1)` et `round(x, p+1)` (arrondi un rang trop tôt / trop tard). **Contrainte** : chaque valeur ≠ `round(x, p)` |
| `D-RND-03` | Chiffre 5 arrondi vers le bas : 2.45 au dixième → 2.4 | `MC-TRUNC` · Steinle & Stacey (2004) | Contexte *digit 5 at boundary* : générer `x` avec `digit(x, p+1) = 5` → distracteur = `trunc(x, p)` |
| `D-RND-04` | Retenue non propagée à la frontière : 3.96 au dixième → « 3.10 » | `MC-CARRY` · Brown & VanLehn (1980) | Quand `digit(x, p) = 9` et arrondi vers le haut : distracteur = `concat(a, ".", b̄[0:p−1], "10")` (le « 10 » écrit littéralement) |
| `D-RND-05` | Double arrondi : 0.148 au dixième → 0.15 → 0.2 | `MC-CARRY` · documenté dans les analyses d'erreurs d'arrondi (à confirmer en revue didacticien) | Distracteur = arrondi séquentiel depuis le dernier chiffre : `round(round(x, p+1), p)`. **Contrainte** : résultat ≠ `round(x, p)` (vrai ssi `digit(x,p+1)=4` et `digit(x,p+2)≥5`) |

### 4.10 `MATH.G5.NBT.SUB_DECIMALS` — G5 · APPLY · prior 1880

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-SUB-01` | Alignement à droite : 4.7 − 0.24 → 47 − 24 = 23 → 0.23 | `MC-ALIGN` · Hiebert & Wearne (1985) | Distracteur = `shift(strip(x) − strip(y), −max(p(x), p(y)))`. **Contraintes** : `p(x) ≠ p(y)` et `strip(x) > strip(y)` (garantir un résultat positif, sinon écarter) |
| `D-SUB-02` | Plus-petit-du-plus-grand par colonne : 3.00 − 0.45 → 3.45 | `MC-BUGSUB` · Brown & VanLehn (1980) ; Resnick et al. (1989) | Après alignement correct sur la virgule et padding de zéros : distracteur = nombre dont chaque colonne vaut `|digit_x − digit_y|` (aucun emprunt). Couvre le contexte *from a whole* : 3 − 0.45 → 3.45 |
| `D-SUB-03` | Emprunt sans décrément de l'entier : 3.00 − 0.45 → 3.55 | `MC-BUGSUB` · Brown & VanLehn (1980, *borrow-no-decrement*) | Quand un emprunt traverse la virgule : distracteur = `concat(a − c, ".", 10^m − d)` où `m = max(p)` — décimales justes, entier non décrémenté. **Contrainte** : `b̄` = zéros (cas « from a whole ») ou `b < d` |

### 4.11 `MATH.G5.NBT.MULT_DIV_POW10` — G5 · APPLY · prior 1900

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-P10-01` | « ×10 ajoute un zéro » : 2.5 × 10 = 2.50 | `MC-ADD0` · Hart (1981, CSMS) ; Steinle & Stacey (2004) | Item `x × 10^k` → distracteur = `concat(x, "0" × k)` (valeur inchangée, zéros accolés). Présenté comme valeur : 2.50 ; l'option doit être affichée avec ses zéros |
| `D-P10-02` | Sens du décalage inversé : 2.5 ÷ 10 = 25 | `MC-SHIFT` · Hiebert & Wearne (1986) | Item `x ÷ 10^k` → distracteur = `shift(x, +k)` ; item `x × 10^k` → distracteur = `shift(x, −k)` |
| `D-P10-03` | Nombre de rangs erroné : 2.5 × 100 = 25 | `MC-SHIFT` · Hart (1981) | Distracteur = `shift(x, ±(k−1))` (un rang de moins que demandé). **Contrainte** : `k ≥ 2` |

### 4.12 `MATH.G5.NBT.MULT_DECIMAL_WHOLE` — G5 · APPLY · prior 1920

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-MDW-01` | Parties multipliées séparément : 2.5 × 3 = 6.15 | `MC-SEP` · Hiebert & Wearne (1985) | Distracteur = `concat(a × n, ".", b × n)` (2×3=6 ; 5×3=15 → 6.15). **Contrainte** : ≠ produit correct (faux dès que `b × n ≥ 10^p(x)` ou qu'il y a retenue — vérifier, sinon écarter) |
| `D-MDW-02` | Virgule mal replacée : 2.5 × 3 → 75 ou 0.75 | `MC-SHIFT` · Hiebert & Wearne (1985) | Distracteurs = `shift(x × n, +1)` et `shift(x × n, −1)` (produit exact, virgule décalée d'un rang dans chaque sens) |
| `D-MDW-03` | « La multiplication agrandit » utilisée comme vérification : 0.4 × 6 → 24 | `MC-MULTBIG` · Fischbein et al. (1985) ; Bell, Swan & Taylor (1981) | Contexte *estimation check* avec `x < 1` : distracteur = `shift(x × n, +j)` avec `j` minimal tel que le distracteur > `n` (la magnitude « rassurante »). Recouvre `D-MDW-02` quand j=1 : taguer les deux IDs |

### 4.13 `MATH.G5.NBT.DIV_DECIMAL_WHOLE` — G5 · REASON · prior 1950

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-DDW-01` | Reste accolé comme décimale : 7.3 ÷ 5 → « 1.43 » | `MC-REST` · Hart (1981) ; Hiebert & Wearne (1986) | Poser `N = strip(x)`, `q = N div n`, `r = N mod n` → distracteur = `shift(concat(q, ".", r), −p(x))` relu comme nombre (73÷5 = 14 r 3 → « 14.3 » → 1.43 après replacement de la virgule du dividende). Variante virgule ignorée : `concat(q, ".", r)` (→ 14.3). **Contrainte** : `r ≠ 0` |
| `D-DDW-02` | Quotient tronqué (zéro à ajouter omis) : 4.5 ÷ 6 → 0.7 | `MC-TRUNC` · Hiebert & Wearne (1986) | Contexte *quotient needs added zero* : distracteur = `trunc(x ÷ n, p(x))`. **Contrainte** : `x ÷ n` a strictement plus de `p(x)` décimales |
| `D-DDW-03` | « Le diviseur doit être plus petit » : 4.5 ÷ 6 → calcule 6 ÷ 4.5 | `MC-DIVSMALL` · Graeber & Tirosh (1990) ; Fischbein et al. (1985) | Quand `x < n` : distracteurs = `round(n ÷ x, p_correct)` (opérandes inversés) et l'option « impossible, on ne peut pas diviser un petit par un grand » |
| `D-DDW-04` | Virgule du quotient mal placée | `MC-SHIFT` · Hiebert & Wearne (1985) | Distracteurs = `shift(x ÷ n, ±1)` |

### 4.14 `MATH.G5.NBT.MULT_DECIMAL_DECIMAL` — G5 · REASON · prior 1960

Le nœud le plus profond du domaine : ses distracteurs croisent le comptage de places (procédural) et la magnitude attendue (conceptuel). C'est le terrain de « la multiplication agrandit toujours » (Fischbein et al., 1985), la misconception la plus robuste de la littérature — persistante jusque chez les enseignants en formation (Graeber, Tirosh & Glover, 1989).

| ID | Misconception | Famille · source | Spec distracteur (déterministe) |
|---|---|---|---|
| `D-MDD-01` | Comptage des places = max au lieu de la somme : 0.4 × 0.6 = 2.4 | `MC-PLACES` · Hiebert & Wearne (1985, 1986) ; noyau A4 | Distracteur = `shift(strip(x) × strip(y), −max(p(x), p(y)))` (24 → 2.4). **Contrainte** : `p(x) + p(y) > max(p(x), p(y))`, toujours vrai si les deux opérandes sont décimaux |
| `D-MDD-02` | « La multiplication agrandit » : rejet du produit < facteurs | `MC-MULTBIG` · Fischbein et al. (1985) ; Bell, Swan & Taylor (1981) ; Graeber, Tirosh & Glover (1989) | Contexte *product smaller than factors* (`x < 1` et `y < 1`) : distracteur = `shift(produit_correct, +j)`, `j` minimal tel que le distracteur > `max(x, y)`. Quand il coïncide avec `D-MDD-01`, taguer les deux IDs (cf. §6.1) |
| `D-MDD-03` | Parties multipliées séparément : 1.2 × 1.3 = 1.6 | `MC-SEP` · Hiebert & Wearne (1985) | Distracteur = `concat(a × c, ".", b × d)` (1×1=1 ; 2×3=6 → 1.6). **Contrainte** : opérandes > 1 pour que la formule soit bien définie et ≠ produit correct |
| `D-MDD-04` | Zéro final du produit brut escamoté avant comptage : 0.5 × 0.4 → 20 → « 0.02 » | `MC-PLACES`/`MC-ZERO` · Hiebert & Wearne (1986) | Quand `strip(x) × strip(y)` finit par 0 : distracteur = `shift(strip_trailing_zeros(strip(x) × strip(y)), −(p(x) + p(y)))` (20 → 2 → 0.02). **Contrainte** : produit brut ≡ 0 mod 10 |

---

## 5. Règles communes de génération (contrat pour A5 / `DECIMAL_GENERATORS`)

Ces règles sont le pendant décimaux des garde-fous déjà en place dans `src/items/deterministic.py` (fractions) et s'imposent à tous les générateurs :

**5.1 — Garde-fou de collision.** Un distracteur dont la valeur coïncide avec la bonne réponse est **écarté** (comme le filtre `[x for x in distractors if x != correct]` de la banque fractions) ; si la spec l'exige (cf. contraintes d'opérandes par entrée du §4), on **régénère les opérandes** plutôt que d'écarter, pour préserver le codage de la misconception. La comparaison de collision se fait sur la **valeur** `Decimal` (0.50 == 0.5), pas sur la chaîne — sauf pour les items où l'écriture est l'objet même de la question (`D-RWD-03`, `D-CMP-03`, `D-P10-01`), où la comparaison est textuelle.

**5.2 — Unicité et complétude.** Les distracteurs d'un même item doivent être deux à deux distincts (en valeur, même règle d'exception que 5.1). Cible : 3 distracteurs par MCQ, chacun tagué d'au moins un `MC-*`. Si le catalogue de la compétence ne fournit que 2 distracteurs valides pour les opérandes tirés, compléter par un distracteur de magnitude (`shift(correct, ±1)`) tagué `MC-SHIFT` — jamais par du bruit aléatoire.

**5.3 — Paires diagnostiques (principe DCT).** Les opérandes ne sont pas tirés au hasard puis habillés de distracteurs : ils sont **contraints pour que chaque règle erronée diverge de la bonne réponse** (et, autant que possible, que deux règles erronées divergent entre elles). C'est le principe du *Decimal Comparison Test* (Steinle & Stacey) : un item où L donne la bonne réponse ne détecte pas L. Les contraintes d'opérandes du §4 (colonnes « Contrainte ») sont donc **partie intégrante de la spec**, pas des options.

**5.4 — Arithmétique exacte.** Tout calcul en `decimal.Decimal` (contexte exact), jamais en flottant — 0.1 + 0.2 doit produire 0.3, pas 0.30000000000000004 (contrainte A5 du cadrage). Les `concat(…)` sont des opérations de chaîne relues via `Decimal(str)`.

**5.5 — Traçabilité.** Chaque option générée transporte sa métadonnée `misconception_ids: [MC-*, …]` et son `distractor_id` (`D-…-nn`) ; le shuffle des options (équivalent du `_mcq(salt)` fractions) doit **préserver ce mapping** option→tags. C'est le prérequis du monitoring (§6).

---

## 6. Monitoring d'attractivité des distracteurs (lien Lot C4)

**Principe.** Un distracteur jamais choisi est inutile : il occupe l'un des trois emplacements du MCQ sans rien diagnostiquer, alors que le catalogue ci-dessus fournit des remplaçants documentés. Symétriquement, un distracteur choisi par les **bons** élèves ne signale pas une misconception mais une ambiguïté d'énoncé. L'attractivité est donc un **critère de révision continue**, instrumenté dans l'analyse d'items du Lot C4 (même harnais que la calibration/equating, réutilisé domaine par domaine).

**6.1 — Instrumentation.** Grâce au tagging §5.5, chaque réponse erronée enregistrée est attribuable à un `distractor_id` et à ses `misconception_ids`. Deux niveaux d'agrégation :
- **niveau item** : santé de chaque distracteur de chaque item ;
- **niveau misconception × compétence** : prévalence de `MC-L` sur `COMPARE_DECIMALS` dans une cohorte, etc. — c'est cette agrégation qui alimente le rapport enseignant (« 40 % de la classe applique *longer-is-larger* »), un sous-produit à forte valeur produit.
Cas des doubles tags (ex. `D-MDD-01`/`D-MDD-02` quand les formules coïncident) : le choix crédite **toutes** les misconceptions taguées ; la désambiguïsation se fait au niveau cohorte en croisant avec les items où les formules divergent.

**6.2 — Seuils et actions.** Fenêtre minimale alignée sur le mécanisme de quarantaine existant du moteur (**n ≥ 30 réponses par item**, cf. A7) ; en dessous, aucune décision.

| Signal | Seuil (proposé, à ancrer empiriquement en C4) | Action |
|---|---|---|
| **Distracteur mort** | < 5 % des réponses **erronées** de l'item sur n ≥ 30 | File de révision : remplacer par la misconception suivante du catalogue de la compétence (§4) ; incrémenter la version de l'item ; l'historique de calibration de l'item est invalidé (re-calibrage) |
| **Distracteur dominant** | > 65 % des réponses erronées sur n ≥ 30 | Revue humaine : soit misconception massivement prévalente (signal pédagogique précieux — remonter au rapport prof, ne pas toucher l'item), soit énoncé ambigu (corriger) |
| **Distracteur qui attire les forts** | Choisi de façon disproportionnée par des élèves d'ability > prior_item + 200 (corrélation choix×ability ≥ 0 là où l'on attend une corrélation négative, type point-bisériel par option) | Revue prioritaire : c'est un défaut d'énoncé, pas une misconception |
| **Misconception sous-représentée** | Un `MC-*` du catalogue n'est porté par aucun distracteur vivant d'une compétence | Combler à la prochaine vague de génération (la couverture du catalogue est un invariant, pas un état initial) |

**6.3 — Boucle de vie.** Génération (A5, specs §4) → gate G2 (« distracteurs = misconceptions A4 », cf. A8) → trafic réel → analyse d'attractivité (C4) → révision/remplacement versionné → re-calibration. Les remplacements sont **journalisés** (quel distracteur, quel motif, quelle date) : ce journal est une pièce de l'auditabilité de l'actif référentiel, au même titre que les arbitrages de la double lecture experte (A1.8).

**6.4 — Honnêteté des seuils.** Les seuils 5 % / 65 % sont des conventions de départ, pas des mesures : ils seront ré-ancrés sur les distributions réelles observées en C4 (même doctrine que les priors experts, cf. avertissement A1.4 du cadrage). Aucun deck ne présente ce monitoring comme « validé » avant les premières cohortes.

---

## 7. Couverture et vérification

Les 14 codes cités dans ce document existent tous dans `referentiel_decimals_draft.json` (vérifié contre le JSON le 2026-07-11) ; jalon A-3 « ≥ 2 misconceptions spécifiées par compétence » couvert :

| # | Code compétence | Misconceptions spécifiées | Familles couvertes |
|---|---|---|---|
| 1 | `MATH.G4.NBT.PLACE_VALUE_TENTHS` | 4 | MIRROR, DIGIT ×2, MONEY |
| 2 | `MATH.G4.NBT.PLACE_VALUE_HUNDREDTHS` | 3 | MIRROR, ZERO, DIGIT |
| 3 | `MATH.G4.NBT.READ_WRITE_DECIMAL` | 3 | 2INT, ZERO ×2 |
| 4 | `MATH.G4.NBT.DECIMAL_AS_FRACTION` | 4 | FRACLINK ×3, 2INT |
| 5 | `MATH.G4.NBT.DECIMAL_NUMBER_LINE` | 3 | SHIFT, MIRROR, DENSE |
| 6 | `MATH.G4.NBT.COMPARE_DECIMALS` | 5 | L, S, ZERO, MONEY, L+S (ordre) |
| 7 | `MATH.G5.NBT.PLACE_VALUE_THOUSANDTHS` | 3 | MIRROR ×2, ZERO |
| 8 | `MATH.G5.NBT.ADD_DECIMALS` | 3 | ALIGN, SEP/2INT (+CARRY), DIGIT |
| 9 | `MATH.G5.NBT.ROUND_DECIMAL` | 5 | TRUNC ×2, MIRROR, CARRY ×2 |
| 10 | `MATH.G5.NBT.SUB_DECIMALS` | 3 | ALIGN, BUGSUB ×2 |
| 11 | `MATH.G5.NBT.MULT_DIV_POW10` | 3 | ADD0, SHIFT ×2 |
| 12 | `MATH.G5.NBT.MULT_DECIMAL_WHOLE` | 3 | SEP, SHIFT, MULTBIG |
| 13 | `MATH.G5.NBT.DIV_DECIMAL_WHOLE` | 4 | REST, TRUNC, DIVSMALL, SHIFT |
| 14 | `MATH.G5.NBT.MULT_DECIMAL_DECIMAL` | 4 | PLACES, MULTBIG, SEP, PLACES/ZERO |

**Total : 50 specs de distracteurs** pour 14 compétences (min. 3 par compétence), 20 familles de misconceptions documentées.

---

## Références

- Bell, A., Swan, M. & Taylor, G. (1981). Choice of operation in verbal problems with decimal numbers. *Educational Studies in Mathematics*, 12, 399–420.
- Brousseau, G. (1980). Problèmes de l'enseignement des décimaux. *Recherches en Didactique des Mathématiques*, 1(1), 11–59.
- Brown, J. S. & VanLehn, K. (1980). Repair theory: A generative theory of bugs in procedural skills. *Cognitive Science*, 4, 379–426.
- Fischbein, E., Deri, M., Nello, M. S. & Marino, M. S. (1985). The role of implicit models in solving verbal problems in multiplication and division. *Journal for Research in Mathematics Education*, 16(1), 3–17.
- Graeber, A. O. & Tirosh, D. (1990). Insights fourth and fifth graders bring to multiplication and division with decimals. *Educational Studies in Mathematics*, 21, 565–588.
- Graeber, A. O., Tirosh, D. & Glover, R. (1989). Preservice teachers' misconceptions in solving verbal problems in multiplication and division. *Journal for Research in Mathematics Education*, 20(1), 95–102.
- Hart, K. M. (dir.) (1981). *Children's Understanding of Mathematics: 11–16* (enquête CSMS). John Murray.
- Hiebert, J. & Wearne, D. (1985). A model of students' decimal computation procedures. *Cognition and Instruction*, 2(3–4), 175–205.
- Hiebert, J. & Wearne, D. (1986). Procedures over concepts: The acquisition of decimal number knowledge. In J. Hiebert (dir.), *Conceptual and Procedural Knowledge: The Case of Mathematics*. Erlbaum.
- Irwin, K. C. (2001). Using everyday knowledge of decimals to enhance understanding. *Journal for Research in Mathematics Education*, 32(4), 399–420.
- Moloney, K. & Stacey, K. (1997). Changes with age in students' conceptions of decimal notation. *Mathematics Education Research Journal*, 9(1), 25–38.
- Moss, J. & Case, R. (1999). Developing children's understanding of the rational numbers: A new model and an experimental curriculum. *Journal for Research in Mathematics Education*, 30(2), 122–147.
- Resnick, L. B., Nesher, P., Leonard, F., Magone, M., Omanson, S. & Peled, I. (1989). Conceptual bases of arithmetic errors: The case of decimal fractions. *Journal for Research in Mathematics Education*, 20(1), 8–27.
- Roche, A. (2005). Longer is larger — or is it? *Australian Primary Mathematics Classroom*, 10(3), 11–16.
- Sackur-Grisvard, C. & Léonard, F. (1985). Intermediate cognitive organizations in the process of learning a mathematical concept: The order of positive decimal numbers. *Cognition and Instruction*, 2(2), 157–174.
- Steinle, V. & Stacey, K. (1998). The incidence of misconceptions of decimal notation amongst students in grades 5 to 10. In *Proceedings of MERGA 21*, 548–555.
- Steinle, V. (2004). *Changes with age in students' misconceptions of decimal numbers* (thèse de doctorat, University of Melbourne — étude longitudinale, n = 3 204).
- Steinle, V. & Stacey, K. (2004). A longitudinal study of students' understanding of decimal notation: An overview and refined results. In *Proceedings of MERGA 27*, 541–548.
- Vamvakoussi, X. & Vosniadou, S. (2004). Understanding the structure of the set of rational numbers: A conceptual change approach. *Learning and Instruction*, 14, 453–467.
