# Méthodologie de fabrication d'un référentiel Atlas

**Statut** : Normatif — livrable A1 du Lot A · **Version** : 1.0 · **Date** : 2026-07-12
**Auteur** : cadrage produit (Nassim + Claude) — intègre les errata E1–E10 du Cadrage-LotA v1.1
**À lire avec** : `01_strategie/Cadrage-LotA-Extension-Contenu.md` (§3/A1), `02_technique/DataModel-KnowledgeGraph.md` (§1, §3), `02_technique/Architecture-Matiere-Pluggable.md` (contrat matière), `04_code/data/referentiel_fractions.json` (référentiel de référence), `03_referentiel/referentiel_decimals_draft.json` (première application de cette méthode).

---

## 0. Objet, portée, mode d'emploi

**Ce document est la doctrine.** Il décrit comment fabriquer un référentiel de compétences Atlas — nœuds, arêtes, priors, niveaux cognitifs, contextes d'items — de façon **réplicable et auditable par un tiers, sans le fondateur**. Chaque règle est accompagnée : (a) d'un **test opératoire** (une question fermée qu'un tiers peut appliquer seul), (b) d'au moins **un exemple fractions** (le référentiel de référence, 32 nœuds / 46 arêtes) et **un exemple décimaux** (le premier draft produit avec cette méthode, 14 nœuds / 26 arêtes).

**Ce que produit cette méthode** : un fichier JSON `{nodes, edges}` au format exact de `referentiel_fractions.json`, en statut DRAFT, prêt pour la double lecture experte (§A1.8). Rien ne passe `active` sans cette revue.

**Ce que cette méthode ne couvre pas** : le mapping curriculaire (Lot B — le référentiel est neutre, le curriculum est une projection), la calibration empirique des priors (Lot C — cette méthode pose des priors experts), la production d'items (A4–A6).

**Avertissement d'honnêteté (obligatoire, à recopier dans tout artefact produit)** : les `difficulty_prior` et `correlation_strength` fixés par cette méthode sont des **points de départ experts**. Ils ne sont ni un standard, ni une mesure. Ils seront ré-estimés sur trafic réel (Lot C). Aucun référentiel produit sous cette méthode ne doit être présenté comme « calibré ».

**Ordre des opérations** (chaque étape correspond à une section) :
1. Découper le domaine en nœuds (A1.1), les nommer (A1.2).
2. Tracer les arêtes, typer HARD/SOFT, fixer les poids (A1.3).
3. Fixer les `difficulty_prior` (A1.4) et les niveaux cognitifs (A1.5).
4. Documenter l'espace de contextes d'items par nœud (A1.6).
5. Vérifier les contraintes structurelles sur le graphe complet, ponts inclus (A1.7).
6. Soumettre à la double lecture experte (A1.8). Le gate A1.8 est bloquant.

---

## A1.1 — Règle de granularité

### Règle normative

> **1 nœud = 1 geste cognitif atomique + 1 contrainte procédurale principale maximum.**

- Une variation qui change la **stratégie de résolution** → **nouveau nœud**.
- Une variation qui ne change que le **contexte ou la difficulté** → **tag d'item** (`item_contexts`, cf. A1.6), **jamais** un nœud.

### Tests opératoires

| # | Question | Si OUI | Si NON |
|---|---|---|---|
| T1 | « Ce nœud demande-t-il **deux stratégies différentes** pour être réussi ? » | **Scinder** en deux nœuds | Garder un seul nœud |
| T2 | « Cette variation change-t-elle fortement le taux de réussite **sans changer la stratégie** ? » | **Tag** d'item, pas de nœud | Ni tag prioritaire ni nœud |
| T3 | « Un élève peut-il maîtriser la variante A et échouer systématiquement la variante B parce qu'il lui manque un **geste** (pas de l'entraînement) ? » | Scinder | Tag |

### Exemples

- **Fractions (scission justifiée)** : `MATH.G3.NF.ADD_SAME_NOSIMP` vs `MATH.G4.NF.ADD_SAME_SIMPLIFY`. Simplifier le résultat est un geste à part entière, avec son propre prérequis (`SIMPLIFY_FRACTION`) : T1 → OUI, deux nœuds.
- **Fractions (tag, pas de nœud)** : dénominateur 4 vs 8 dans `NAME_FRACTION_VISUAL` → `item_contexts: ["denominator<=4", "denominator<=6", ...]`. Même geste, contexte plus dur : T2 → tag.
- **Décimaux (scission justifiée)** : `MATH.G5.NBT.MULT_DECIMAL_WHOLE` vs `MATH.G5.NBT.MULT_DECIMAL_DECIMAL`. Multiplier deux décimaux exige le comptage des décimales au produit et le raisonnement « le produit peut être plus petit que les facteurs » — stratégie distincte : deux nœuds, liés par un HARD (0.8).
- **Décimaux (tag, pas de nœud)** : addition avec ou sans alignement de places différentes → `MATH.G5.NBT.ADD_DECIMALS`, contexts `["same number of places", "different number of places (alignment)", "carrying", ...]`. Même algorithme, charge différente : tag.

### Anti-pattern interdit

**La fragmentation par contexte** : créer `ADD_DECIMALS_TENTHS`, `ADD_DECIMALS_HUNDREDTHS`, `ADD_DECIMALS_MONEY`… Conséquence mécanique : explosion à plusieurs milliers de micro-skills, densité de données par nœud trop faible pour calibrer, production d'items ingérable. Le moteur détecte les patterns de difficulté par contexte **via les tags** (`context_tags` sur l'item), pas via des nœuds. Ce point est un item explicite de la grille de revue (A1.8) — c'est le biais naturel des experts.

**Corollaire (data model §1)** : **1 item mesure 1 seule compétence** (`competency_id` unique). Pas de multi-skill au MVP.

---

## A1.2 — Convention de nommage

### Règle normative

> Code = `MATH.G{n}.{DOMAINE}.{SKILL}` — le `code` est l'identité de la compétence, stable et versionnable. Jamais l'UUID.

- `{n}` : grade (2–8 pour la roadmap actuelle).
- `{DOMAINE}` : aligné sur les domaines CCSS-M (décision structurante — le nommage interne parle déjà le langage d'un framework cible, ce qui simplifie le Lot B) :
  `NS` (number sense), `NF` (number & fractions), `NBT` (base ten / décimaux), `OA` (operations & algebraic thinking), `RP` (ratios & proportional), `EE` (expressions & equations), `G` (geometry), `MD` (measurement & data).
- `{SKILL}` : SCREAMING_SNAKE_CASE, forme **verbe + objet** (ou objet qualifié), sans abréviation opaque, stable dans le temps.

### Test opératoire

1. Le code matche la regex `^MATH\.G[2-8]\.(NS|NF|NBT|OA|RP|EE|G|MD)\.[A-Z0-9_]+$` → sinon rejet.
2. Un enseignant qui lit le `{SKILL}` sans documentation devine le geste évalué → sinon renommer.
3. Le code est unique dans le graphe combiné (tous domaines) → contrainte `unique` en base sur `competency.code`.
4. Renommer un code actif est **interdit** (les items et le crosswalk pointent dessus) : on déprécie (`status=deprecated`) et on crée.

### Exemples

- **Fractions** : `MATH.G4.NF.ADD_UNLIKE_LCM` — grade 4, domaine fractions, « additionner des fractions à dénominateurs différents nécessitant le PPCM ». Lisible à l'œil, mappable CCSS-M 4.NF/5.NF.
- **Décimaux** : `MATH.G5.NBT.MULT_DIV_POW10` — grade 5, base ten, « multiplier/diviser un décimal par une puissance de dix ». Le domaine `NBT` a été choisi (et non `NF`) parce que c'est là que CCSS-M range les décimaux : le crosswalk B en hérite gratuitement.

---

## A1.3 — Arêtes : décision HARD vs SOFT et fixation du poids

### Règle normative

Une arête `source → target` (`competency_prerequisite`, data model §3.2) porte : `edge_type` (HARD | SOFT), `correlation_strength ∈ [0,1]`, `weight_source=expert`, `weight_version=1`.

- **HARD = nécessité logique** : *impossible de réussir la cible sans maîtriser la source*. Un HARD sert à trois choses : la propagation de mesure, le **routing** (ne pas servir B si A est échoué), et le **diagnostic causal** (la clôture amont des HARD donne la cause racine d'un échec).
- **SOFT = corrélation pédagogique ou empirique**, utile à la propagation, **sans blocage** pédagogique.

### Test opératoire (type d'arête)

> « Peut-on construire un item honnête de la **cible** qu'un élève réussirait tout en échouant **systématiquement** la source ? »
> - **NON** → HARD.
> - **OUI, mais les deux réussites sont corrélées en pratique** → SOFT.
> - **OUI, et la corrélation est faible (< 0.5)** → **pas d'arête**.

Contre-vérification obligatoire pour chaque HARD : imaginer l'élève qui échoue la source — le routing va lui **bloquer** la cible. Si ce blocage serait pédagogiquement absurde, l'arête n'est pas HARD.

### Grille d'élicitation du poids (ancres ordinales imposées)

Les experts choisissent une **ancre sémantique**, jamais un nombre au doigt mouillé :

| Poids | Sémantique HARD | Sémantique SOFT |
|---|---|---|
| 0.85–0.90 | Dépendance quasi-mécanique (la source est un composant de la cible) | — (interdit, plafond SOFT = 0.7) |
| 0.75–0.84 | Prérequis fort, contournable à la marge | — |
| 0.65–0.74 | Prérequis nécessaire mais partiellement | Corrélation forte (≤ 0.7) |
| 0.50–0.64 | **Interdit méthodologiquement** (errata E4, cf. ci-dessous) | Corrélation modérée |
| < 0.50 | Interdit | Corrélation faible → le plus souvent **pas d'arête** |

### Bornes normatives

- **Plancher HARD méthodologique : 0.65–0.70.** Justification (errata E4) : le diagnostic causal traite tous les HARD identiquement quel que soit leur poids — un HARD à 0.55 aurait un pouvoir de blocage diagnostique disproportionné par rapport à sa force réelle. Les HARD réels des fractions sont tous ∈ [0.70, 0.88]. Le plancher DB de 0.5 reste le garde-fou **technique** (contrainte de ré-estimation en Lot C), pas une licence méthodologique.
- **Plafond SOFT : 0.7.** Au-delà, se demander si ce n'est pas un HARD déguisé.
- **Monotonie partielle** : un HARD validé pédagogiquement ne peut pas être inversé ni requalifié SOFT par la ré-estimation empirique (Lot C).
- **Pas de doublon** : PK composite `(source_id, target_id)`.

### Exemples

- **Fractions, HARD fort** : `EQUAL_SHARES → HALVES_QUARTERS` (HARD 0.85). Identifier une moitié suppose de savoir partager en parts égales : composant quasi-mécanique.
- **Fractions, SOFT** : `MATH.G3.NS.MULT_FACTS → MATH.G4.NF.EQUIVALENCE_COMPUTE` (SOFT 0.58). Connaître ses tables aide fortement à générer des équivalences par multiplication, mais un élève peut compenser (calcul lent, doublements) : le test opératoire répond OUI → SOFT, pas de blocage de routing.
- **Décimaux, HARD** : `PLACE_VALUE_TENTHS → PLACE_VALUE_HUNDREDTHS` (HARD 0.85). On ne conçoit pas la place des centièmes sans celle des dixièmes.
- **Décimaux, SOFT** : `ADD_DECIMALS → SUB_DECIMALS` (SOFT 0.65). Les deux partagent l'alignement sur la virgule (corrélation forte), mais la soustraction ne **requiert** pas logiquement l'addition — un blocage de routing serait abusif.

---

## A1.4 — Fixation du `difficulty_prior`

### Règle normative : méthode en 3 temps

**Temps 1 — Ligne de base par grade.** Ancrer la médiane de grade du nouveau domaine sur l'échelle interne Elo [0, 4000] (centrée 1500), en utilisant les repères **observés en base** sur les fractions (errata E2) :

| Grade | Médiane fractions (observée en base) |
|---|---|
| G2 | **1200** |
| G3 | **1480** |
| G4 | **1660** |
| G5 | **1900** |

Ces repères sont des **conventions expertes**, pas des mesures (cf. avertissement §0). Un nouveau domaine peut s'écarter de la médiane fractions du même grade **si l'écart est argumenté par écrit** et soumis à l'arbitrage de la revue (A1.8).

**Temps 2 — Ajustement cognitif, à l'intérieur du grade.** RECALL **abaisse** le prior sous la médiane de grade ; REASON le **relève** ; APPLY gravite autour. Ordre de grandeur observé sur les deux corpus : **±50 à 160 Elo** autour de la médiane (fractions : `MULT_FACTS` RECALL à −160 de la médiane G3 ; décimaux : `COMPARE_DECIMALS` REASON à +80 de la médiane G4).

**Temps 3 — Ajustement par position dans la chaîne.** Plus un nœud est **aval** (profond dans le DAG, loin des racines), plus son prior monte. Deux nœuds de même grade et même niveau cognitif ne devraient pas avoir le même prior si l'un est un prérequis de l'autre.

### Tests opératoires

1. La médiane des priors du domaine, par grade, est à ±100 Elo du repère fractions du même grade — **ou** l'écart est justifié par écrit (nature des nœuds, position dans le curriculum) et listé comme point d'arbitrage de revue.
2. Pour toute arête HARD `A → B` du même domaine : `prior(B) > prior(A)` (la cible est plus dure que son prérequis). Exception tolérée et documentée pour les ponts inter-domaines et les ponts inter-grades.
3. Aucun prior hors [0, 4000] ; aucun prior identique pour deux nœuds reliés par un HARD.

### Dérivation du prior d'item (contrat matière pluggable)

Le prior de **nœud** est une graine ; le prior d'**item** en dérive via la fonction de complexité du domaine (cf. A1.6) et la couche générique `src/items/difficulty.py` :

```
prior_item = prior_compétence + (complexité − 0.5) × 2 × 250
```

soit exactement `difficulty_from_score(competency_prior, complexity, band=DEFAULT_BAND=250)` — l'item module le prior de sa compétence de ±250 Elo selon sa complexité structurelle ∈ [0,1], borné à [0, 4000]. Le moteur Elo affine ensuite `difficulty_elo` avec le trafic (burn-in 20 réponses, difficulté gelée au prior).

### Exemples

- **Fractions** : `MULT_FACTS` (G3, RECALL, proche racine) = **1320**, sous la médiane G3 (1480) — temps 2 et 3 tirent vers le bas. `ADD_UNLIKE_FULL` (G5, REASON, 10ᵉ maillon de la plus longue chaîne) = **1950**, au-dessus de la médiane G5 (1900).
- **Décimaux** : `PLACE_VALUE_TENTHS` (G4, RECALL, racine locale du domaine) = **1520**, nettement sous la médiane G4 ; `DIV_DECIMAL_WHOLE` (G5, REASON, aval) = **1950**. Médianes du draft : G4 = 1620, G5 = 1890. L'écart G4 décimaux (1620) vs G4 fractions (1660) est **documenté comme point d'arbitrage** de revue (nœuds d'entrée de domaine, CCSS 4.NF.C) — c'est l'application du test opératoire n°1.

---

## A1.5 — Niveau cognitif (RECALL / APPLY / REASON, aligné TIMSS)

### Définitions opérationnelles

| Niveau | Équivalent TIMSS | Définition | Heuristique d'attribution |
|---|---|---|---|
| **RECALL** | *Knowing* | Restituer un fait, une définition, une procédure figée | « La réponse est-elle stockée telle quelle en mémoire (fait, nom de place, table) ? » |
| **APPLY** | *Applying* | Exécuter une procédure connue sur un cas standard | « L'élève sait-il **quoi faire** dès la lecture, la difficulté étant l'exécution ? » |
| **REASON** | *Reasoning* | Choisir/combiner des stratégies, transférer, justifier | « L'élève doit-il **choisir** entre plusieurs stratégies, ou raisonner sur la magnitude/structure ? » |

### Test opératoire

Appliquer les trois questions dans l'ordre RECALL → APPLY → REASON ; le premier OUI gagne. En cas d'hésitation APPLY/REASON : si l'item type peut être réussi en déroulant un algorithme unique sans décision, c'est APPLY.

### Contrainte de répartition

Cible à surveiller par domaine : **≥ 2 REASON par grade** pour que le diagnostic ait du grain, sans forcer artificiellement. Repères : fractions = 18 APPLY / 12 REASON / 2 RECALL (penche APPLY) ; décimaux draft = 9 APPLY / 4 REASON / 1 RECALL (≥ 2 REASON par grade : respecté). La répartition est déclarée dans le dossier de revue.

### Exemples

- **Fractions** : `MULT_FACTS` = RECALL (fait mémorisé) ; `ADD_SAME_SIMPLIFY` = APPLY (procédure connue) ; `COMPARE_BENCHMARK` = REASON (choisir le bon repère 1/2 ou 1 et raisonner).
- **Décimaux** : `PLACE_VALUE_TENTHS` = RECALL (nommer la place) ; `ROUND_DECIMAL` = APPLY (procédure de troncature/arrondi) ; `MULT_DECIMAL_DECIMAL` = REASON (raisonner sur la place de la virgule et sur « le produit peut être plus petit que les facteurs »).

---

## A1.6 — Définition des `item_contexts` (et contrat matière pluggable)

### Règle normative

Chaque nœud déclare son **espace de contextes** : les dimensions de variation qui produisent la variété d'items **sans** créer de nœud (le versant positif de la règle A1.1). Documenter, par famille de compétences, au moins ces quatre dimensions :

1. **Magnitude / paramètres numériques** — ex. `denominator<=8`, nombre de décimales.
2. **Représentation** — symbolique vs visuelle : `bar model`, `circle model`, `number line`, `expanded form`.
3. **Pièges classiques** — les misconceptions du domaine, encodées comme contextes : `already simplified (trap)`, `trailing zero trap`.
4. **Registre** — habillage porteur de sens local : `money model (dirhams/fils)`, `unit conversion`.

### Test opératoire

1. Chaque nœud a **≥ 3 contextes** distincts (sinon impossible de produire ~10 items étalés en difficulté, cf. volumétrie A7).
2. Chaque contexte est **générable** : il correspond à un paramètre que le générateur déterministe du domaine sait produire et à une feature que `features()` sait extraire. Un contexte non générable est retiré ou reporté.
3. Aucun contexte n'aurait dû être un nœud : repasser le test T1 de A1.1 sur chaque contexte.

### Absorption du contrat « matière pluggable » (errata E6)

Les `item_contexts` du référentiel sont la **spécification amont** du module matière. Pour brancher un domaine, fournir exactement **trois choses** (contrat de `Architecture-Matiere-Pluggable.md`, miroir de `src/items/deterministic.py`) :

1. **Générateurs de contenu** (`{DOMAINE}_GENERATORS`) — produisent des items `{stem, options, answer}` corrects. Déterministe quand c'est possible (correction garantie — pour les décimaux : arithmétique `Decimal` Python, jamais de flottant) ; le LLM peut habiller, **jamais** décider la vérité de la réponse.
2. **Extracteur de features** `{domaine}_features(content) → context_tags` — dict de features porteuses de sens, propres à la matière (fractions : `needs_lcm`, `simplify_required`, `max_denominator` ; décimaux : nombre de décimales, besoin d'alignement, zéro non significatif…). Ce sont les `context_tags` JSONB de l'item.
3. **Fonction de complexité** `{domaine}_complexity(features) → [0,1]` — combine les features normalisées via la couche générique `weighted_score(features, {DOMAINE}_FEATURE_WEIGHTS)` ; le dict de poids **est** le savoir-métier.

La couche générique (`difficulty_from_score`, `weighted_score`, modèle `Item`, workflow de revue/AR/quarantaine, sélection, moteur Elo) **ne change jamais** d'une matière à l'autre. Le rédacteur du référentiel doit donc vérifier, nœud par nœud, que ses `item_contexts` se traduisent en features extractibles — sinon le contexte est décoratif.

### Exemples

- **Fractions** : `SIMPLIFY_FRACTION` → contexts `["common factor<=5", "gcd needed", "already simplified (trap)"]`. Côté module : `fraction_features` extrait `simplify_required`, `needs_lcm`… pondérées par `FRACTION_FEATURE_WEIGHTS` dans `fraction_complexity` (`src/items/deterministic.py`).
- **Décimaux** : `COMPARE_DECIMALS` → contexts `["same number of places", "different number of places (longer-is-larger trap)", "trailing zero trap", "ordering 3+ numbers"]`. Chaque contexte active une feature de `decimal_complexity` (spec A5 : nombre de places différentes = poids 0.20, zéro non significatif = 0.10…) et une misconception du catalogue A4. Le registre local `money model (dirhams/fils)` apparaît dès `PLACE_VALUE_TENTHS`.

**Non-conformité connue du référentiel de référence** (à traiter en revue, pas à imiter) : deux nœuds fractions n'ont que **2** contextes — `MATH.G5.NF.MIXED_TO_IMPROPER` (`["whole<=5", "denominator<=10"]`) et `MATH.G4.NF.SUB_SAME_SIMPLIFY` (`["result simplifiable", "denominator<=12"]`). Le test opératoire n°1 les rejette ; ils sont antérieurs à cette doctrine et à enrichir lors de la prochaine revue fractions. Le draft décimaux, produit sous cette méthode, est conforme (4–5 contextes par nœud).

---

## A1.7 — Contraintes structurelles du graphe

### Règles normatives et tests opératoires

| # | Contrainte | Norme | Test opératoire |
|---|---|---|---|
| S1 | **DAG strict** | Aucun cycle, y compris sur le **graphe combiné** (nouveau domaine + domaines existants + ponts) | Exécuter le validateur du repo (`src/graph/validator.py`) sur le graphe combiné avant toute revue. Fait pour le draft décimaux : fractions+décimaux, 0 cycle. |
| S2 | **Densité intra-domaine** | Cible **1.3–1.6 arête/nœud en intra-domaine** ; les **ponts inter-domaines sont comptés à part** (errata E5). < 1.0 = graphe sous-connecté (propagation inutile) ; > ~2.0 = sur-spécification | Calculer `arêtes_intra / nœuds` et `arêtes_totales / nœuds`, reporter les deux chiffres dans le dossier de revue |
| S3 | **Profondeur de chaîne** | Documenter la plus longue chaîne HARD du domaine. Longue chaîne = pouvoir diagnostique concentré mais propagation fragile (1 saut ne remonte qu'un cran) | Lister la chaîne nœud par nœud dans le dossier de revue |
| S4 | **Racines** | Tout nœud non-racine a ≥ 1 arête entrante. Les **racines de sous-domaine** sont explicites, documentées, avec leur prérequis futur nommé | Lister les nœuds sans arête entrante ; chacun est soit une racine assumée, soit une erreur |
| S5 | **Ponts inter-domaines** | Tout nouveau domaine doit se relier au graphe existant (sinon la propagation ne circule pas entre domaines). Les codes cibles des ponts sont **vérifiés contre la base** (pas de code inventé) | Chaque code de pont existe en base (`competency.code`) ; les ponts passent le test HARD/SOFT de A1.3 |
| S6 | **Bornes de poids** | HARD ∈ [0.65, 0.90] (plancher méthodologique E4), SOFT ∈ (0, 0.70] | Scan automatique du JSON |

### Exemples

- **Fractions** : densité 46/32 ≈ **1.44** (tout intra, premier domaine, 0 pont) — dans la cible. Plus longue chaîne HARD : **11 nœuds** (errata E3) : `EQUAL_SHARES → HALVES_QUARTERS → NAME_FRACTION_VISUAL → UNIT_FRACTION → FRACTION_AS_PART → EQUIVALENCE_VISUAL → EQUIVALENCE_COMPUTE → ADD_UNLIKE_SIMPLE → ADD_UNLIKE_LCM → ADD_UNLIKE_FULL → ADD_MIXED`. Racine globale : `EQUAL_SHARES`.
- **Décimaux** : densité **intra 21/14 = 1.50** ✅ ; global (ponts compris) 26/14 = 1.86 — conforme à la convention E5 (les 5 ponts sont comptés à part, ils enrichissent la propagation inter-domaines sans « sur-spécifier » l'intra). Plus longue chaîne HARD **intra-domaine : 4 nœuds** (`PLACE_VALUE_TENTHS → PLACE_VALUE_HUNDREDTHS → PLACE_VALUE_THOUSANDTHS → MULT_DIV_POW10`) ; sur le **graphe combiné**, elle atteint **9 nœuds** via le pont `FRACTION_AS_PART → PLACE_VALUE_TENTHS` — c'est exactement ce que S3 demande de documenter, aux deux échelles. Ponts vérifiés contre les codes réels en base : `MATH.G3.NF.FRACTION_AS_PART → PLACE_VALUE_TENTHS` (HARD 0.75) et `→ DECIMAL_AS_FRACTION` (HARD 0.8), `MATH.G4.NF.EQUIVALENCE_COMPUTE → DECIMAL_AS_FRACTION` (HARD 0.72), `MATH.G3.NF.NUMBER_LINE_PLACE → DECIMAL_NUMBER_LINE` (SOFT 0.6), `MATH.G3.NF.COMPARE_SAME_DENOM → COMPARE_DECIMALS` (SOFT 0.55). Racine locale documentée : `PLACE_VALUE_TENTHS`, en attente du futur domaine place-value entier (elle a déjà un pont fraction entrant — S4 satisfait sur le graphe combiné).

---

## A1.8 — Protocole de revue experte (grille + double lecture)

### Processus (normatif)

1. **Double lecture indépendante** : (a) un **didacticien mathématiques**, (b) un **enseignant primaire EAU en exercice** (idéalement issu d'une école pilote). Chacun remplit la grille **seul**, sans voir l'autre.
2. **Réconciliation** : les désaccords sont listés et arbitrés en séance ; chaque arbitrage est **journalisé** (registre ci-dessous). Un désaccord non tranché = nœud/arête maintenu en `draft`.
3. **Gate bloquant** : **aucun nœud ne passe `active` sans double validation experte.** Correspond au gate G1 du Lot A (A8).

### Grille de revue — checklist par NŒUD

Pour chaque nœud, cocher les 6 points ; un seul échec = retour en rédaction.

- [ ] **N1 Granularité** : 1 geste cognitif, 1 contrainte procédurale max ; les tests T1–T3 (A1.1) répondent dans le bon sens ; pas de fragmentation par contexte.
- [ ] **N2 Nommage** : regex A1.2 respectée ; `{SKILL}` compréhensible sans doc ; domaine CCSS-M correct.
- [ ] **N3 Prior plausible** : cohérent avec la médiane de grade (repères G2=1200 / G3=1480 / G4=1660 / G5=1900), l'ajustement cognitif et la position dans la chaîne ; tout écart est argumenté par écrit.
- [ ] **N4 Cognitif correct** : RECALL/APPLY/REASON attribué via l'heuristique A1.5 ; contribue à ≥ 2 REASON par grade.
- [ ] **N5 Contextes suffisants** : ≥ 3 `item_contexts`, tous générables (features extractibles par le module matière), couvrant magnitude / représentation / pièges / registre quand pertinent.
- [ ] **N6 Labels bilingues** : `label_en` et `label_ar` présents, fidèles, terminologie AR conforme au glossaire du domaine (registre scolaire MoE).

### Grille de revue — checklist par ARÊTE

- [ ] **E1 Type justifié** : le test opératoire A1.3 (« item de la cible réussi malgré échec systématique de la source ? ») confirme HARD ou SOFT ; le blocage de routing d'un HARD est pédagogiquement défendable.
- [ ] **E2 Poids dans la fourchette** : HARD ∈ [0.65, 0.90], SOFT ≤ 0.70 ; le poids correspond à une **ancre sémantique** de la grille A1.3, pas à un chiffre libre.
- [ ] **E3 Pas de cycle** : le validateur a été exécuté sur le graphe combiné (S1) — vérifier que le rapport est joint au dossier.
- [ ] **E4 Sens du prior** : `prior(cible) > prior(source)` pour les HARD intra-domaine, ou exception documentée.

### Grille de revue — checklist GRAPHE (une fois par domaine)

- [ ] **G1** Densité intra-domaine ∈ [1.3, 1.6] (tolérance dure : [1.0, 2.0]) ; ponts comptés à part et listés.
- [ ] **G2** Plus longue chaîne HARD documentée (fractions : 11 — repère de comparaison).
- [ ] **G3** Toutes les racines sont assumées et documentées, avec prérequis futur nommé le cas échéant.
- [ ] **G4** Tous les ponts pointent vers des codes existants en base, et passent E1–E2.
- [ ] **G5** Répartition cognitive déclarée ; ≥ 2 REASON par grade.
- [ ] **G6** Médianes de prior par grade déclarées et comparées aux repères fractions ; écarts listés comme points d'arbitrage.
- [ ] **G7** L'avertissement « priors experts, non mesurés » figure dans le document livré.

### Registre d'arbitrage (modèle à recopier)

| Date | Objet (code nœud/arête) | Position lecteur A (didacticien) | Position lecteur B (enseignant EAU) | Arbitrage retenu | Motif |
|---|---|---|---|---|---|
| … | … | … | … | … | … |

### Exemples de points d'arbitrage réels (à traiter tels quels en revue du draft décimaux)

- **Décimaux — médiane G4** : 1620 (décimaux) vs 1660 (fractions G4). Position rédacteur : défendable (nœuds d'entrée de domaine, CCSS 4.NF.C). À confirmer ou corriger par le didacticien (checklist N3/G6).
- **Fractions — arête inversée en grade** : `MATH.G5.NF.IMPROPER_TO_MIXED → MATH.G4.NF.ADD_SAME_IMPROPER` (HARD 0.7) : un nœud G5 prérequis d'un nœud G4. Cas d'école pour E4 — l'exception est réelle (convertir en nombre mixte est requis pour finaliser l'addition à résultat impropre) et doit rester documentée, pas « corrigée » silencieusement.

---

## Annexe — Pipeline récapitulatif et definition of done d'un référentiel-draft

**Entrée** : un domaine décidé (via la matrice A2), la liste des grades couverts.
**Sortie** : `03_referentiel/referentiel_{domaine}_draft.json` au format `{nodes, edges}` :

```json
{
  "nodes": [{ "code", "label_en", "label_ar", "grade", "difficulty_prior",
              "cognitive_level", "item_contexts": [] }],
  "edges": [["CODE_SOURCE", "CODE_CIBLE", "HARD|SOFT", 0.75]]
}
```

**Definition of done du draft (avant revue A1.8)** :
- [ ] Tous les nœuds passent les tests A1.1 (granularité) et A1.2 (nommage regex).
- [ ] Toutes les arêtes typées et pondérées via la grille A1.3 ; HARD ≥ 0.65, SOFT ≤ 0.70.
- [ ] Priors fixés par la méthode 3 temps A1.4 ; médianes par grade calculées et comparées aux repères.
- [ ] Niveaux cognitifs attribués (A1.5) ; ≥ 2 REASON par grade.
- [ ] ≥ 3 `item_contexts` générables par nœud (A1.6) ; traduction en features vérifiée avec le contrat matière.
- [ ] Validateur DAG exécuté sur le graphe **combiné** ; densité intra et globale calculées ; racines et ponts documentés (A1.7).
- [ ] Avertissement « priors experts, non mesurés » inscrit dans le livrable.
- [ ] Dossier de revue préparé : chaînes, médianes, répartition cognitive, points d'arbitrage pré-identifiés.

**Après revue** : arbitrages journalisés → corrections → re-validation DAG → seed idempotent en base (gate G4 du Lot A) → simulation cohorte (gate G5, `simulate_cohort.py` une fois paramétré — errata E10). Les priors restent `weight_source=expert` jusqu'au Lot C.

*Fin du document normatif. Toute dérogation à une règle de ce document se journalise dans le registre d'arbitrage et se reporte dans la version suivante de la méthodologie.*
