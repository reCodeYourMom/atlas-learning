# Manuel Technique de Mesure — Atlas Learning

**Livrable C1 du Lot C (Cadrage-LotC-Mesure-Defendable.md §3/C1)** · Version 1.0 · 2026-07-11
**Statut** : v1 — à relire en interne, puis revue externe recommandée (C6).
**Sources normatives** : chaque constante et formule de ce manuel est extraite du code de production et cite son fichier source. Fichiers de référence : `src/engine/elo.py`, `src/restitution/scale.py`, `src/restitution/diagnosis.py`, `src/api/views_service.py`, `src/items/quarantine.py`, `src/items/difficulty.py`, `scripts/simulate_cohort.py`, `data/referentiel_fractions.json` (chemin racine : `atlas_dossier/04_code/`).
**Public** : psychométricien, Head of Assessment, auditeur de due diligence. L'objectif est qu'un spécialiste de la mesure puisse auditer Atlas **dans son propre langage (Rasch/IRT), sans lire notre code**.

---

## Executive Summary (English)

Atlas Learning estimates student ability and item difficulty with an **Elo rating engine** operating on a bounded scale [0, 4000] centered at 1500 (`src/engine/elo.py`). This document establishes the psychometric defensibility of that engine in six parts.

**1. The model is mathematically identical to the Rasch model.** The implemented response function is `P(correct) = 1/(1 + 10^((b−a)/400))`. Under the exact change of variable `θ = (Elo − 1500)·ln(10)/400`, this is *algebraically equal* — not approximately equal — to the Rasch item response function `P = 1/(1 + e^−(θ−β))`. One logit ≈ **173.7178** Elo points; 400 Elo points = ln(10) ≈ **2.3026** logits. Every Rasch/IRT statistic (information, standard errors, fit) therefore transposes mechanically to the Atlas scale. Hand-checked numerical examples are provided in §1.4.

**2. The update dynamic is a stochastic approximation of Rasch maximum likelihood.** The Elo update `a ← a + K·(score − P)` is a Robbins–Monro stochastic gradient ascent step on the Rasch log-likelihood, whose score function is exactly `(score − P)`. Step sizes: K = 32 for a student's first 10 direct responses, then 16; item K = 0 during a 20-response burn-in (difficulty frozen at its generator-calibrated prior), then `32/(1 + n/30)`. Outside burn-in and outside the [0, 4000] clamp, updates satisfy the conservation identity `Δability/K_student + Δdifficulty/K_item = 0`. This design follows established educational-measurement precedents: Klinkenberg, Straatemeier & van der Maas (2011, Math Garden), Pelánek (2016), Brinkhuis & Maris, and Glickman's Glicko for the confidence/RD analogy.

**3. Confidence maps to a standard error.** The reported confidence is `c(n) = 1 − e^(−n/8)` over the number of *direct* responses (c(10) ≈ 0.71, c(20) ≈ 0.92). Through the Rasch bridge and Fisher information `I(θ) = Σ p(1−p)`, n near-adaptive responses give SE(θ̂) ≈ `2/√n` logits ≈ `347.4/√n` Elo points. The UI's ±150-Elo uncertainty band, triggered when confidence < 0.5 (i.e. n ≤ 5), matches the model-based SE at n = 5 (≈ 155 Elo) — the band is justified, not arbitrary.

**4. Inference never masquerades as measurement.** Propagation to graph neighbors is damped (`Δ × edge_weight × 0.4`), one hop only, never toward a more confident node, and never increments the direct-response counter. The UI guard requires ability ≥ 1500 **and** at least one direct response before displaying "mastered" (`src/api/views_service.py`).

**5. Item quality control is an item-fit procedure.** An active item is quarantined (reversibly, with an audit trail) when, after ≥ 30 responses, its observed success rate diverges from the model-expected rate by more than 0.40 — a deliberately conservative residual test (> 4 binomial SDs at n = 30).

**6. Limits are stated, not hidden** (§6): expert priors and expert restitution anchors not yet empirically calibrated, no real-cohort data yet (validation is synthetic), no linguistic-equity evidence until `Response.language` is logged (C-0) and the pilot runs, and an expert prerequisite graph not yet empirically validated. The claims policy (livrable C5) restricts what may be asserted at each maturity stage.

---

## 0. Objet, conventions et notation

| Symbole | Sens | Échelle |
|---|---|---|
| `a` | ability élève (par compétence) | Elo [0, 4000] |
| `b` | difficulté item | Elo [0, 4000] |
| `θ`, `β` | ability / difficulté transposées | logits |
| `P` ou `E` | probabilité de réussite attendue | [0, 1] |
| `s` | score observé (1 = correct, 0 = incorrect) | {0, 1} |
| `n` | nombre de réponses **directes** de l'élève sur la compétence (`n_direct`) | ℕ |
| `m` | nombre de réponses reçues par l'item (`n_responses`) | ℕ |
| `c(n)` | confiance de l'estimation | [0, 1] |

Le moteur (`src/engine/elo.py`) est un module de **mathématiques pures** : fonctions déterministes, sans accès base de données ni LLM, testables au chiffre près. L'échelle Elo est bornée à **[0, 4000]**, centrée **1500** (`ELO_MIN`, `ELO_MAX`, elo.py). Chaque élève porte une ability *par compétence* (32 compétences dans le référentiel fractions v1) : le modèle est unidimensionnel *par nœud*, pas globalement.

---

## 1. C1.1 — Le modèle et son pont exact vers Rasch

### 1.1 Fonction de réponse implémentée

Le code de production (`expected_score`, `src/engine/elo.py`) implémente :

```
P(correct | a, b) = 1 / (1 + 10^((b − a) / 400))
```

C'est la fonction d'espérance Elo classique (Elo, 1978), utilisée ici comme **modèle de réponse à l'item** : la probabilité qu'un élève d'ability `a` réussisse un item de difficulté `b`.

### 1.2 Dérivation complète de l'identité P_Elo = P_Rasch

Le modèle de Rasch (Rasch, 1960) pose, en logits :

```
P_Rasch(correct | θ, β) = e^(θ−β) / (1 + e^(θ−β)) = 1 / (1 + e^−(θ−β))
```

**Étape 1 — réécrire la base 10 en base e.** Pour tout x, `10^x = e^(x·ln 10)`. Donc :

```
P_Elo = 1 / (1 + 10^((b−a)/400))
      = 1 / (1 + e^((b−a)·ln(10)/400))
      = 1 / (1 + e^−((a−b)·ln(10)/400))
```

**Étape 2 — changement de variable affine.** Posons, avec le centre d'échelle 1500 :

```
θ = (a − 1500) · ln(10)/400        β = (b − 1500) · ln(10)/400
```

Alors :

```
θ − β = (a − 1500)·ln(10)/400 − (b − 1500)·ln(10)/400 = (a − b)·ln(10)/400
```

(le centre 1500 s'élimine — n'importe quel centre donne la même identité ; 1500 est choisi pour que le centre de l'échelle Elo corresponde à θ = 0).

**Étape 3 — substitution.**

```
P_Elo = 1 / (1 + e^−(θ−β)) = P_Rasch(θ, β)
```

**Conclusion.** L'identité est **algébrique et exacte** — ce n'est pas une approximation. Le moteur Atlas *est* un modèle de Rasch reparamétré sur une échelle affine. Par conséquent, **toute** statistique du cadre Rasch/IRT (information de Fisher, erreur-type, statistiques de fit, courbes caractéristiques d'item, equating) se transpose mécaniquement à l'échelle Atlas par la relation linéaire ci-dessus. Un auditeur peut donc analyser le journal de réponses Atlas avec n'importe quel outil Rasch standard (WINSTEPS, `eRm`, `mirt`, `TAM`) après conversion linéaire des paramètres.

*Exigence de test (Cadrage C1) : la conversion aller-retour Elo↔logit doit être couverte par un test unitaire à tolérance 1e-9.*

### 1.3 Table de conversion

Constante fondamentale : **1 logit = 400/ln(10) ≈ 173.7178 points Elo** ; réciproquement **400 points Elo = ln(10) ≈ 2.3026 logits**.

| Elo (a) | θ (logits) | | Δ Elo | Δ logits |
|---|---|---|---|---|
| 0 (ELO_MIN) | −8.635 | | 100 | 0.576 |
| 1000 | −2.878 | | **150 (bande UI)** | **0.863** |
| 1300 | −1.151 | | 173.72 | 1.000 |
| 1500 (centre) | 0.000 | | 200 | 1.151 |
| 1800 | +1.727 | | 400 | 2.303 |
| 2100 | +3.454 | | 500 | 2.878 |
| 4000 (ELO_MAX) | +14.391 | | | |

La bande d'incertitude affichée par la restitution (±150 Elo, `src/restitution/scale.py`) vaut donc **±0.8635 logit** — voir §3.4 pour sa justification par l'erreur-type. Le clamp [0, 4000] correspond à un support en logits de [−8.64, +14.39], très au-delà de la plage utile de mesure (les ancres de restitution vont de 1000 à 2100, soit [−2.88, +3.45] logits).

### 1.4 Exemples numériques vérifiés à la main

Chaque ligne a été calculée indépendamment par les deux formules (Elo base 10, Rasch base e) ; les probabilités coïncident à la précision machine.

**Exemple 1 — élève au-dessus de l'item.** a = 1700, b = 1500.
- Voie Elo : `P = 1/(1 + 10^((1500−1700)/400)) = 1/(1 + 10^−0.5) = 1/(1 + 0.31623) = 0.7597`.
- Voie Rasch : θ = 200·ln(10)/400 = 1.15129 ; β = 0 ; `P = 1/(1 + e^−1.15129) = 0.7597`. ✅

**Exemple 2 — item au-dessus de l'élève.** a = 1500, b = 1800.
- Voie Elo : `P = 1/(1 + 10^(300/400)) = 1/(1 + 10^0.75) = 1/(1 + 5.6234) = 0.1510`.
- Voie Rasch : θ = 0 ; β = 1.72694 ; `P = 1/(1 + e^1.72694) = 0.1510`. ✅

**Exemple 3 — appariement parfait.** a = b = 1300 : les deux voies donnent P = 0.5 (θ = β = −1.15129). C'est le régime visé par une sélection adaptative — et celui qui maximise l'information (§3.2). ✅

**Exemple 4 — grand écart.** a = 2100, b = 1500 : `P = 1/(1 + 10^−1.5) = 0.9693` ; côté Rasch, θ = 3.45388, β = 0, même valeur. ✅

### 1.5 Restitution : de l'échelle interne aux repères lisibles

La couche de restitution (`src/restitution/scale.py`) est **strictement séparée du moteur** : une `AnchorTable` configurable convertit l'Elo en percentile et niveau par interpolation linéaire entre ancres, sans jamais toucher au moteur. Table par défaut (`DEFAULT_ANCHORS`, scale.py — **barème expert**, le code lui-même indique « à remplacer par cohorte réelle plus tard ») :

| Elo | θ (logits) | Percentile | Niveau |
|---|---|---|---|
| 1000 | −2.878 | 5 | G2 |
| 1300 | −1.151 | 25 | G3 |
| 1500 | 0.000 | 50 | G4 |
| 1800 | +1.727 | 75 | G5 |
| 2100 | +3.454 | 95 | G6 |

Si la confiance est < 0.5, la restitution affiche une **fourchette** de percentiles calculée à ±150 Elo (`restitute`, paramètres `confidence_threshold=0.5`, `band=150.0`, scale.py) au lieu d'un point. La justification statistique de ces deux constantes est donnée en §3.4. Le remplacement des ancres expertes par des ancres empiriques est l'objet du protocole de calibration (livrable C2) ; tant qu'il n'est pas exécuté, la politique de claims (C5, étage 0) interdit le mot « calibré ».

---

## 2. C1.2 — Dynamique d'estimation : Elo comme approximation stochastique du ML de Rasch

### 2.1 La règle de mise à jour

À chaque réponse, le moteur applique (`update_elo`, `src/engine/elo.py`) :

```
E  = P(correct | a, b)                    (expected_score)
Δ  = s − E                                (s ∈ {0,1})
a' = clamp[0,4000]( a + K_élève · Δ )
b' = clamp[0,4000]( b − K_item  · Δ )
```

**Interprétation en approximation stochastique.** Sous le modèle de Rasch, la log-vraisemblance d'une réponse est `ℓ(θ) = s·ln P + (1−s)·ln(1−P)` et sa dérivée (fonction score) vaut exactement `∂ℓ/∂θ = s − P`. La mise à jour Elo est donc un pas de **montée de gradient stochastique de type Robbins–Monro sur la vraisemblance de Rasch**, avec un pas `K·ln(10)/400` en logits (K = 32 → 0.184 logit/réponse ; K = 16 → 0.092). C'est l'interprétation standard de l'Elo en mesure éducative (Brinkhuis & Maris ; Pelánek, 2016) : un estimateur de maximum de vraisemblance incrémental, qui échange un léger surcroît de variance (pas constant non décroissant, cf. §2.2) contre la capacité à **suivre une ability qui évolue** — précisément le cas d'un élève qui apprend, où le ML statique de Rasch est mal posé.

### 2.2 K-factors élève : compromis vitesse/variance

`k_student` (elo.py) : **K = 32 tant que n_direct < 10, puis K = 16** (`K_NEW = 32`, `K_STABLE = 16`, `N_DIRECT_STABLE = 10`).

Choix assumé : **pas de gain décroissant en 1/n** (qui donnerait la convergence ML exacte pour une ability *fixe*, cf. condition de Robbins–Monro Σγₙ = ∞, Σγₙ² < ∞), mais un plancher K = 16. Justification : l'ability d'un élève en apprentissage n'est pas stationnaire ; un gain plancher maintient la réactivité du tracker (le système reste capable de suivre une progression), au prix d'une variance asymptotique non nulle — quantifiée et affichée via la confiance (§3). Ce schéma à deux régimes (grand K en phase d'accrochage, K réduit en régime établi) est celui de Math Garden (Klinkenberg et al., 2011) et de la pratique Elo générale.

### 2.3 K-factor item : burn-in puis décroissance

`k_item` (elo.py) :

```
K_item(m) = 0                    si m < 20     (ITEM_BURN_IN)
          = 32 / (1 + m/30)      sinon         (K_ITEM_BASE = 32, ITEM_HALFLIFE = 30)
```

Valeurs : K_item(20) = 19.2 ; K_item(30) = 16 ; K_item(60) ≈ 10.7 ; K_item(150) ≈ 5.3.

**Burn-in (m < 20) : la difficulté est GELÉE au prior.** Le `difficulty_prior` est calibré *par item* par le générateur déterministe (`difficulty_from_score`, `src/items/difficulty.py` : `prior_compétence + (complexité − 0.5) × 2 × 250`, complexité ∈ [0,1] fournie par la couche matière, borné à ±250 Elo autour du prior de la compétence). Ce signal est plus fiable qu'une poignée de réponses bruitées : sur une petite cohorte biaisée (ex. seuls les élèves forts répondent au début), même un K réduit ferait dériver l'item ; le gel est prévisible et testable (commentaire de conception, elo.py, revue 2026-07-07). Sur le plan psychométrique, c'est un **prior informatif à poids infini pendant 20 observations**, puis relâché.

**Décroissance hyperbolique ensuite.** `32/(1 + m/30)` décroît en ~1/m pour m grand : c'est la forme du gain qui rend l'itération équivalente à un estimateur ML au sens de Robbins–Monro — cohérent avec l'hypothèse qu'une difficulté d'item, contrairement à une ability d'élève, **est** stationnaire.

### 2.4 Invariant pondéré (conservation)

Hors clamp et hors burn-in, puisque `Δa = K_élève·Δ` et `Δb = −K_item·Δ` :

```
Δa / K_élève + Δb / K_item = Δ − Δ = 0
```

Cet invariant est documenté dans le code (docstring `update_elo`, elo.py) et **volontairement rompu** dans deux cas : (i) au clamp — borner l'échelle prime sur conserver la masse ; (ii) pendant le burn-in — K_item = 0, l'ability élève bouge normalement, la difficulté non. Il joue le rôle de la conservation de somme des ratings de l'Elo classique, généralisée aux K asymétriques.

**Exemple numérique vérifié (reproduit depuis `update_elo`).** a = 1500, b = 1600, réponse correcte, n_direct = 3 (→ K_élève = 32), m = 25 (→ K_item = 32/(1+25/30) = 17.4545) :
- E = 1/(1 + 10^(100/400)) = 0.35994 ; Δ = 1 − 0.35994 = 0.64006 ;
- a' = 1500 + 32 × 0.64006 = **1520.48** ; b' = 1600 − 17.4545 × 0.64006 = **1588.83** ;
- vérification de l'invariant : 20.482/32 + (−11.172)/17.4545 = 0.64006 − 0.64006 = 0 ✅ (écart machine ~3.6e-15).

### 2.5 Clamp [0, 4000]

`clamp_elo` (elo.py, revue 2026-07-07) : sans borne, une longue série de réponses anormales (triche, bug client, boucle de rejeu) fait dériver ability ou difficulté hors de l'échelle annoncée — et toute la sélection d'items avec. Le clamp est un garde-fou d'intégrité opérationnelle, pas un élément du modèle de mesure : dans la plage utile (§1.3), il est inactif. La rupture d'invariant à la borne est assumée et documentée.

### 2.6 Ancrage dans la littérature

Le dispositif n'est **pas une invention maison** ; chaque brique a un précédent publié :

- **Klinkenberg, S., Straatemeier, M., & van der Maas, H. L. J. (2011).** Computer adaptive practice of maths ability using a new item response model for on the fly ability and difficulty estimation. *Computers & Education*, 57(2), 1813–1824. — Le précédent K-12 à grande échelle (Math Garden) : Elo bilatéral élève/item en production sur des millions de réponses.
- **Pelánek, R. (2016).** Applications of the Elo rating system in adaptive educational systems. *Computers & Education*, 98, 169–179. — Revue de référence : choix des K, variantes, équivalence avec les modèles IRT, recommandations que ce moteur suit (K à deux régimes, décroissance côté item).
- **Brinkhuis, M. J. S., & Maris, G.** (rapports Cito ; et 2019, *Dynamic estimation in the extended marginal Rasch model with an application to mathematical computer-adaptive practice*, BJMSP). — Fondement formel : l'Elo comme chaîne de Markov de tracking d'un paramètre de Rasch, propriétés d'invariance et de suivi de tendance.
- **Glickman, M. E. (1999).** Parameter estimation in large dynamic paired comparison experiments. *JRSS-C*, 48(3), 377–394. — Glicko : la parenté conceptuelle de notre couple (ability, confiance) avec (rating, RD) ; notre `confidence(n)` joue le rôle d'un RD croissant en information (§3).
- **Rasch, G. (1960).** *Probabilistic Models for Some Intelligence and Attainment Tests.* — Le modèle cible du pont §1.
- **Elo, A. (1978).** *The Rating of Chessplayers, Past and Present.* — La fonction d'espérance et l'échelle en base 10/400.

---

## 3. C1.3 — De la confiance à l'erreur-type

### 3.1 La confiance implémentée

`confidence` (elo.py) :

```
c(n) = 1 − e^(−n/8)        (TAU = 8 ; borné [0,1] ; n = réponses DIRECTES)
```

Saturation exponentielle : **c(5) ≈ 0.46 ; c(10) ≈ 0.71 ; c(20) ≈ 0.92 ; c(30) ≈ 0.98**. Propriétés voulues : nulle sans mesure directe (c(0) = 0 — une ability uniquement propagée a une confiance nulle, cf. §4), croissante, à rendements décroissants, jamais exactement 1 (on ne certifie pas). La propagation n'incrémentant jamais `n_direct` (`propagate`, elo.py), c(n) ne compte **que la mesure directe** — c'est un choix d'honnêteté structurel, pas cosmétique.

### 3.2 Le pont vers une erreur-type : information de Fisher

Sous Rasch, l'information de Fisher apportée par un ensemble de réponses au point θ est :

```
I(θ) = Σᵢ Pᵢ(θ)·(1 − Pᵢ(θ))
```

et l'erreur-type asymptotique de l'estimateur ML est `SE(θ̂) = 1/√I(θ̂)` (Lord, 1980). Chaque terme `P(1−P)` est maximal (0.25) quand P = 0.5 — c'est-à-dire quand l'item est apparié à l'élève, le régime que vise la sélection adaptative.

**Transposition par le pont §1** : `SE_Elo = SE_logit × 173.7178`.

### 3.3 Mapping proposé confiance → SE

Hypothèse de travail (approximation adaptative) : les n réponses directes sont servies près du niveau de l'élève, donc P ≈ 0.5 et I ≈ n/4, d'où :

```
SE(θ̂) ≈ 2/√n  logits   ⇔   SE_Elo(n) ≈ 347.44/√n  points Elo
```

| n | c(n) = 1−e^(−n/8) | SE_Elo ≈ 347.4/√n | IC 95 % (±1.96·SE) |
|---|---|---|---|
| 5 | 0.46 | ±155 Elo | ±305 Elo |
| 8 | 0.63 | ±123 Elo | ±241 Elo |
| 10 | 0.71 | ±110 Elo | ±215 Elo |
| 20 | 0.92 | ±78 Elo | ±152 Elo |
| 30 | 0.98 | ±63 Elo | ±124 Elo |

**Exemple chiffré complet.** Un élève a répondu à n = 10 items directs près de son niveau. I ≈ 10 × 0.25 = 2.5 ; SE_logit = 1/√2.5 = 0.632 ; SE_Elo = 0.632 × 173.72 ≈ **110 points Elo** ; IC 95 % ≈ ±215 Elo. Restitution possible : « ability 1620 ± 110 (à 68 %) », au lieu du seul « confiance 0.71 ». Variante non idéalement appariée : si les items étaient plus faciles (P ≈ 0.7), I = 10 × 0.7 × 0.3 = 2.1 et SE_Elo ≈ 120 — la formule 347.4/√n est donc un **plancher** (meilleur cas) ; toute déviation de l'appariement augmente la SE.

**Statut de ce mapping.** `c(n)` et `SE(n)` sont deux fonctions monotones du même n : le mapping est bijectif (`SE_Elo ≈ 347.4·√(−ln(1−c))⁻¹·(1/√8)`… en pratique on passe par n). Il est **modèle-dépendant** (hypothèses : Rasch correct, items appariés, indépendance locale, ability stationnaire sur la fenêtre) et proposé ici comme lecture rigoureuse de la confiance existante — pas comme une SE empirique. Sa validation empirique (fidélité split-half, stabilité re-test) est planifiée au livrable C4 sur les données du pilote. Nuance de tracking : avec le K plancher (§2.2), la variance stationnaire de l'estimateur ne descend pas strictement en 1/n ; la table ci-dessus reste la référence sur la fenêtre courte typique d'une session de mesure.

### 3.4 Justification de la bande ±150 et du seuil 0.5

La restitution bascule en fourchette quand c(n) < 0.5 (`restitute`, scale.py). Or c(n) < 0.5 ⟺ n < 8·ln 2 ≈ 5.5, soit **n ≤ 5 réponses directes**. Au point de bascule n = 5, la SE modèle vaut 347.4/√5 ≈ **155 points Elo** — la bande implémentée (±150, `band=150.0`, scale.py) coïncide avec ~1 SE au seuil. Autrement dit : **le système affiche un point dès que la demi-largeur ±150 couvre au moins ±1 SE, et une fourchette avant**. En logits, ±150 Elo = ±0.86 logit (§1.3). Les deux constantes de la restitution sont donc dérivables du modèle, pas posées arbitrairement.

---

## 4. C1.4 — Propagation sur le graphe et garde-fous d'honnêteté

### 4.1 Le mécanisme

Le référentiel fractions v1 (`data/referentiel_fractions.json`) est un graphe de **32 compétences et 46 arêtes de corrélation** : 35 arêtes HARD (prérequis, poids ∈ [0.70, 0.88]) et 11 SOFT (parenté, poids ∈ [0.55, 0.68]) ; plus longue chaîne HARD = 11 nœuds ; médianes des priors de difficulté par grade : G2 = 1200, G3 = 1480, G4 = 1660, G5 = 1900.

Après chaque mise à jour directe de delta `Δ` sur une compétence, `propagate` (elo.py) applique aux voisins **directs** :

```
Δ_voisin = Δ × correlation_strength × 0.4        (DAMPING = 0.4)
```

avec quatre restrictions structurelles, toutes dans le code :

1. **1 saut seulement** — pas de propagation transitive (pas d'avalanche sur la chaîne de 11 nœuds).
2. **Jamais vers un voisin plus confiant** — condition `confidence(voisin) < confidence(source)` : une inférence n'écrase jamais une mesure plus sûre.
3. **N'incrémente jamais `n_direct`** — l'estimation propagée ne « compte » pas comme mesure : la confiance du voisin ne monte pas, et le garde-fou §4.2 reste bloquant.
4. **Clamp [0, 4000]** — même règle qu'`update_elo`.

Facteur effectif : Δ × 0.4 × poids, soit **28–35 %** du delta via une arête HARD, **22–27 %** via une SOFT. L'asymétrie prérequis/dépendant est portée par `correlation_strength` (donnée du référentiel), pas par la fonction. La propagation est un **lissage bayésien informel** exploitant la structure de corrélation du domaine pour améliorer les estimations des compétences peu testées — son bénéfice est vérifié en simulation (AC3, §5.3) — sans jamais se faire passer pour de la mesure.

### 4.2 Garde-fous d'honnêteté : mesure ≠ estimation

Le système distingue **structurellement** trois régimes : mesuré (n_direct > 0), estimé par propagation (ligne ability, n_direct = 0), jamais observé (pas de ligne ability). Les garde-fous, chacun vérifié dans le code :

- **Affichage « maîtrisé »** : exige `ability ≥ 1500` **ET** `n_direct > 0` (`_is_mastered`, `src/api/views_service.py` ; seuil `MASTERY_ELO = 1500`, `src/restitution/diagnosis.py`). **Jamais de maîtrise par inférence seule** : une propagation favorable ne suffit pas, il faut au moins une réponse directe.
- **Asymétrie assumée maîtrise/lacune** (docstring `find_gaps`, diagnosis.py, revue 2026-07-08) : déclarer une *lacune* est permis sur une estimation propagée (prudence : on va vérifier), déclarer une *maîtrise* ne l'est pas (on ne certifie pas sans mesure). L'erreur coûteuse est asymétrique — le seuil d'affirmation l'est aussi.
- **Diagnostic causal** : la cause racine d'une lacune est cherchée dans la clôture amont complète des prérequis HARD, mais **un nœud jamais estimé (aucune ligne ability) n'est jamais désigné racine** (`diagnose`, diagnosis.py, revue adversariale 2026-07-07) : accuser un nœud sur lequel il n'existe aucune observation produirait des racines systématiques absurdes. Si des ancêtres non évalués subsistent, l'explication le dit explicitement (« certains prérequis amont n'ont pas encore été évalués ») — on ne certifie pas non plus leur maîtrise.
- **Confiance basse → fourchette** à la restitution (§3.4) ; **c(0) = 0** pour toute ability purement propagée.

Pour l'audit : c'est l'argument central de crédibilité du système. Beaucoup de produits adaptatifs affichent des « maîtrises » issues de modèles d'inférence ; Atlas rend la distinction mesure/estimation **inviolable par construction** (compteur n_direct jamais incrémenté par l'inférence + garde d'affichage), et non par convention d'interface.

---

## 5. C1.5 — Quarantaine d'items = contrôle de fit

### 5.1 Reformulation statistique

`src/items/quarantine.py` retire du pool servi tout item actif dont le comportement de terrain contredit sa difficulté annoncée. Le test implémenté (`is_drifting`) :

```
Quarantaine ⟺  m ≥ 30                                (DEFAULT_MIN_RESPONSES)
           ET  | p_obs − p_att(b, a_réf) | > 0.40      (DEFAULT_MAX_DIVERGENCE)
```

où `p_obs` est le taux de réussite observé et `p_att(b, a_réf) = 1/(1 + 10^((b − a_réf)/400))` le taux attendu sous le modèle à l'ability de référence `a_réf = 1200` (`DEFAULT_REFERENCE_ABILITY`, paramètre injectable).

**Lecture psychométrique.** C'est un **résidu de proportion non standardisé**, la forme la plus simple d'une statistique d'item fit : l'écart entre courbe observée et courbe caractéristique du modèle, agrégé en un point d'ability — un analogue borné de l'outfit de Rasch (Wright & Masters, 1982) restreint à un test de niveau plutôt qu'à un χ² complet. Calibration du seuil : sous H₀ (l'item suit le modèle), l'écart-type binomial de p_obs à m = 30 vaut au plus √(0.25/30) ≈ 0.091 ; le seuil 0.40 représente donc **≈ 4.4 écarts-types** (0.40/0.0913 = 4.38) — un test volontairement **conservateur**, qui ne signale que les défauts grossiers (énoncé faux, corrigé erroné, ambiguïté bilingue majeure) avec un risque de fausse alarme quasi nul, et laisse le fit fin au plan d'analyses C4. Le plancher m ≥ 30 interdit toute quarantaine sur du bruit (AC4).

Exemple : un item de difficulté annoncée b = 1500 a p_att(1500, 1200) = 0.151 ; il n'est quarantainé que si son taux observé dépasse 0.551 (ou passe sous −0.249, impossible) — c'est-à-dire s'il est en réalité *massivement* plus facile qu'annoncé.

### 5.2 Procédure opérationnelle

- **Détection pure** (`is_drifting`) : stats injectées, testable sans trafic réel, branchable sur le journal `Response`.
- **Application** (`apply_quarantine`) : uniquement sur item `active` ; transition `active → quarantined` via la machine d'états de revue (`promote`), **réversible** (`quarantined → active`).
- **Journal de provenance** : la raison est horodatée et stampée sur l'item (« dérive : réussite X vs attendu Y sur m réponses », `_stamp_reviewer`), avec l'auteur (`system` ou humain) — auditabilité complète de chaque retrait.
- **Effet servi** : `active_pool` exclut les items quarantainés de toute sélection ; les réponses passées restent dans le journal append-only (aucune réécriture d'historique).

**Limite documentée** : la référence fixe a_réf = 1200 suppose une population de répondants proche de ce niveau ; une divergence peut refléter un décalage de population plutôt qu'un défaut d'item. Le harnais de simulation utilise déjà la parade (référence = ability moyenne réelle des répondants de l'item, `simulate_cohort.py` AC4) ; le plan C4 systématise cette version en production (courbes observé/attendu par strate d'ability des répondants réels).

### 5.3 Validation synthétique (à citer comme telle, jamais comme preuve terrain)

`scripts/simulate_cohort.py` (seed 42, déterministe) : 40 élèves à ability vraie cachée ~N(1500, 250), 30 réponses directes chacun, 6 items/compétence à difficulté vraie ~ prior + N(0, 120), réponses tirées selon la probabilité du modèle, moteur rejoué avec et sans propagation. Quatre critères d'acceptation, tous PASS à la version courante :

| AC | Critère | Cible |
|---|---|---|
| AC1 | Erreur médiane \|ability estimée − vraie\| sur la compétence primaire | < 150 Elo |
| AC2 | Corrélation de Pearson difficulté estimée / difficulté vraie (items **calibrés** : ≥ 30 réponses = burn-in 20 + ≥ 10 mises à jour ; 6 items au seed de référence — échantillon mince, à ré-estimer sur données pilotes, cf. C4) | > 0.8 |
| AC3 | Erreur médiane sur voisins jamais testés directement : propagation < baseline | strict |
| AC4 | Items quarantainés à tort sur données cohérentes au modèle | 0 |

Portée : ces chiffres valident la **cohérence interne** (le moteur retrouve les paramètres quand les données suivent le modèle) et le réglage (K, τ, DAMPING). Ils ne disent **rien** de la validité externe — c'est l'objet des protocoles C2/C3 pendant le pilote, et la politique de claims (C5, étage 0) impose de les présenter comme « validation par simulation », jamais comme calibration.

---

## 6. C1.6 — Limites assumées

Section obligatoire (Cadrage-LotC §3/C1.6). Ce que le système **ne peut pas encore prétendre**, et le livrable qui lève chaque limite :

1. **Priors experts non calibrés empiriquement.** Les `difficulty_prior` des compétences et la modulation ±250 par item (`difficulty.py`) sont du jugement expert encodé. Le burn-in (§2.3) les gèle 20 réponses, puis le trafic réel les recale — mais aucun trafic réel n'existe encore. *Levée : trafic pilote + harnais de ré-estimation (Lot A).*
2. **Ancres de restitution internes.** La table percentile/niveau (`DEFAULT_ANCHORS`, scale.py) est un barème expert ; le code le déclare lui-même (« à remplacer par cohorte réelle plus tard »). Les percentiles affichés sont **indicatifs**, non normés sur une population de référence. *Levée : étude de calibration C2 (AnchorTable empirique + SE par ancre) et standard-setting C3 (cut scores par panel enseignant, méthode Bookmark).*
3. **Aucune donnée de cohorte réelle.** Toute la validation est synthétique (§5.3), sous l'hypothèse que les données suivent le modèle. Fidélité, stabilité re-test, invariance inter-écoles : non mesurées à ce jour. *Levée : plan d'analyses C4 sur le journal `Response` du pilote.*
4. **Aucune preuve d'équité linguistique EN/AR.** Le journal `Response` n'enregistre pas encore la langue servie (constat C-0 du cadrage, migration bloquante pré-pilote) : aucune analyse DIF EN/AR n'est possible avant cette migration **et** la collecte pilote. La promesse « bilingue à parité » est aujourd'hui une exigence de conception, pas un résultat mesuré. *Levée : C-0 puis DIF Mantel-Haenszel/régression logistique (C4).*
5. **Graphe de prérequis expert, non validé empiriquement.** Les 46 arêtes et leurs poids [0.55, 0.88] sont du jugement expert ; la propagation (§4) et le diagnostic causal en héritent. La validation synthétique montre que la propagation aide *si les corrélations sont réelles* — pas qu'elles le sont. *Levée : corrélations empiriques inter-compétences sur données pilote (C4).*
6. **Hypothèses de modèle standard, non testées sur données réelles** : unidimensionnalité par compétence, indépendance locale, absence de paramètre de discrimination et de pseudo-chance (Rasch pur — pas de 2PL/3PL ; les QCM peuvent violer l'asymptote basse), ability supposée quasi stationnaire sur la fenêtre d'une session. Le fit item (C4) en fournira les tests.
7. **Mapping confiance → SE modèle-dépendant** (§3.3) : dérivé de l'information de Fisher sous hypothèse d'appariement adaptatif, non encore confronté à une SE empirique.
8. **Quarantaine à référence fixe** (a_réf = 1200, §5.2) : test de niveau conservateur, pas un item fit complet ; raffinement en C4.
9. **Aucune preuve d'efficacité pédagogique.** Hors périmètre et hors claims (C5, ligne « toujours ») : pas de RCT, donc jamais « améliore les résultats de X % », et jamais de claim clinique (« détecte la dyslexie »).

**Règle de communication associée** : la politique de claims (livrable C5) fixe ce qui est affirmable à chaque étage — aujourd'hui (étage 0) : « échelle interne validée par simulation ; percentiles indicatifs ; modèle documenté » ; interdits : « calibré », « aligné sur les standards MoE/CCSS », toute équivalence de grade présentée comme mesurée.

---

## Annexe A — Table des constantes (chacune vérifiée dans le code le 2026-07-11)

| Constante | Valeur | Rôle | Source |
|---|---|---|---|
| Échelle | [0, 4000], centre 1500 | support Elo (clamp) | `ELO_MIN`/`ELO_MAX`, `src/engine/elo.py` |
| `expected_score` | 1/(1+10^((b−a)/400)) | fonction de réponse | `src/engine/elo.py` |
| K_NEW / K_STABLE | 32 / 16 | K élève avant/après stabilisation | `src/engine/elo.py` |
| N_DIRECT_STABLE | 10 | seuil de stabilisation élève | `src/engine/elo.py` |
| ITEM_BURN_IN | 20 | gel difficulté au prior (K_item = 0) | `src/engine/elo.py` |
| K_ITEM_BASE / ITEM_HALFLIFE | 32 / 30 | K_item = 32/(1+m/30) après burn-in | `src/engine/elo.py` |
| TAU | 8 | confiance c(n) = 1−e^(−n/8) | `src/engine/elo.py` |
| DAMPING | 0.4 | amortissement propagation 1 saut | `src/engine/elo.py` |
| Invariant | Δa/K_élève + Δd/K_item = 0 | hors clamp/burn-in | docstring `update_elo`, `src/engine/elo.py` |
| Pont Rasch | θ = (Elo−1500)·ln(10)/400 | 1 logit ≈ 173.7178 Elo | §1.2 (dérivé de `expected_score`) |
| Ancres restitution | 1000→5/G2 ; 1300→25/G3 ; 1500→50/G4 ; 1800→75/G5 ; 2100→95/G6 | expertes, configurables | `DEFAULT_ANCHORS`, `src/restitution/scale.py` |
| Fourchette UI | ±150 Elo si confiance < 0.5 | ≈ ±0.86 logit ≈ 1 SE à n = 5 | `restitute`, `src/restitution/scale.py` |
| Maîtrise affichée | ability ≥ 1500 ET n_direct > 0 | jamais par inférence seule | `MASTERY_ELO`, `src/restitution/diagnosis.py` ; `_is_mastered`, `src/api/views_service.py` |
| Quarantaine | m ≥ 30 ET \|obs−att\| > 0.40 (réf. 1200) | item fit conservateur, réversible | `src/items/quarantine.py` |
| Modulation prior item | prior ± 250 Elo (complexité [0,1]) | difficulté a priori par item | `DEFAULT_BAND`, `src/items/difficulty.py` |
| Référentiel v1 | 32 nœuds, 46 arêtes (35 HARD [0.70,0.88], 11 SOFT [0.55,0.68]) ; chaîne HARD max 11 ; priors médians G2=1200, G3=1480, G4=1660, G5=1900 | domaine fractions | `data/referentiel_fractions.json` |
| Simulation | 40 élèves × 30 réponses, seed 42 ; AC1 <150 Elo, AC2 >0.8, AC3 strict, AC4 = 0 | validation synthétique | `scripts/simulate_cohort.py` |

## Annexe B — Références

1. Rasch, G. (1960). *Probabilistic Models for Some Intelligence and Attainment Tests.* Danish Institute for Educational Research.
2. Elo, A. E. (1978). *The Rating of Chessplayers, Past and Present.* Arco.
3. Klinkenberg, S., Straatemeier, M., & van der Maas, H. L. J. (2011). Computer adaptive practice of maths ability using a new item response model for on the fly ability and difficulty estimation. *Computers & Education*, 57(2), 1813–1824.
4. Pelánek, R. (2016). Applications of the Elo rating system in adaptive educational systems. *Computers & Education*, 98, 169–179.
5. Brinkhuis, M. J. S., & Maris, G. (2019). Dynamic estimation in the extended marginal Rasch model with an application to mathematical computer-adaptive practice. *British Journal of Mathematical and Statistical Psychology*, 72(2).
6. Glickman, M. E. (1999). Parameter estimation in large dynamic paired comparison experiments. *Journal of the Royal Statistical Society, Series C*, 48(3), 377–394.
7. Lord, F. M. (1980). *Applications of Item Response Theory to Practical Testing Problems.* Erlbaum. (Information de Fisher et SE, §3.)
8. Wright, B. D., & Masters, G. N. (1982). *Rating Scale Analysis.* MESA Press. (Statistiques de fit, §5.)
9. Kolen, M. J., & Brennan, R. L. *Test Equating, Scaling, and Linking.* Springer. (Référence du protocole C2.)
10. Cizek, G. J., & Bunch, M. B. *Standard Setting.* Sage. (Référence du protocole C3.)
11. Swaminathan, H., & Rogers, H. J. (1990). Detecting differential item functioning using logistic regression procedures. *Journal of Educational Measurement*, 27(4). (Référence du plan C4/DIF.)

---

*Fin du Manuel v1. Prochaines étapes (Cadrage-LotC §4) : test unitaire de conversion Elo↔logit (tolérance 1e-9), relecture interne, puis revue externe C6 avant tout lancement de collecte pilote (précédée de la migration bloquante C-0 `Response.language`).*
