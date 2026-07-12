# LOT C — Machine de mesure défendable + traduction mathématique exacte

**Version** : Cadrage v1 · **Date** : 2026-07-11 · **Auteur** : cadrage produit (Nassim + Claude)
**État produit de référence** : 2026-07-11 — moteur Elo opérationnel et testé (constantes vérifiées dans `src/engine/elo.py`), ancres de restitution **expertes** (`src/restitution/scale.py`, le code lui-même dit « à remplacer par cohorte réelle plus tard »), aucune donnée de cohorte réelle, **aucun enregistrement de la langue servie par réponse** (voir C-0).
**À lire avec** : `src/engine/elo.py` (les constantes citées ici en sont extraites), `src/restitution/scale.py` + `diagnosis.py`, `scripts/simulate_cohort.py`, Cadrage-LotB (le wording B4/B5 est contraint par la politique C5).

---

## 1. Objectif et definition of done

**Objectif.** Trois choses distinctes, souvent confondues en RDV — les séparer est le cœur du lot :
1. **Un Manuel Technique de Mesure** qui tient face à un Head of Assessment ou un psychométricien : formalisation du modèle, ponts mathématiques exacts vers les cadres qu'ils connaissent (Rasch/IRT), limites assumées.
2. **Des protocoles prêts à exécuter pendant le pilote** : étude de calibration (remplace les ancres expertes de `scale.py` par des ancres empiriques) et standard-setting (cut scores défendables sur les bandes de maîtrise).
3. **Une politique de claims** : ce qu'on a le droit d'affirmer à chaque étage de maturité, appliquée aux decks, à l'UI et aux rapports.

**Pourquoi maintenant.** C'est la réponse à la question qui tue (« votre scoring est calé sur nos standards ? »). Aujourd'hui la réponse honnête est non ; le lot C la transforme en « voici notre manuel, et l'ancrage sur vos bandes est un livrable du pilote ».

**Definition of done.**
- [ ] C-0 (**bloquant, avant toute collecte pilote**) : `Response.language` migré et alimenté — sans lui, aucune analyse d'équité EN/AR ne sera jamais possible sur les données du pilote.
- [ ] C1 : Manuel v1 rédigé, conversions Elo↔logit testées unitairement, relu (idéalement C6).
- [ ] C2 : protocole d'étude de calibration écrit, avec critères d'acceptation chiffrés et référence externe choisie.
- [ ] C3 : matériel de standard-setting prêt (méthode, livret, script d'animation, grille de stats d'accord).
- [ ] C4 : plan d'analyses (DIF, item fit, fidélité) spécifié avec scripts squelettes sur le journal `Response`.
- [ ] C5 : politique de claims adoptée — decks et UI audités contre elle.

---

## 2. Périmètre (in / out) et dépendances

**In.** Formalisation du modèle existant ; ponts mathématiques ; protocoles d'étude ; plan d'analyses ; politique de communication ; migration `Response.language`.

**Out (explicitement).**
- **L'exécution** de l'étude de calibration et du standard-setting → pendant le pilote, avec les écoles (le lot livre les protocoles, pas les résultats).
- **Remplacer le moteur par un IRT complet en production** → non (D-C2) : l'Elo reste le moteur temps réel ; l'IRT sert d'outil d'analyse offline.
- **RCT d'efficacité pédagogique** (« Atlas améliore les résultats ») → hors périmètre, hors claims (C5).
- La révision des priors experts du contenu → Lot A (C fournit le harnais de ré-estimation, A consomme).

**Dépendances.**
- **C-0 précède le pilote** — chemin critique absolu : une donnée non loggée est perdue pour toujours.
- **C2 consomme les difficultés produites par A** (les `difficulty_prior`/`difficulty_elo` servent d'ordre pour le livret Bookmark et d'ancres initiales d'equating).
- **C5 contraint B4/B5** (wording) et tous les decks commerciaux.
- `simulate_cohort.py` paramétré (errata E10 du Lot A) sert de banc d'essai au pipeline d'equating avant les vraies données.

---

## 3. Livrables détaillés

### C-0 — Migration `Response.language` (BLOQUANT PRÉ-PILOTE) — découverte revue code 2026-07-11

**Constat vérifié** : `Response` (append-only, `src/models/measurement.py`) enregistre `item_id, is_correct, response_time_ms, session_id, created_at` — **pas la langue servie**. `AssessmentSession` n'a pas de locale non plus. Les items étant bilingues dans une seule ligne (content EN + content_ar), il est **impossible de reconstituer** si l'élève a vu l'item en anglais ou en arabe.

**Conséquence si rien n'est fait** : aucune analyse DIF EN/AR possible → la promesse « bilingue à parité » restera une affirmation invérifiable, et les données du pilote seront inutilisables pour l'équité linguistique (pas de backfill possible sur un journal append-only).

**Livrable** : migration Alembic `response.language ENUM('en','ar') NOT NULL` (+ défaut applicatif au point d'écriture, dérivé de la locale de session d'évaluation — ajouter aussi `assessment_session.locale` pour la traçabilité) ; test que chaque réponse créée via l'API porte la langue. Effort ~0,5 j. **À faire même si le reste du lot C attend.**

**Note positive du même constat** : `response_time_ms` existe déjà → les analyses de vitesse (speededness, désengagement) sont possibles sans migration.

### C1 — Manuel Technique de Mesure

Format : `02_technique/Manuel-Technique-Mesure.md` (EN à terme pour les due diligences ; FR accepté en v1). Contenu, avec les valeurs **vérifiées dans le code** :

**C1.1 — Le modèle et son pont exact vers Rasch.**
- Fonction de réponse implémentée : `P(correct) = 1/(1 + 10^((b−θ)/400))` (`expected_score`, elo.py).
- Identité avec le modèle de Rasch : en posant `θ_logit = (Elo − 1500) · ln(10)/400`, on a exactement `P = 1/(1 + e^−(θ'−b'))`. **1 logit ≈ 173.72 points Elo ; 400 points Elo ≈ 2.303 logits.** Toute statistique Rasch/IRT (information, SE, fit) se transpose donc mécaniquement. → À livrer avec un test unitaire de la conversion (aller-retour à 1e-9).
- Ce pont est la « traduction mathématique parfaite » : un psychométricien peut auditer Atlas dans son propre langage sans lire notre code.

**C1.2 — Dynamique d'estimation (Elo comme approximation stochastique).**
- K élève : 32 puis 16 après 10 réponses directes (`K_NEW/K_STABLE/N_DIRECT_STABLE`) — interprétation : pas de gradient décroissant, compromis vitesse/variance.
- K item : **0 pendant le burn-in de 20 réponses** (difficulté gelée au prior — anti-dérive petite cohorte biaisée), puis `32/(1 + n/30)` (`ITEM_BURN_IN`, `ITEM_HALFLIFE`).
- Invariant pondéré `Δability/K_élève + Δdifficulté/K_item = 0` hors clamp et hors burn-in — déjà documenté dans le code (docstring `update_elo`), à reprendre tel quel.
- Clamp [0, 4000] : justification anti-dérive (triche, rejeu), et rupture assumée de l'invariant à la borne.
- Littérature d'ancrage : Klinkenberg, Straatemeier & van der Maas 2011 (Math Garden — précédent K-12 à grande échelle) ; Pelánek 2016 (Elo en systèmes éducatifs adaptatifs) ; Brinkhuis & Maris (tracking) ; Glickman (Glicko, pour la parenté confiance/RD). Positionnement : **des précédents établis, pas une invention maison**.

**C1.3 — Confiance et erreur-type.**
- Implémenté : `confidence(n) = 1 − e^(−n/8)` (saturation exponentielle — c(10) ≈ 0.71, c(20) ≈ 0.92, c(30) ≈ 0.98).
- À livrer : le mapping confiance → SE approchée (via l'information de Fisher au voisinage de θ, transposée par le pont C1.1), pour pouvoir dire « ±X points Elo à 95 % » au lieu d'un score de confiance abstrait. La restitution en fourchette existe déjà (bande ±150 si confiance < 0.5, `scale.py`) — le manuel la justifie au lieu de la poser.

**C1.4 — Propagation et garde-fous d'honnêteté.**
- `delta × correlation_strength × 0.4`, 1 saut, jamais vers un voisin plus confiant, n'incrémente jamais `n_direct` (`propagate`, elo.py).
- Garde-fou d'affichage : « maîtrisé » exige `ability ≥ 1500` **et** `n_direct > 0` — jamais de maîtrise par inférence seule. C'est un argument de crédibilité majeur : le système distingue structurellement mesure et estimation.

**C1.5 — Contrôle qualité des items = item fit.**
- Quarantaine existante (n ≥ 30, divergence observé/attendu > 0.40) reformulée comme statistique de fit (analogue outfit borné) ; procédure de retour (`quarantined ↔ active`) et journal de provenance.
- Validation par simulation (`simulate_cohort.py`, 40 élèves × 30 réponses) : erreur médiane < 150 Elo, corrélation difficultés > 0.8, propagation réduit l'erreur, 0 fausse quarantaine — chiffres à citer comme validation synthétique, PAS comme preuve terrain.

**C1.6 — Limites assumées (section obligatoire).** Priors experts non calibrés empiriquement ; ancres de restitution internes ; pas de données réelles ; pas d'étude d'équité linguistique (jusqu'à C-0 + pilote) ; graphe de prérequis expert non validé empiriquement.

### C2 — Protocole d'étude de calibration (exécution pendant pilote)

Format : `Protocole-Calibration-Pilote.md`.
- **Design** : administration concurrente — chaque élève du pilote passe Atlas (usage normal) + une mesure de référence sur le même trimestre. Options de référence (D-C3) : examens internes de l'école (accessibles, mais hétérogènes) ; items libérés TIMSS en ancres embarquées (psychométriquement documentés — **vérifier les conditions de licence IEA pour un usage commercial avant d'engager**) ; examen blanc MoE si accessible.
- **Échantillon** : ≥ 50–100 élèves **par grade** ciblé (G4–G5 d'abord), idéalement 2–3 écoles pour l'invariance. En dessous : publier les bandes comme provisoires avec SE affichée.
- **Méthode** : equating équipercentile avec lissage (peu d'hypothèses, robuste à petit n) en v1 ; co-calibration Rasch avec ancres si les items TIMSS sont utilisables (réf. Kolen & Brennan, *Test Equating, Scaling, and Linking*).
- **Sortie** : une `AnchorTable` empirique (le code est **déjà** conçu pour ça : table configurable, commentaire « à remplacer par cohorte réelle ») + SE par ancre + rapport de méthode.
- **Critères d'acceptation** : SE de chaque cut < demi-largeur de la bande qu'il sépare ; corrélation Atlas/référence ≥ 0.6 (en dessous, la référence ou l'échantillon est en cause — documenter au lieu de forcer).

### C3 — Protocole de standard-setting (bandes de maîtrise)

Format : `Protocole-Standard-Setting.md`. Méthode **Bookmark** (recommandée : les difficultés Elo existent déjà → livret ordonné gratuit) ; Angoff modifié en secours.
- Panel : 6–10 enseignants du/des pilotes (recrutement = même relation école que Lot A/D-A2).
- Matériel : livret d'items ordonnés par `difficulty_elo`, définitions des niveaux de performance (à écrire avec l'école — MoE : Beginning/Developing/Proficient/Advanced ou équivalent inspection), convention RP67, script d'animation, 2 rounds + données d'impact entre les rounds.
- Sortie : cut scores sur l'échelle Elo (→ logits par C1.1) + stats d'accord inter-juges + rapport de défendabilité (réf. Cizek & Bunch, *Standard Setting*).
- Articulation avec C2 : C2 ancre l'échelle sur une référence externe ; C3 pose les coupures de communication. Les deux remplissent la même `AnchorTable` — C2 les percentiles, C3 les niveaux.

### C4 — Plan d'analyses de validité et d'équité (sur données pilote)

Format : `Plan-Analyses-Pilote.md` + squelettes de scripts (consommant le journal `Response` — append-only, parfait pour ça).
1. **DIF EN/AR par item** (nécessite C-0) : Mantel-Haenszel + régression logistique (réf. Swaminathan & Rogers), seuils d'action : DIF modéré → revue linguiste ; DIF sévère → retrait + régénération. C'est **la** preuve de la promesse bilingue.
2. **Item fit systématique** : courbes observé vs attendu par item (extension du calcul de quarantaine), flag sous le seuil de quarantaine.
3. **Fidélité** : split-half pair/impair sur les réponses par compétence ; stabilité re-test des θ sur sessions rapprochées.
4. **Invariance inter-écoles** : mêmes items, mêmes difficultés estimées (±SE) d'une école à l'autre.
5. **Speededness** : distribution de `response_time_ms` (déjà loggé) — détection du désengagement (réponses < 2 s) à exclure des estimations.
- Banc d'essai : tout le pipeline tourne d'abord sur cohorte synthétique via `simulate_cohort.py` paramétré (E10) — le pipeline est validé avant la première vraie donnée.

### C5 — Politique de communication des scores (claims par maturité)

Format : `Politique-Claims-Mesure.md`, opposable aux decks, à l'UI (wording B4/B5) et aux rapports.

| Étage | État | Autorisé | Interdit |
|---|---|---|---|
| **0 — aujourd'hui** | ancres expertes | « échelle interne validée par simulation ; percentiles indicatifs ; modèle documenté (manuel) » | « calibré », « aligné sur les standards MoE/CCSS », toute équivalence de grade présentée comme mesurée |
| **1 — post-C2** | ancres empiriques | « bandes ancrées sur données pilotes (n=…, SE=…) » | généralisation hors population pilote sans le dire |
| **2 — post-C3** | cut scores standard-set | « niveaux de maîtrise établis par panel enseignant selon la méthode Bookmark » | « certifié/endossé par MoE/KHDA » (jamais, sauf accord écrit) |
| **Toujours** | — | « mesure de compétences, diagnostic causal » | « améliore les résultats de X % » (pas de RCT), « détecte la dyslexie/troubles » (jamais) |

### C6 — Revue externe (option recommandée)

Mission de 2–3 jours d'un psychométricien consultant : relecture du Manuel (C1) + du protocole (C2/C3) **avant** le lancement de l'étude. Livrable : note de revue citable en due diligence (« reviewed by… »). Moment optimal : après C1 v1, avant la première collecte. Coût estimé 2–4 k€ — le meilleur ratio crédibilité/euro du projet.

---

## 4. Plan de travail séquencé (jalons vérifiables)

| Phase | Contenu | Jalon vérifiable | Dépend de |
|---|---|---|---|
| **C-0** | Migration `Response.language` (+ locale session) | Migration sur PG vierge ✅ ; toute réponse API porte `language` ; test | — **IMMÉDIAT, avant pilote** |
| **C-1** | Manuel C1 v1 | Conversion Elo↔logit testée unitairement ; relecture interne complète | — |
| **C-2** | Protocoles C2 + C3 rédigés | Critères d'acceptation chiffrés ; référence externe choisie (D-C3) ; matériel Bookmark prêt | C-1 |
| **C-3** | Scripts C4 squelettes + banc synthétique | Pipeline DIF/fit/fidélité tourne sur cohorte simulée | E10 (Lot A), C-0 |
| **C-4** | Politique C5 adoptée | Decks + UI audités ; wording B4/B5 conforme | C-1 |
| **C-5** | (Option) revue externe C6 | Note de revue reçue | C-1, C-2 |
| **Exécution** | Étude C2 + panel C3 **pendant le pilote** | AnchorTable empirique en prod ; rapport de calibration | pilote signé |

---

## 5. Ressources : profils et effort

| Livrable | Profil | Effort |
|---|---|---|
| C-0 migration | Fondateur + Claude | 0,5 j |
| C1 manuel | Fondateur + Claude | 2–3 j |
| C2 + C3 protocoles | Fondateur + Claude | 1,5–2 j |
| C4 scripts + banc | Fondateur + Claude | 1,5–2 j |
| C5 politique + audit decks | Fondateur + Claude | 0,5 j |
| C6 revue externe | **Psychométricien consultant** | 2–3 j (externe) |
| Exécution étude (pendant pilote) | Fondateur + coordinateur école + panel 6–10 profs | ~2 j fondateur + 1 j panel |

---

## 6. Risques et mitigations (top 5)

| # | Risque | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Collecte pilote lancée sans `Response.language`** → données d'équité perdues à jamais | H si non traité | Élevé | C-0 bloquant, hors de tout autre séquencement ; check dans la checklist pré-pilote existante |
| 2 | **Échantillon insuffisant** (une seule petite école) → bandes non défendables | M | Élevé | Viser 2–3 écoles ; sinon publier « provisoire, n=…, SE=… » (étage 1 de C5, honnêteté = crédibilité) |
| 3 | **Licence TIMSS refusée/ambiguë** pour usage commercial | M | M | Vérifier AVANT d'engager (C2) ; fallback : examens internes école comme référence (moins propre, documenté) |
| 4 | **Sur-claim avant l'étude** (deck qui dit « calibré ») | M | Élevé | C5 étage 0 adopté immédiatement ; audit des supports existants ; le manuel donne un langage de remplacement crédible |
| 5 | **Panel Bookmark en désaccord** (cut scores instables) | M | M | 2 rounds + données d'impact (procédure standard) ; stats d'accord publiées ; si instable, retenir la fourchette et le dire |

---

## 7. Décisions à prendre par le fondateur (avec recommandation)

**D-C1 — L'étude de calibration est-elle un livrable VENDU du pilote ?**
> **Recommandation : oui.** « Vous recevez, en fin de pilote, la calibration de l'échelle sur votre population et vos bandes de maîtrise établies avec vos enseignants » — ça transforme le point faible (pas d'ancrage) en livrable payé, ça engage l'école (panel), et ça produit l'actif réutilisable pour toutes les ventes suivantes.

**D-C2 — Rester Elo ou migrer vers un IRT complet ?**
> **Recommandation : rester Elo en production, IRT en analyse offline.** Le pont C1.1 rend les deux mondes équivalents pour l'audit ; l'Elo garde ses avantages opérationnels (incrémental, pas de re-fit batch, robuste au flux) ; l'IRT offline (Rasch sur le journal) sert à valider/recalibrer périodiquement. Migrer le moteur serait un chantier lourd sans gain de crédibilité que le manuel n'apporte déjà.

**D-C3 — Quelle référence externe pour C2 ?**
> **Recommandation : examens internes des écoles pilotes en principal, items TIMSS libérés en ancres si la licence IEA le permet.** L'examen blanc MoE serait idéal mais son accès est incertain ; ne pas conditionner l'étude à son obtention.

**D-C4 — Revue externe (C6) : oui ou non ?**
> **Recommandation : oui, avant le lancement de l'étude.** 2–3 jours d'un psychométricien = la différence entre « ils affirment » et « c'est relu par un tiers du métier » en due diligence. C'est aussi une assurance qualité sur C2/C3 avant de brûler l'unique fenêtre de collecte du pilote.
