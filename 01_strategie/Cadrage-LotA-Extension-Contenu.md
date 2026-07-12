# LOT A — Industrialiser l'extension de contenu (matières & grades)

**Version** : Cadrage v1.1 · **Date** : 2026-07-09 (errata 2026-07-11) · **Auteur** : cadrage produit (Nassim + Claude)
**État produit de référence** : 2026-07-09 (fractions G2–G5, 32 nœuds / 46 arêtes, 300+300 items EN/AR, moteur Elo + propagation, aucune donnée cohorte réelle).
**À lire avec** : `02_technique/DataModel-KnowledgeGraph.md` (§1 granularité, §3 arêtes), `02_technique/Architecture-Matiere-Pluggable.md` (contrat d'un nouveau domaine — ajouté en errata), `03_referentiel/Referentiel-Fractions.md` (le modèle à répliquer), `03_referentiel/referentiel_decimals_draft.json` (livrable A3).

---

## 1. Objectif et definition of done

**Objectif.** Transformer la fabrication du référentiel — aujourd'hui artisanale, tacite, portée par une seule tête — en une **méthode écrite, réplicable et auditable**, puis cadrer et amorcer la **première extension de contenu**. On ne produit pas du code : on produit la doctrine de fabrication, la matrice de décision du périmètre, et le premier référentiel-draft prêt pour revue experte.

**Pourquoi maintenant.** Le référentiel neutre est l'actif défendable du produit (la thèse d'acquisition en dépend). Tant qu'il n'existe qu'en un exemplaire (fractions) fabriqué sans méthode formalisée, il n'est ni réplicable, ni transmissible, ni vérifiable par un tiers. L'industrialiser est ce qui fait passer « j'ai construit un graphe » à « je possède une machine à construire des graphes ».

**Definition of done.**
- [ ] A1 (méthodologie) rédigée, validée en interne, applicable par un tiers sans le fondateur.
- [ ] A2 (matrice de périmètre) : options chiffrées, recommandation tranchée, roadmap séquencée.
- [x] A3 (référentiel-draft du 1er domaine) : JSON complet nodes+edges, DAG vérifié, prêt pour double lecture experte. *(Livré et validé le 2026-07-11 — cf. errata E1.)*
- [ ] A4–A8 : catalogue misconceptions, spec générateurs, plan AR, volumétrie, QA gates — au niveau « exécutable par un dev + un expert ».
- [ ] **Critère bloquant** : rien dans ce lot ne conditionne la signature du premier pilote (le pilote tourne sur fractions seules). A est le chantier long, parallélisé.

---

## 2. Périmètre (in / out) et dépendances

**In.**
- Doctrine de fabrication d'un référentiel (granularité, nommage, arêtes, priors, cognitif, contextes, contraintes structurelles, revue).
- Décision du premier domaine d'extension + roadmap.
- Référentiel-draft complet du domaine retenu.
- Catalogue misconceptions + spec générateurs déterministes + plan de production AR + volumétrie + QA gates du domaine.

**Out (explicitement).**
- Toute matière hors mathématiques (sciences, littéracie) → décision A2 argumentera le report.
- Toute implémentation du moteur ou de l'API (le moteur est déjà neutre matière ; A ne le touche pas).
- Le mapping curriculaire des nouvelles compétences → c'est **Lot B** (le référentiel reste neutre ; le curriculum est une projection).
- La calibration empirique des nouveaux priors sur cohorte réelle → **Lot C** (A pose des priors experts ; C les remplace par de l'empirique).

**Dépendances.**
- **A3 dépend de A1** : on ne dessine pas un domaine avant d'avoir figé les règles. Ordre non négociable.
- **A alimente C2** : les `difficulty_prior` produits par A sont les ancres que l'étude de calibration (C2) ré-estime ; le harnais d'equating de C4 se réutilise domaine par domaine.
- **A ↔ B** : chaque compétence produite par A devra être mappée dans les frameworks activés (règle CI de B6). A produit la matière, B produit l'étiquette.
- **Contrainte transverse** : bilingue EN/AR à parité, DAG strict, cœur curriculum-neutre, zéro PII dans les prompts LLM.

---

## 3. Livrables détaillés

### A1 — Méthodologie référentiel (le document fondateur)

Format : `Methodologie-Referentiel.md`, doctrine normative avec exemples tirés des fractions.

**A1.1 — Règle de granularité.** Réaffirme et généralise la règle du data model : **1 nœud = 1 geste cognitif atomique + 1 contrainte procédurale principale max**.
- Variation de **stratégie** de résolution → **nouveau nœud** (ex. `ADD_SAME_NOSIMP` vs `ADD_SAME_SIMPLIFY`).
- Variation de **contexte / difficulté** → **tag d'item** (`item_contexts`), jamais un nœud (ex. dénominateur 4 vs 8).
- Test opératoire : « ce nœud demande-t-il deux stratégies différentes pour être réussi ? » → si oui, scinder. « Cette variation change-t-elle fortement le taux de réussite sans changer la stratégie ? » → tag, pas nœud.
- Anti-pattern à interdire : la fragmentation par contexte (explosion à plusieurs milliers de micro-skills, densité de données par nœud trop faible pour calibrer).

**A1.2 — Convention de nommage.** `MATH.G{n}.{DOMAINE}.{SKILL}`.
- `{DOMAINE}` aligné sur les domaines CCSS-M (décision structurante : le nommage interne parle déjà le langage d'un des frameworks cibles, ce qui simplifie Lot B) : `NS` (number sense), `NF` (number & fractions), `NBT` (base ten / décimaux), `OA` (operations & algebraic thinking), `RP` (ratios & proportional), `EE` (expressions & equations), `G` (geometry), `MD` (measurement & data).
- `{SKILL}` en SCREAMING_SNAKE, verbe+objet, stable et versionnable. Le `code` est l'identité, jamais l'UUID.

**A1.3 — Décision HARD vs SOFT + fixation du poids.**
- **HARD** = nécessité logique : *impossible de réussir la cible sans la source*. Sert aussi au routing (ne pas servir B si A échoué) et au diagnostic causal (la clôture amont des HARD donne la cause racine).
- **SOFT** = corrélation pédagogique/empirique sans blocage.
- Grille d'élicitation du poids (`correlation_strength ∈ [0,1]`), ancres ordinales à imposer aux experts pour éviter les nombres au doigt mouillé :

  | Poids | Sémantique HARD | Sémantique SOFT |
  |---|---|---|
  | 0.85–0.90 | Dépendance quasi-mécanique (A est un composant de B) | — |
  | 0.75–0.84 | Prérequis fort, contournable à la marge | — |
  | 0.65–0.74 | Prérequis nécessaire mais partiellement | Corrélation forte |
  | 0.50–0.64 | *(voir errata E4 — plancher relevé)* | Corrélation modérée |
  | < 0.50 | Interdit pour un HARD | Corrélation faible (souvent → pas d'arête) |

- **Bornes normatives** (repris du data model, à recâbler comme garde-fou de ré-estimation empirique en C) : HARD ≥ 0.5 (plancher DB — mais voir errata E4 : plancher méthodologique recommandé 0.65–0.70), SOFT ≤ 0.7 (plafond). Un HARD validé pédagogiquement ne peut être inversé par la ré-estimation (monotonie partielle).

**A1.4 — Fixation du `difficulty_prior`.** Méthode en 3 temps, à documenter :
1. **Ligne de base par grade** : ancrer la médiane de grade sur l'échelle interne (repères fractions **observés en base** : G2 = 1200, G3 = 1480, G4 = 1660, G5 = 1900 — errata E2). Ces repères sont des **conventions expertes** — cf. avertissement honnêteté ci-dessous.
2. **Ajustement cognitif** : RECALL abaisse, REASON relève, à l'intérieur du grade.
3. **Ajustement par position dans la chaîne** : plus un nœud est aval (profond dans le DAG), plus son prior monte.
- Le prior de nœud sert de graine ; le prior d'**item** en dérive via la fonction de complexité domaine (A5) : `prior_item = prior_compétence + (complexité − 0.5) × 2 × 250`.
- **Avertissement honnêteté (à écrire noir sur blanc dans A1)** : ces priors sont des points de départ experts. Ils ne sont ni un standard, ni une mesure. Ils seront ré-estimés sur trafic réel (Lot C). Aucun artefact produit sous A ne doit être présenté comme « calibré ».

**A1.5 — Niveau cognitif (RECALL / APPLY / REASON, aligné TIMSS).** Définitions opérationnelles + heuristique d'attribution :
- **RECALL** (≈ *Knowing* TIMSS) : restituer un fait, une définition, une procédure figée (ex. `MULT_FACTS`).
- **APPLY** (≈ *Applying*) : exécuter une procédure connue sur un cas standard.
- **REASON** (≈ *Reasoning*) : choisir/combiner des stratégies, transférer, justifier.
- Cible de répartition à surveiller (les fractions penchent APPLY : 18/12/2) : viser un minimum de REASON par grade pour que le diagnostic ait du grain, sans forcer artificiellement.

**A1.6 — Définition des `item_contexts`.** Les dimensions de variation contextuelle qui produisent la variété d'items **sans** créer de nœud. Documenter, par famille de compétence, l'espace de contextes (magnitude, représentation symbolique/visuelle, pièges classiques, registre — ex. money model). C'est ce qui permet au moteur de détecter des patterns de difficulté par contexte via les tags, pas via des nœuds.

**A1.7 — Contraintes structurelles.**
- **DAG strict** : check anti-cycle obligatoire à l'insertion (`src/graph/validator.py`).
- **Densité d'arêtes** : cible indicative ~1.3–1.6 arête/nœud **en intra-domaine** ; les ponts inter-domaines sont comptés à part (errata E5). Fractions : 46/32 ≈ 1.44. Sous 1.0 = graphe sous-connecté (propagation inutile) ; au-dessus de ~2.0 = risque de sur-spécification.
- **Profondeur de chaîne** : les chaînes HARD longues concentrent le pouvoir diagnostique mais fragilisent la propagation (1 saut ne remonte qu'un cran). Documenter la profondeur par domaine (fractions : **11** — errata E3).
- **Racines** : tout nœud non-racine a ≥ 1 arête entrante. Les racines de sous-domaine sont explicites et documentées (ex. `PLACE_VALUE_TENTHS` dans A3, en attente du domaine place-value entier).

**A1.8 — Protocole de revue experte.** Grille + double lecture :
- **Grille de revue** (par nœud) : granularité (1 geste ?), nommage conforme, prior plausible, cognitif correct, contextes suffisants. (Par arête) : type HARD/SOFT justifié, poids dans la fourchette, pas de cycle.
- **Double lecture** : un didacticien maths + un enseignant primaire EAU en exercice, indépendamment, puis réconciliation des désaccords. Journaliser les arbitrages.
- **Gate** : aucun nœud ne passe `active` sans double validation experte.

### A2 — Matrice de décision du périmètre

Format : tableau + reco argumentée + roadmap. **Voir §7 pour la recommandation tranchée.**

| Option | Effort (compétences / items EN+AR / arêtes) | Réutilisation existant | Valeur commerciale EAU | Risques |
|---|---|---|---|---|
| **(a) Maths G2–G8 complet** | ~180–240 nœuds / ~3 600–4 800 items / ~260–380 arêtes | Moteur ✅, générateurs déterministes à étendre lourdement (algèbre, géométrie), AR massif | Élevée mais diffuse ; ouvre le collège | **Dispersion** ; G6–G8 = nouveaux types d'items (multi-étapes, saisie, symbolique) → coût psychométrique et production x3 ; bloque tout sur un chantier de 9–12 mois |
| **(b) Maths G2–G5 élargi (spine primaire)** | ~60–90 nœuds / ~1 200–1 800 items / ~90–130 arêtes | Moteur ✅, générateurs déterministes réutilisables (arithmétique exacte), AR glossaire dans la continuité, ponts vers fractions | **Élevée et ciblée** : complète l'offre pour l'acheteur pilote (primaire) | Modéré ; reste à discipliner l'ordre des domaines |
| **(c) Nouvelle matière (ex. sciences)** | ~50–80 nœuds / items majoritairement LLM | Moteur ✅ mais **tout le reste à refaire** : enum Subject, types d'items, générateurs, glossaire AR, crosswalk | Incertaine au MVP ; élargit le TAM mais dilue le wedge | **Élevé** : abandonne l'avantage « maths exactes déterministes » ; ouvre un front de contenu non maîtrisé ; contredit la discipline de scope du PRD |

**Sous-décision (a) vs (b) : séparer « aller plus haut » (G6–G8) de « aller plus large » (plus de domaines G2–G5).** La reco (§7) recommande **la profondeur en primaire avant la montée en collège**, et **décimaux en premier domaine**.

### A3 — Référentiel-draft du 1er domaine (décimaux G4–G5)

Format : `03_referentiel/referentiel_decimals_draft.json` (**livré et validé 2026-07-11**), format exact `{nodes, edges}`, prêt pour double lecture.
- **14 nœuds** NBT (place value tenths/hundredths/thousandths, read/write, decimal↔fraction, number line, compare, round, add, sub, ×/÷ powers of 10, ×whole, ×decimal, ÷whole).
- **26 arêtes** (17 HARD, 9 SOFT), dont **5 ponts inter-domaines** vers le référentiel fractions existant (codes réels vérifiés en base : `MATH.G3.NF.FRACTION_AS_PART` → tenths et → decimal-as-fraction ; `MATH.G4.NF.EQUIVALENCE_COMPUTE` → decimal-as-fraction ; `MATH.G3.NF.NUMBER_LINE_PLACE` et `MATH.G3.NF.COMPARE_SAME_DENOM` en SOFT). Ces ponts sont ce qui rend le graphe global cohérent : la maîtrise décimale s'appuie sur la maîtrise fractionnaire, et la propagation circule entre les deux.
- **DAG vérifié** avec le validateur du repo sur le graphe combiné fractions+décimaux : aucun cycle. Bornes de poids respectées. Médianes : G4 = 1620, G5 = 1890. Distribution cognitive 1 RECALL / 9 APPLY / 4 REASON (≥ 2 REASON par grade).
- **Statut** : DRAFT v0.1. Tous les priors et poids sont experts et **à réviser** en double lecture (A1.8). Point d'arbitrage pour la revue : médiane G4 décimaux (1620) sous la médiane G4 fractions (1660) — défendable (nœuds d'entrée de domaine, CCSS 4.NF.C), à confirmer par le didacticien. Racine locale `PLACE_VALUE_TENTHS` en attente du futur domaine place-value entier (elle a déjà un pont fraction entrant).

### A4 — Catalogue de misconceptions (décimaux) → spec de distracteurs

Format : `Misconceptions-Decimaux.md`, une entrée par compétence, sourcée en didactique. Chaque misconception → spécification de distracteur codable en dur (voie déterministe). Noyau non exhaustif à documenter :

| Misconception | Compétence(s) touchée(s) | Distracteur généré |
|---|---|---|
| « Plus de chiffres = plus grand » (*longer-is-larger*) | `COMPARE_DECIMALS`, `ROUND_DECIMAL` | proposer 0.45 > 0.5 comme vrai |
| « Moins de chiffres = plus grand » (*shorter-is-larger*, réciproque) | `COMPARE_DECIMALS` | 0.3 < 0.25 |
| Le zéro non significatif change la valeur (0.5 ≠ 0.50) | `READ_WRITE_DECIMAL`, `PLACE_VALUE_*` | 0.5 ≠ 0.50 présenté comme correct |
| Alignement à droite au lieu de la virgule (add/sub) | `ADD_DECIMALS`, `SUB_DECIMALS` | 2.5 + 0.35 = 2.40 (aligné à droite) |
| Décimal lu comme deux entiers (« trois virgule douze » > « trois virgule cinq ») | `READ_WRITE_DECIMAL`, `COMPARE_DECIMALS` | 3.12 > 3.5 |
| Multiplication « fait toujours grandir » | `MULT_DECIMAL_DECIMAL` | 0.4 × 0.6 = 2.4 (place de la virgule) |
| Comptage erroné des décimales au produit | `MULT_DECIMAL_DECIMAL` | 1 décimale au lieu de 2 |
| Confusion fraction/décimal (1/2 = 0.2) | `DECIMAL_AS_FRACTION` | 1/2 → 0.2 |

Chaque distracteur est spécifié pour la génération déterministe **et** documenté pour la validation du taux d'attractivité (un distracteur jamais choisi est inutile ; à surveiller en analyse d'items, Lot C4).

### A5 — Spécification des générateurs déterministes (décimaux)

Format : `Spec-Generateurs-Decimaux.md`, **conforme au contrat de `02_technique/Architecture-Matiere-Pluggable.md`** (errata E6) : livrables nommés `DECIMAL_GENERATORS`, `decimal_features(content) → context_tags`, `DECIMAL_FEATURE_WEIGHTS`, `decimal_complexity(features) → [0,1]` — miroir exact de `fraction_features` / `FRACTION_FEATURE_WEIGHTS` / `fraction_complexity` dans `src/items/deterministic.py`. La couche générique (`difficulty_from_score`, `weighted_score`) ne change pas.
- **Types d'items** par compétence : contraintes de génération exacte (arithmétique sur `Decimal` Python, pas de flottant, pour éviter 0.1+0.2 = 0.30000000000000004).
- **Fonction de complexité domaine `decimal_complexity ∈ [0,1]`** (features + poids indicatifs à calibrer) :

  | Feature | Poids indicatif | Justification |
  |---|---|---|
  | Nombre de décimales (max des opérandes) | 0.25 | thousandths > hundredths > tenths |
  | Nombre de places différentes entre opérandes (besoin d'alignement) | 0.20 | source majeure d'erreur |
  | Retenue / emprunt requis | 0.15 | charge procédurale |
  | Présence de zéro non significatif (piège) | 0.10 | active la misconception |
  | Résultat traverse une unité entière | 0.10 | rupture de magnitude |
  | Magnitude des nombres | 0.10 | charge de calcul |
  | Placement de virgule non trivial (× / ÷) | 0.10 | raisonnement sur la magnitude |

- Sortie : `prior_item = prior_compétence + (decimal_complexity − 0.5) × 2 × 250`, borné à l'échelle [0, 4000].

### A6 — Plan de production arabe (décimaux)

Format : `Plan-Production-AR-Decimaux.md`.
- **Glossaire mathématique MSA** aligné sur l'usage scolaire EAU (terminologie MoE) : أعشار (tenths), أجزاء من مئة (hundredths), أجزاء من ألف (thousandths), الفاصلة العشرية (decimal separator). **Convention constatée en banque (errata E7) : chiffres occidentaux 0–9 et point décimal** — à formaliser dans le glossaire plutôt qu'à re-débattre, cohérence avec l'existant fractions.
- **Guide de style** : registre scolaire, cohérence avec le glossaire fractions existant.
- **Charge de validation** estimée : ~140 items AR décimaux à valider linguiste (14 nœuds × ~10) + fidélité mathématique automatique via `check_ar_fidelity.py` (réutilisé) avant file linguiste.
- **Critères de fidélité** : l'énoncé AR doit produire exactement la même réponse mathématique que l'EN (vérif déterministe) ; la terminologie doit matcher le glossaire ; RTL correct pour le texte, LTR préservé pour l'expression mathématique. **Ajout (errata E8)** : détection de tokens latins résiduels dans les stems AR (hors notation mathématique) — un item actif de la banque fractions contient un mot anglais non traduit (« ONE ») que le check numérique ne peut pas attraper.

### A7 — Volumétrie cible justifiée

Format : note de volumétrie. Raisonnement à documenter :
- **Contrainte moteur** : la sélection adaptative sert l'item dont `difficulty_elo ≈ ability`. Pour couvrir la plage de niveaux d'une classe hétérogène sur une compétence, il faut ~8–12 items de difficultés étalées par compétence et par langue.
- **Contrainte quarantaine** : le mécanisme se déclenche à ≥ 30 réponses/item. Avec ~10 items/compétence, une classe de ~25 élèves génère assez de trafic pour calibrer sans épuiser la banque en une session.
- **Usure en usage classe** : un item **déjà vu** est exclu de la re-sélection tant qu'il reste des alternatives (errata E9 — règle réelle de `selection.py`, plus forte que « vu récemment ») ; ~10/compétence évite la répétition sur plusieurs sessions rapprochées.
- **Cible décimaux** : **~10 items/compétence/langue** → 14 × 10 × 2 = **~280 items** (140 EN + 140 AR). Cohérent avec la densité fractions (300+300 pour 32 nœuds ≈ 9,4/nœud/langue).

### A8 — QA gates

Format : tableau de gates avec critère d'acceptation par étape.

| Gate | Entrée | Critère d'acceptation |
|---|---|---|
| G1 — Référentiel validé | `referentiel_decimals_draft.json` | DAG sans cycle (validator ✅) ; double lecture experte OK ; densité intra-domaine ∈ [1.0, 2.0] ; tout non-racine a une entrée |
| G2 — Items générés | générateurs A5 | 100 % parsent `ItemContent` ; distracteurs = misconceptions A4 ; difficultés étalées ; 1 item = 1 compétence (strict) |
| G3 — AR validé | items EN validés | fidélité math déterministe ✅ ; **détection tokens latins résiduels** ✅ (errata E8) ; validation linguiste ✅ ; `ar_validated=true` avant `active` |
| G4 — Seedé | JSON + banque | seed idempotent ; nœuds + arêtes + ponts fractions en base ; comptes attendus |
| G5 — Simulé | `simulate_cohort.py` **paramétré** (errata E10 : le script hardcode aujourd'hui `referentiel_fractions.json` ligne 26 — tâche de paramétrisation à planifier en A-6, y compris mode multi-domaines pour tester les ponts) | cohorte synthétique : erreur médiane < 150 Elo ; corrélation difficultés > 0.8 ; propagation réduit l'erreur sur nœuds peu testés ; **0 quarantaine à tort** |

---

## 4. Plan de travail séquencé (jalons vérifiables)

| Phase | Contenu | Jalon vérifiable | Dépend de |
|---|---|---|---|
| **A-0** | A1 méthodologie rédigée | Un tiers reproduit la règle de granularité sur 3 cas sans le fondateur | — |
| **A-1** | A2 matrice + décision périmètre | Décision fondateur actée (domaine + ordre) ; roadmap séquencée | A1 |
| **A-2** | A3 draft JSON (décimaux) — **livré, à réviser** | DAG ✅ (fait) ; passé en double lecture experte (grille A1.8) | A1 |
| **A-3** | A4 misconceptions + A5 spec générateurs | Chaque compétence a ≥ 2 misconceptions spécifiées + type d'item déterministe défini | A2, A3 |
| **A-4** | A6 plan AR + glossaire MSA | Glossaire validé linguiste ; convention chiffres/point formalisée | A3 |
| **A-5** | A7 volumétrie + A8 QA gates | Cibles chiffrées ; gates G1–G5 rédigés avec critères testables | A5 |
| **A-6** | Production (hors périmètre cadrage) | Génération → revue → AR → seed → simulate (paramétré) ; G1–G5 franchis | tout A |

**Règle de séquencement inter-lots** : A-6 (production réelle) ne démarre **qu'après signature du premier pilote** ou en parallèle strict, jamais avant — le pilote tourne sur fractions. A ne doit jamais être sur le chemin critique de la signature.

---

## 5. Ressources : profils et effort

| Livrable | Profil | Effort estimé |
|---|---|---|
| A1 méthodologie | Fondateur + Claude | 2–3 j |
| A2 matrice périmètre | Fondateur + Claude | 1 j |
| A3 draft JSON décimaux | Fondateur + Claude (**fait**) puis **didacticien + enseignant primaire EAU** (double lecture) | 0,5 j prod + 2 j revue experte |
| A4 misconceptions | Claude (sourcing didactique) + didacticien (validation) | 1,5 j + 0,5 j revue |
| A5 spec générateurs | Fondateur + Claude | 1,5 j |
| A6 plan AR + glossaire | **Linguiste native AR** + Claude | 2 j |
| A7 volumétrie | Fondateur + Claude | 0,5 j |
| A8 QA gates | Fondateur + Claude | 0,5 j |
| **Production A-6** | Claude (génération) + fondateur (revue) + linguiste (AR) | ~5–8 j étalés |

**Experts externes — où exactement ?**
- **Didacticien maths** : indispensable sur **A1.8 (protocole), A3 (revue référentiel), A4 (misconceptions)**. C'est la revue référentiel + misconceptions qui donne la crédibilité de l'actif. ~3–4 j au total.
- **Enseignant primaire EAU en exercice** : deuxième lecture du référentiel (ancrage terrain + réalité MoE) + validation des contextes d'items. ~2 j. **Idéalement issu d'une école pilote** (double bénéfice : validation + relation commerciale).
- **Linguiste native AR** : A6 + validation AR de production. Déjà dans la boucle du MVP.

---

## 6. Risques et mitigations (top 5)

| # | Risque | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Sur-promesse commerciale** : présenter les priors experts décimaux comme « calibrés » | M | Élevé | A1.4 impose la mention explicite « prior expert, non mesuré » ; les claims sont régis par la politique C5 (Lot C) ; aucun deck ne dit « calibré » avant Lot C |
| 2 | **Dispersion** : glisser vers G6–G8 ou une nouvelle matière avant d'avoir prouvé le primaire | M | Élevé | Décision A2 tranchée et écrite (profondeur primaire d'abord) ; scope gelé domaine par domaine ; règle « 1 domaine jusqu'à preuve » |
| 3 | **Fragmentation du graphe** : experts qui multiplient les nœuds par contexte | M | M | Règle A1.1 + test opératoire imposé en grille de revue ; audit de densité (A1.7) à chaque domaine |
| 4 | **Rupture de parité AR** : items EN produits, AR en retard → activation asymétrique | M | Élevé | Gate G3 bloque `active` sans `ar_validated` ; charge AR planifiée en A6 dès le départ, pas en rattrapage |
| 5 | **Priors incohérents inter-domaines** : l'échelle décimale ne s'aligne pas sur l'échelle fractionnaire | M | M | Ponts inter-domaines (A3) + simulate_cohort mixte (G5) détectent les décalages ; ré-estimation empirique (Lot C) corrige à terme |

---

## 7. Décisions à prendre par le fondateur (avec recommandation)

**D-A1 — Premier périmètre d'extension.**
> **Recommandation : profondeur en primaire avant montée en collège. Décimaux (G4–G5) en premier domaine.** ❗
- **Pourquoi pas G2–G8 d'emblée** : l'hypothèse de travail conflate deux mouvements distincts (aller plus haut / aller plus large). Les écoles pilotes sont **primaires** — un produit « mesure des maths » pour le primaire a besoin de la colonne vertébrale primaire (décimaux, opérations sur entiers, mesure), pas des fractions isolées + de l'algèbre collège inutilisée. G6–G8 introduit de nouveaux types d'items (multi-étapes, saisie numérique, symbolique) qui triplent le coût de production et la complexité psychométrique.
- **Pourquoi décimaux en premier** : (1) adjacence cognitive maximale avec les fractions (réutilise le modèle mental, se lie au graphe via l'équivalence décimal↔fraction) ; (2) génération déterministe tractable (arithmétique décimale exacte, misconceptions bien cataloguées) ; (3) fréquence d'évaluation élevée en G4–G5 ; (4) extension propre du crosswalk (standards CCSS-M NBT/NF).
- **Séquence recommandée post-décimaux** : opérations sur entiers + valeur de position (compléter le bas de la colonne G2–G3) → mesure/géométrie légère → **puis seulement** ouvrir G6–G8 quand un pilote collège l'exige et le finance.

**D-A2 — Recours à des experts externes : lesquels, pour quelles étapes ?**
> **Recommandation : oui, deux profils, sur des étapes précises — pas une revue générale.** Didacticien maths sur A1.8 + A3 + A4 (~3–4 j). Enseignant primaire EAU, idéalement issu d'une école pilote, sur la 2ᵉ lecture du référentiel + contextes d'items (~2 j). C'est la revue **référentiel + misconceptions** qui fabrique la crédibilité de l'actif défendable ; la revue d'items unitaires peut rester interne (déterministe + linguiste).

**D-A3 — G6–G8 : mêmes mécaniques ou nouveaux types d'items ?**
> **Recommandation : trancher que G6–G8 = nouveaux types d'items (saisie numérique libre, multi-étapes), et donc les traiter comme un chantier distinct, hors de la première extension.** Le MVP est bâti sur MCQ / numérique simple / réponse courte. La proportionnalité, le pré-algèbre et la géométrie-mesure exigent de la saisie structurée et du scoring multi-étapes, ce qui touche le moteur d'items et la calibration. Ne pas les mélanger à l'extension primaire.

---

## Errata — revue contre le code (2026-07-09 → 2026-07-11)

Corrections issues de la vérification du cadrage v1 contre le repo (`04_code`), intégrées ci-dessus :

- **E1** — A3 était annoncé « livré » mais absent du disque. Créé et validé le 2026-07-11 : `03_referentiel/referentiel_decimals_draft.json` (DAG combiné ✅, ponts vérifiés contre les codes réels, bornes ✅).
- **E2** — Médianes de grade réelles en base : G3 = **1480** (pas 1450), G4 = **1660** (pas 1650). G2 = 1200 et G5 = 1900 confirmés.
- **E3** — Plus longue chaîne HARD fractions = **11 nœuds** (pas 12).
- **E4** — Les HARD réels des fractions sont tous ∈ [0.70–0.88]. Plancher méthodologique recommandé : **0.65–0.70** (le diagnostic causal traite tous les HARD identiquement quel que soit leur poids — un HARD faible aurait un pouvoir de blocage diagnostique disproportionné). Le plancher DB 0.5 reste le garde-fou technique.
- **E5** — Convention de densité : **intra-domaine** (ponts inter-domaines comptés à part). Draft décimaux : intra 21/14 = 1.50 ✅ ; global 26/14 = 1.86.
- **E6** — `Architecture-Matiere-Pluggable.md` normalise déjà le contrat d'un nouveau domaine (générateurs + `features()` + `complexity()` via `weighted_score`/`difficulty_from_score`). A1 l'absorbe ; A5 s'y conforme (nommage miroir de la matière fractions).
- **E7** — Convention AR constatée en banque : chiffres occidentaux 0–9, point décimal. À formaliser dans le glossaire A6.
- **E8** — Trouvé en banque : item AR actif avec token anglais non traduit (« ONE »). `check_ar_fidelity.py` ne vérifie que les nombres → ajouter la détection de tokens latins au gate G3.
- **E9** — Règle réelle de sélection (`src/engine/selection.py`) : exclusion des items **déjà vus** tant qu'il reste des alternatives (pas « vus récemment »).
- **E10** — `scripts/simulate_cohort.py` hardcode `referentiel_fractions.json` (ligne 26) : la paramétrisation (chemin + multi-domaines) est une tâche à part entière du gate G5, à planifier en A-6.
