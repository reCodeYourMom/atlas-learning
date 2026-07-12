# Protocole d'étude de calibration — Pilote (Lot C, livrable C2)

**Version** : v1 · **Date** : 2026-07-11 · **Auteur** : Nassim + Claude
**Cadré par** : `01_strategie/Cadrage-LotC-Mesure-Defendable.md` §3/C2 (design concurrent, échantillons, méthodes et critères d'acceptation y sont posés ; ce document les développe en protocole exécutable).
**À lire avec** : `04_code/src/restitution/scale.py` (la sortie de l'étude), `04_code/src/models/measurement.py` (la source des données), `04_code/src/engine/elo.py` (constantes du moteur), Manuel Technique de Mesure (C1) pour le pont Elo↔logit.
**Référence méthodologique principale** : Kolen, M. J. & Brennan, R. L., *Test Equating, Scaling, and Linking: Methods and Practices* (3ᵉ éd., Springer) — chap. 2 (equating équipercentile), chap. 3 (lissage), chap. 7 (erreurs-types).

---

## 0. Objet, statut et prérequis bloquants

**Objet.** Remplacer la table d'ancrage **experte** de la restitution par une table **empirique**, ancrée sur une mesure de référence externe, avec erreur-type par ancre. Le code est déjà conçu pour cet échange : `src/restitution/scale.py` définit une `AnchorTable` « CONFIGURABLE (pas en dur) » et sa table par défaut porte le commentaire explicite *« barème expert ; à remplacer par cohorte réelle plus tard »* (`DEFAULT_ANCHORS`, lignes 68–75). L'étude produit exactement l'objet que ce code attend — aucune modification du moteur Elo n'est requise (séparation stricte moteur/restitution, docstring de `scale.py`).

**Ce que l'étude ne fait PAS** : elle n'établit pas les cut scores de maîtrise (→ C3, standard-setting Bookmark) ; elle ne prouve pas l'efficacité pédagogique (hors claims, C5) ; elle ne recalibre pas les difficultés d'items (→ harnais Lot A + C4 item fit).

**Prérequis bloquants (go/no-go avant la première donnée collectée)** :

| # | Prérequis | Vérification | Statut requis |
|---|---|---|---|
| P1 | **C-0 : `Response.language` migré et alimenté** | migration Alembic appliquée ; toute réponse API porte `language` | ✅ obligatoire — une donnée non loggée est perdue pour toujours (journal append-only) |
| P2 | Référence externe choisie et sécurisée (D-C3) | examens internes : accord écrit école ; TIMSS : licence IEA obtenue (§4.0) | ✅ obligatoire |
| P3 | Pipeline d'analyse validé sur cohorte synthétique | `scripts/simulate_cohort.py` (paramétré, errata E10 Lot A) traverse le pipeline §3 de bout en bout et reconstitue des ancres plausibles | ✅ obligatoire — on ne débogue pas le pipeline sur l'unique fenêtre de collecte |
| P4 | Accord de traitement de données signé (§8) | DPA/annexe pilote signée par chaque école | ✅ obligatoire |
| P5 | Revue externe C6 du présent protocole | note de revue reçue | recommandé (D-C4) |

---

## 1. Design de l'étude

### 1.1 Schéma : administration concurrente, groupe unique (*single group design*)

Chaque élève du pilote fournit **les deux mesures** dans la même fenêtre :
- **X (Atlas)** : usage normal du produit pendant le trimestre — aucune passation spéciale, la mesure est le sous-produit de l'apprentissage adaptatif (journal `Response`).
- **Y (référence)** : une mesure externe du même domaine (maths, grades ciblés G4–G5 d'abord), administrée par l'école dans ses conditions habituelles.

Le groupe unique élimine le besoin d'équivalence entre groupes (pas de design NEAT nécessaire en méthode principale) : c'est le design le plus robuste à petit n, au prix d'une hypothèse — les deux mesures visent le même construit au même moment. D'où la contrainte de fenêtre (§1.2) et le critère de corrélation (§6).

### 1.2 Fenêtre de collecte et calendrier

| Jalon | Moment | Contenu |
|---|---|---|
| T0 | Démarrage pilote | usage Atlas normal ; comptage hebdomadaire des élèves atteignant le seuil d'inclusion (§2.3) |
| T0 + 8 à 10 semaines | **Date de gel (freeze)** | snapshot des `StudentCompetencyAbility` (θ Elo, `confidence`, `n_direct`, `last_measured_at`) — figé, horodaté, versionné |
| Gel ± 3 semaines | **Mesure de référence Y** | examen interne de trimestre (idéal : il tombe naturellement dans la fenêtre) ou passation TIMSS ancres |
| Gel + 1 sem | Réception des scores Y | fichier école au format §1.6 |
| Gel + 3 sem | Analyse (§3) | AnchorTable + SE + diagnostics |
| Gel + 4 sem | Rapport (§7) + PR de configuration | AnchorTable empirique en production, C5 étage 1 activable |

**Règle de fenêtre** : |date(Y) − date(gel)| ≤ 3 semaines par élève. Au-delà, l'élève sort de l'échantillon d'equating (l'hypothèse « même construit au même moment » ne tient plus sur un trimestre d'apprentissage actif). La date de gel est choisie pour coïncider avec les examens internes de l'école — **la caler avec le coordinateur école dès la signature du pilote**.

### 1.3 Variable X — définition opérationnelle du score Atlas

Le score équaté est le **θ agrégé par domaine** (l'échelle que restitue `AnchorTable`), pas le θ d'une compétence isolée :

```
X(élève) = Σ_c [ confidence_c · ability_elo_c ] / Σ_c confidence_c
           sur les compétences c du domaine ciblé (ex. maths G4)
           avec n_direct_c ≥ 3 (mesure directe minimale par compétence incluse)
```

Justifications :
- pondération par `confidence` (= `1 − e^(−n/8)`, `elo.py`) : les compétences bien mesurées pèsent plus ;
- exclusion des compétences à `n_direct < 3` : on n'équate pas de l'inférence pure (cohérent avec le garde-fou C1.4 « jamais de maîtrise par inférence seule ») ;
- **analyse de sensibilité obligatoire** : recalculer avec moyenne non pondérée ; si les ancres bougent de plus d'un SE, le documenter dans le rapport (§7, section 6).

Hygiène des données en entrée (aligné C4) :
- exclure les réponses `response_time_ms < 2000` (désengagement, C4.5) du recalcul de contrôle ;
- exclure les items en quarantaine au moment du gel ;
- ne garder que les réponses avec `session_id` non nul (les seeds/appels moteur directs ne sont pas des mesures élèves — cf. commentaire `uq_response_session_item`, `measurement.py`).

### 1.4 Variable Y — la mesure de référence (décision D-C3)

Par ordre de préférence (recommandation du cadrage) :

1. **Examens internes des écoles pilotes** (principal). Accessibles, calendrier naturel. Faiblesses assumées : hétérogènes entre écoles (→ equating par école puis comparaison, §2.4), fidélité inconnue (→ la demander ou l'estimer, §3.4).
2. **Items libérés TIMSS en ancres embarquées** (si licence IEA — checklist §4.0 obligatoirement AVANT engagement). Psychométriquement documentés, difficultés internationales publiées → ouvre la variante Rasch (§4).
3. **Examen blanc MoE** si accessible — ne pas conditionner l'étude à son obtention.

Exigences minimales sur Y, quelle que soit l'option : score numérique par élève ; ≥ 20 points de score distincts possibles (sinon la granularité dégrade l'equating) ; barème et conditions de passation documentés ; correspondance grade ↔ contenu du domaine Atlas vérifiée (crosswalk Lot B).

### 1.5 Consignes aux écoles (document d'une page à remettre au coordinateur)

1. **Usage Atlas normal** — aucune préparation spéciale, aucun « entraînement à l'évaluation ». L'étude mesure l'usage réel.
2. **Assiduité minimale** : viser ≥ 2 sessions/semaine par classe pendant la fenêtre, pour que les élèves atteignent le seuil d'inclusion (§2.3). Le coordinateur reçoit un état hebdomadaire (n élèves inclus / classe) — pseudonymisé.
3. **Si ancres TIMSS embarquées** : ne pas signaler ces items aux élèves, ne pas les corriger en classe pendant la fenêtre (contamination des ancres).
4. **Examen de référence** : conditions habituelles de l'école, pas de tiers temps différentiel non documenté ; transmettre les scores bruts (pas les notes converties) via le canal sécurisé (§1.6).
5. **Identifiants** : l'école transmet les scores avec l'**ID d'étude pseudonyme** fourni par Atlas — jamais de nom d'élève dans les fichiers échangés (§8).
6. **Point de contact unique** : un coordinateur école + un responsable Atlas, canal convenu, délai de réponse 48 h pendant la fenêtre.

### 1.6 Flux de données de bout en bout

```
[École]                          [Atlas prod]                      [Poste d'analyse isolé]
   │                                  │                                     │
   │  usage normal ────────────────▶  │ journal Response (append-only)      │
   │                                  │ StudentCompetencyAbility            │
   │                                  │                                     │
   │                                  │── gel : export pseudonymisé ──────▶ │  fichier A (X)
   │                                  │   (study_id, grade, école,          │
   │                                  │    X, confidence, n_direct,         │
   │                                  │    language mix EN/AR)              │
   │                                  │                                     │
   │── scores référence ───────────────────────────────────────────────────▶│  fichier B (Y)
   │   (study_id, score_Y, date,      │                                     │
   │    max_points) — canal chiffré   │                                     │
   │                                  │                                     │
   │                                  │                        appariement study_id
   │                                  │                        pipeline §3 (scripts versionnés)
   │                                  │                                     │
   │                                  │ ◀── AnchorTable + SE (PR config) ───│
   │ ◀── rapport de calibration ──────│                                     │
```

Règles :
- **`study_id`** : pseudonyme d'étude dérivé de `student.id` (UUID) par HMAC avec un sel d'étude — la table de correspondance `study_id ↔ student.id` reste chez Atlas, jamais transmise ; l'école reçoit la liste `study_id ↔ identité élève` via SON registre (elle seule peut réidentifier ses élèves) — voir §8.
- Export Atlas : requête SQL versionnée dans le dépôt (squelette dans C4), résultat horodaté, hash du fichier consigné dans le rapport.
- Fichier école : gabarit CSV fourni (`study_id,score_y,max_points,date_passation,accommodations`), transmission chiffrée, validation à réception (IDs inconnus, doublons, scores hors barème → retour sous 48 h).
- Analyse : environnement isolé, données jamais copiées hors du poste d'analyse, suppression des fichiers appariés à la fin (rétention §8).

---

## 2. Plan d'échantillonnage

### 2.1 Tailles cibles

| Paramètre | Cible | Plancher | Conséquence sous le plancher |
|---|---|---|---|
| Élèves inclus **par grade** | 100 | 50 | bandes publiées comme **provisoires**, SE affichée (C5 étage 1) — on publie quand même, avec l'honnêteté comme claim |
| Grades | G4–G5 d'abord | 1 grade | extension G3/G6 seulement si n atteint |
| Écoles | 2–3 | 1 | pas de vérification d'invariance → le rapport le dit explicitement |

Le recrutement vise le **double** du plancher en élèves exposés (attrition attendue ~40–50 % : seuil d'inclusion non atteint, absents à l'examen, hors fenêtre, retraits de consentement).

### 2.2 Précision d'equating attendue (calcul justifiant 50–100/grade)

L'erreur-type d'un quantile empirique de rang p est approximativement (Kolen & Brennan chap. 7) :

```
SE(x̂_p) ≈ σ · √(p(1−p)/n) / φ(z_p)
```

avec σ l'écart-type intra-grade des scores Atlas et φ la densité normale au quantile. En prenant **σ ≈ 250 Elo** (hypothèse de travail : la table experte espace les grades d'environ 300 Elo, `DEFAULT_ANCHORS` ; à réestimer sur cohorte synthétique en P3 puis sur les données) :

| Ancre (percentile) | SE brute, n=50 | SE brute, n=100 | SE attendue après lissage (−20 à −40 %) |
|---|---|---|---|
| P50 | ≈ 44 Elo | ≈ 31 Elo | ≈ 27–35 / 19–25 Elo |
| P25 / P75 | ≈ 48 Elo | ≈ 34 Elo | ≈ 29–38 / 20–27 Elo |
| P5 / P95 | ≈ 75 Elo | ≈ 53 Elo | ≈ 45–60 / 32–42 Elo |

Lecture : avec des bandes de ~300 Elo de large (demi-largeur 150 Elo), le critère d'acceptation « SE < demi-largeur » (§6) est atteignable dès n=50 **y compris aux percentiles extrêmes**, et confortable à n=100. C'est le calcul qui fonde la fourchette 50–100 du cadrage — pas un chiffre de convention. Les SE réelles seront estimées par bootstrap (§3.3), pas par cette formule (qui sert au dimensionnement a priori).

Contre-vérification obligatoire en P3 : faire tourner le bootstrap sur cohorte synthétique (`simulate_cohort.py` paramétré à n=50 et n=100) et vérifier que les SE observées sont dans ces ordres de grandeur.

### 2.3 Critères d'inclusion / exclusion élève

**Inclus** si, à la date de gel :
- `confidence` agrégée du domaine ≥ 0.7 — soit ~10 réponses directes par compétence pesante (`confidence(10) ≈ 0.71`, `elo.py`) ;
- ≥ 3 compétences du domaine avec `n_direct ≥ 3` ;
- score Y disponible dans la fenêtre ±3 semaines ;
- consentement/information conforme au dispositif du pilote (§8).

**Exclu** (avec comptage motivé dans le rapport) :
- élève `deleted_at` non nul ou sous `legal_hold` au gel (`measurement.py`) ;
- accommodations d'examen non comparables (au cas par cas, documenté) ;
- profil de désengagement massif : > 50 % des réponses < 2 s.

### 2.4 Multi-écoles et invariance

Si ≥ 2 écoles : l'equating est calculé (a) sur l'échantillon poolé et (b) par école. Critère d'invariance : les ancres par école tombent dans ± 1 SE bootstrap des ancres poolées. Sinon : ne pas moyenner de force — publier les ancres poolées, documenter la divergence, et signaler la limite de généralisation (C5 étage 1 : « ancré sur données pilotes, n=…, SE=… », pas au-delà).

---

## 3. Méthode principale : equating équipercentile avec lissage log-linéaire

Choisie car elle fait **peu d'hypothèses** (aucune forme paramétrique de la relation X–Y) et reste robuste à petit n une fois lissée — exactement le régime du pilote. Référence : Kolen & Brennan, chap. 2–3.

### 3.1 Notation et données d'entrée

- `X_i` : score Atlas de l'élève i (§1.3), continu sur l'échelle Elo.
- `Y_i` : score de référence, discret (points d'examen).
- Tout se calcule **par grade** (une AnchorTable par grade équaté), échantillon poolé multi-écoles (§2.4).

### 3.2 Étapes de calcul

1. **Contrôles d'entrée** : appariement complet (chaque ligne a X et Y), distribution des deux variables inspectée (histogrammes au rapport), corrélation Pearson **et** Spearman X–Y calculées d'emblée — si r < 0.6, s'arrêter et passer en mode diagnostic (§6, critère A2) avant tout equating.
2. **Pré-lissage log-linéaire de Y** (scores discrets) : ajuster la famille de modèles log-linéaires polynomiaux de degré C = 2, 3, 4, 5 sur la distribution des scores Y (le modèle de degré C préserve les C premiers moments de la distribution observée — Kolen & Brennan §3.2). Sélection de C : test du rapport de vraisemblance entre degrés successifs (seuil 0.05) + AIC ; inspection visuelle des fréquences lissées vs observées au rapport.
3. **Fonction de rang percentile de Y** : à partir de la distribution lissée, calculer P_Y(y) avec la continuisation standard (le score discret y couvre [y−0.5, y+0.5[).
4. **Fonction de rang percentile de X** : X étant continu, utiliser le rang percentile empirique avec lissage kernel gaussien léger de la CDF (bande passante de Silverman) — équivalent fonctionnel du pré-lissage côté continu.
5. **Fonction d'equating équipercentile** : `e_Y(x) = P_Y⁻¹(P_X(x))` — au score Atlas x correspond le score de référence de même rang percentile.
6. **Construction des ancres** : pour chaque percentile d'ancrage **p ∈ {5, 25, 50, 75, 95}** (structure identique à `DEFAULT_ANCHORS`, qui pose 5/25/50/75/95 — la restitution n'a pas à changer de forme), calculer :
   - `elo_p = P_X⁻¹(p)` : le score Atlas au percentile p de la cohorte du grade ;
   - `level_p` : le niveau au sens de la référence à ce même percentile (position de `e_Y(elo_p)` dans le barème/les bandes de l'examen de référence ; en attendant C3, le libellé de niveau reste celui de la référence, pas une bande de maîtrise Atlas).
7. **Erreurs-types** : §3.3.
8. **Diagnostics** : §3.4. Puis assemblage de l'`AnchorTable` (§5) et rapport (§7).

Toutes les étapes sont scriptées (Python, dépôt `04_code`, arborescence d'analyse à côté des squelettes C4), seedées, et rejouables : la commande unique `calibrate --grade G4 --freeze 2026-XX-XX` doit reproduire la table à l'identique.

### 3.3 Erreurs-types : bootstrap

- **B = 1 000** rééchantillonnages avec remise **des élèves** (pas des réponses — l'élève est l'unité d'échantillonnage).
- À chaque réplique : réappliquer TOUT le pipeline (lissage compris — le choix de C peut être figé au C sélectionné sur l'échantillon complet, décision documentée).
- `SE(ancre_p)` = écart-type bootstrap de `elo_p` ; reporter aussi l'IC percentile à 95 %.
- Le bootstrap donne également la SE de chaque **cut** (frontière entre bandes adjacentes) pour le critère A1 (§6).

### 3.4 Diagnostics (tous au rapport)

- Corrélation X–Y (Pearson, Spearman) + nuage de points par grade et par école.
- Si la fidélité de Y est estimable (split-half sur les items de l'examen, ou fournie par l'école) : reporter la corrélation corrigée d'atténuation `r/√(ρ_XX'·ρ_YY')` **à titre indicatif seulement** (le critère A2 porte sur la corrélation brute).
- Qualité du lissage : fréquences observées vs lissées, moments préservés.
- Invariance inter-écoles (§2.4).
- Sensibilité à la définition de X (§1.3 : pondérée vs non pondérée).
- Comparaison ancres empiriques vs `DEFAULT_ANCHORS` expertes : écarts en Elo par ancre — c'est la mesure de « combien le barème expert se trompait », précieuse pour le récit produit et pour le Lot A.

---

## 4. Variante : co-calibration Rasch avec ancres TIMSS

À n'engager **que si** la checklist §4.0 est verte. Apport : ancrer l'échelle Atlas sur une métrique **internationale documentée** au lieu d'un examen local — le pont C1.1 (1 logit ≈ 173.72 Elo ; θ_logit = (Elo−1500)·ln(10)/400) rend la co-calibration mathématiquement directe.

### 4.0 Checklist licence IEA — À COMPLÉTER AVANT TOUT ENGAGEMENT

Le cadrage (risque #3) impose la vérification **avant** d'engager quoi que ce soit — ni intégration d'items, ni promesse à une école, ni deck qui mentionne TIMSS :

- [ ] 1. Identifier précisément les items visés : items **libérés** (released items) TIMSS mathématiques Grade 4 (et Grade 8 si G6+ un jour), cycle(s) concerné(s).
- [ ] 2. Lire les conditions d'utilisation publiées par l'IEA pour les released items : l'usage **recherche/éducation non commerciale** est généralement permis avec attribution ; **Atlas est un usage commercial** → autorisation écrite préalable requise. Ne pas extrapoler depuis l'usage académique.
- [ ] 3. Adresser une demande écrite à l'IEA (Amsterdam) et/ou au TIMSS & PIRLS International Study Center (Boston College) décrivant : usage (ancres embarquées dans un produit commercial), volumes, durée, pays (EAU/GCC), et le fait que les statistiques d'items publiées seront utilisées comme valeurs d'ancrage.
- [ ] 4. Couvrir explicitement les **versions arabes** : l'étude est bilingue EN/AR (C-0) ; utiliser les traductions officielles IEA (celles administrées dans le Golfe) suppose une autorisation propre — ne pas retraduire soi-même (ça détruirait la valeur d'ancrage ET poserait un problème de droits).
- [ ] 5. Couvrir l'**adaptation de format** : le rendu des items dans l'UI Atlas est une adaptation — vérifier qu'elle est permise et sous quelles contraintes (fidélité visuelle, mention de source).
- [ ] 6. Obtenir la réponse **par écrit** ; l'archiver dans le dossier juridique du pilote.
- [ ] 7. Décision : verte → §4.1 ; refusée ou ambiguë → **fallback D-C3** (examens internes seuls, §3 sans variante) et on le note au rapport. Une licence « probablement OK » n'est pas verte.
- [ ] 8. Échéance : la réponse IEA doit être obtenue **avant T0** (les ancres doivent être servies dès le début de la fenêtre pour accumuler des réponses). Sinon : pilote en méthode principale seule, TIMSS repoussé au pilote suivant.

### 4.1 Design d'ancrage

- **8–12 items TIMSS par grade** (assez pour purifier sans tomber sous 6 — §4.3), couvrant la plage de difficulté du grade, servis dans le flux adaptatif normal, flaggés `is_anchor` en base.
- Difficultés **gelées** aux valeurs publiées TIMSS converties en Elo via le pont C1.1 (le mécanisme existe déjà : burn-in `ITEM_BURN_IN = 20` gèle la difficulté au prior, `elo.py` — pour une ancre, le gel est permanent : K_item = 0 sans limite).
- Exposition cible : ≥ 100 réponses par item d'ancre sur la fenêtre (piloter via l'état hebdomadaire §1.5.2).

### 4.2 Étapes de calcul

1. Extraire du journal `Response` la matrice élèves × items (réponses dichotomiques, filtres d'hygiène §1.3), fenêtre complète.
2. Ajuster un **modèle de Rasch** (estimation conditionnelle ou JML avec correction, ou MML — au choix de l'outillage, documenté) avec les difficultés des items d'ancre **fixées** à leurs valeurs TIMSS (en logits).
3. Vérifier les ancres (§4.3) ; purifier si nécessaire ; ré-ajuster.
4. Les θ estimés sont alors exprimés dans la métrique TIMSS ; les reconvertir en Elo (pont C1.1) et construire l'AnchorTable aux mêmes percentiles {5, 25, 50, 75, 95} : `elo_p` = quantile p des θ convertis ; `level_p` = position par rapport aux repères internationaux TIMSS (benchmarks publiés), libellée comme telle.
5. SE : par bootstrap élèves (identique §3.3) ; les SE conditionnelles Rasch (information de Fisher) sont reportées en complément.
6. **Convergence des deux méthodes** : si §3 (examens internes) et §4 (TIMSS) ont tourné tous les deux, comparer les tables — écart par ancre en Elo et en SE. La concordance est un argument de validité majeur ; la discordance se documente (elle dit quelque chose de l'examen interne).

### 4.3 Critères de qualité des ancres (avant d'accepter la co-calibration)

- **Déplacement** : ré-estimer librement chaque ancre et comparer à sa valeur fixée — |déplacement| < 0.5 logit (≈ 87 Elo), sinon l'item sort du jeu d'ancres (purification) ;
- **Fit** : infit/outfit dans [0.7, 1.3] ;
- **Minimum** : ≥ 6 ancres survivantes par grade, sinon la variante est abandonnée pour ce grade (retour méthode principale seule) ;
- **DIF EN/AR sur les ancres** (nécessite C-0) : une ancre à DIF sévère sort du jeu — une ancre biaisée entre langues contaminerait toute l'échelle.

---

## 5. Format de sortie : AnchorTable empirique + SE

### 5.1 L'objet cible existe déjà

`src/restitution/scale.py` définit :

```python
class Anchor(NamedTuple):
    elo: float
    percentile: float    # [0..100]
    level: str           # ex. "G3", "G4"

class AnchorTable:
    """Table de correspondance Elo → percentile/niveau, CONFIGURABLE (pas en dur)."""
```

et la table par défaut est explicitement provisoire : *« Table d'ancrage par défaut (barème expert ; à remplacer par cohorte réelle plus tard). »* (`DEFAULT_ANCHORS`). **Le livrable de l'étude est le remplaçant de ce défaut** : une liste d'`Anchor` par grade équaté, injectée par configuration — zéro changement de moteur, zéro changement d'interface de restitution (`restitute()` et la fourchette basse-confiance ±150 restent tels quels).

### 5.2 Format de livraison

Un fichier de configuration versionné (PR dédiée) :

```json
{
  "calibration_id": "pilote-2026T1-G4",
  "freeze_date": "2026-XX-XX",
  "method": "equipercentile_loglinear | rasch_timss",
  "n": 87,
  "schools": 2,
  "anchors": [
    {"elo": 1042, "percentile": 5,  "level": "…", "se_elo": 61, "ci95": [922, 1160]},
    {"elo": 1315, "percentile": 25, "level": "…", "se_elo": 34, "ci95": [1248, 1382]},
    {"elo": 1518, "percentile": 50, "level": "…", "se_elo": 29, "ci95": [1461, 1575]},
    {"elo": 1779, "percentile": 75, "level": "…", "se_elo": 33, "ci95": [1714, 1844]},
    {"elo": 2088, "percentile": 95, "level": "…", "se_elo": 57, "ci95": [1976, 2200]}
  ],
  "report": "Rapport-Calibration-pilote-2026T1-G4.md",
  "pipeline_commit": "<sha>"
}
```

(Valeurs illustratives.) Le chargement en prod ne consomme que `(elo, percentile, level)` — la signature d'`Anchor` est inchangée ; `se_elo`/`ci95` vivent dans la config et le rapport, et alimentent l'affichage « ±X » de C5 étage 1. Si on décide plus tard d'exposer la SE dans l'UI, étendre `Anchor` sera une évolution de `scale.py` distincte de cette étude.

### 5.3 Invariants à vérifier au chargement (test automatisé)

- percentiles strictement croissants avec l'Elo (l'interpolation linéaire de `AnchorTable.percentile()` le suppose) ;
- 5 ancres minimum, couvrant p5–p95 ;
- `calibration_id` et `pipeline_commit` présents (traçabilité) ;
- la table experte `DEFAULT_ANCHORS` reste le fallback si aucune calibration n'est configurée — mais alors l'UI reste en wording C5 étage 0.

---

## 6. Critères d'acceptation (chiffrés — issus du cadrage §3/C2, rendus opérationnels)

| # | Critère | Seuil | Si non atteint |
|---|---|---|---|
| A1 | **SE de chaque cut < demi-largeur de la bande qu'il sépare** | pour chaque paire d'ancres adjacentes (elo₁, elo₂) : `SE_bootstrap(cut) < (elo₂ − elo₁)/2` | l'ancre concernée est publiée comme **provisoire** avec SE affichée ; pas de niveau communiqué sur cette frontière (fourchette seulement) |
| A2 | **Corrélation Atlas/référence ≥ 0.6** (Pearson, brute, par grade) | r ≥ 0.6 | **ne pas forcer l'equating.** Diagnostic documenté : fidélité de Y ? restriction de variance (classe homogène) ? désengagement Atlas ? mauvais crosswalk de contenu ? → rapport §7 section 8, décision explicite (refaire avec autre référence / autre fenêtre) |
| A3 | **n par grade ≥ 50** (inclus, appariés, dans la fenêtre) | n ≥ 50 ; cible 100 | publication « provisoire, n=…, SE=… » (C5 étage 1 dégradé) ; jamais de publication sans le n |
| A4 | Monotonie et bornes | ancres strictement croissantes ; p5 et p95 dans [ELO_MIN, ELO_MAX] avec marge | erreur de pipeline — corriger avant toute livraison |
| A5 | Invariance inter-écoles (si ≥ 2 écoles) | ancres par école dans ±1 SE des ancres poolées | publication poolée + limite documentée (pas de claim de généralisation) |
| A6 | (Variante Rasch) qualité des ancres | §4.3 intégralement | abandon de la variante pour le grade, retour méthode principale |

Règle générale (alignée C5) : **un critère manqué ne se cache pas, il se documente**. La crédibilité du dispositif vient de là.

---

## 7. Template du rapport de calibration

`Rapport-Calibration-<pilote>-<grade>.md` — sections obligatoires :

1. **Résumé exécutif** (1 page) : méthode, n, table livrée, critères A1–A6 ✔/✘, claims autorisés (renvoi C5 étage 1).
2. **Contexte et design** : écoles, grades, fenêtre effective (dates réelles), référence Y retenue et pourquoi (D-C3), écarts au présent protocole (chacun motivé).
3. **Échantillon** : flux CONSORT-like — exposés → seuil d'inclusion atteint → Y disponible → appariés → analysés ; motifs d'exclusion comptés ; répartition par école/grade/langue servie (EN/AR, via `Response.language` — C-0).
4. **Données** : hash et horodatage des exports, version du pipeline (`pipeline_commit`), hygiène appliquée (§1.3).
5. **Méthode** : degré C du lissage retenu et justification, paramètres bootstrap, tout choix résiduel documenté.
6. **Résultats** : AnchorTable + SE + IC95 (format §5.2) ; nuage X–Y ; corrélations ; écarts vs table experte ; sensibilité (§3.4) ; invariance (§2.4) ; le cas échéant, convergence équipercentile vs Rasch (§4.2.6).
7. **Critères d'acceptation** : tableau A1–A6, verdicts, conséquences appliquées.
8. **Limites et diagnostics** : tout critère manqué, toute anomalie, généralisation (population pilote uniquement).
9. **Décision de publication** : table activée en prod (oui/non), wording C5 correspondant, signature fondateur + (si C6) relecture externe.
10. **Annexes** : distributions, fréquences lissées vs observées, table bootstrap complète, correspondance des consignes écoles signées.

---

## 8. Protection des données — RGPD / PDPL (EAU)

Principe : **l'étude tourne entièrement en pseudonymisé** ; personne côté analyse ne voit une identité d'élève.

**Ce que le schéma garantit déjà** (`src/models/measurement.py`) :
- `Response` est un événement **append-only** qui ne porte **aucune donnée identifiante directe** : uniquement des UUID (`student_id`, `school_id`, `item_id`, `competency_id`), `is_correct`, `response_time_ms`, `session_id`, `created_at` (+ `language` post-C-0). Pas de nom, pas de date de naissance, pas de texte libre.
- `Student` ne porte lui-même que des références (`external_ref`, `user_id`) — l'identité vit dans le système de l'école ;
- soft-delete (`deleted_at`) et **legal hold** individuel et tenant-large (`legal_hold`, `legal_hold_reason`, commentaires du modèle) articulés avec la purge de rétention (`scripts/purge_retention.py`) : un élève supprimé/retiré sort de l'échantillon au gel (§2.3), un legal hold suspend sa purge sans le réinjecter dans l'analyse.

**Mesures propres à l'étude** :
1. **Double pseudonymisation** : `study_id = HMAC(student.id, sel_étude)` — la table `study_id ↔ student.id` reste chez Atlas (accès fondateur uniquement, journalisée) ; la réidentification nominative n'est possible que chez l'école, qui est la seule à en avoir besoin (distribuer les examens). Aucun fichier échangé ne contient de nom.
2. **Minimisation** : l'export d'analyse contient exactement les champs du §1.6, rien d'autre (pas de `session_id`, pas d'horodatages fins au-delà de la date de passation).
3. **Base et rôles** : l'école est controller des données élèves, Atlas processor — l'étude de calibration est couverte par une **annexe au DPA du pilote** (finalité : calibration de l'échelle de restitution ; catégories de données ; durée) signée avant T0 (prérequis P4). Information des parents via le canal école conformément au dispositif du pilote et au droit local (PDPL EAU, Federal Decree-Law 45/2021 ; RGPD si des personnes concernées y sont soumises).
4. **Rétention** : fichiers appariés (X+Y) supprimés du poste d'analyse à la publication du rapport ; seuls survivent l'AnchorTable (aucune donnée individuelle), le rapport (agrégats uniquement) et l'export X pseudonymisé archivé selon la politique de rétention existante.
5. **Agrégats publiables** : aucune statistique publiée sur une cellule < 5 élèves (école × grade × langue) — règle anti-réidentification.
6. **Équité linguistique** : `Response.language` (C-0) permet de reporter la composition EN/AR de l'échantillon et, en C4, le DIF — l'étude de calibration n'introduit aucune collecte nouvelle à ce titre, elle consomme le journal existant.

---

## 9. Risques opérationnels et mitigations (spécifiques à l'exécution)

| # | Risque | Mitigation |
|---|---|---|
| 1 | Fenêtre manquée (examens école décalés) | date de gel calée avec l'école dès la signature ; la règle ±3 semaines absorbe un décalage modéré ; sinon gel déplacé (jamais la règle élargie) |
| 2 | Attrition > prévue (seuil d'inclusion non atteint) | état hebdomadaire au coordinateur (§1.5.2) ; relance à mi-fenêtre ; recrutement à 2× le plancher (§2.1) |
| 3 | Y de mauvaise qualité (examen trop facile → plafond, granularité faible) | exigences minimales §1.4 vérifiées AVANT la fenêtre sur le sujet d'examen de l'an passé ; si plafond constaté : documenter, ancres hautes marquées provisoires |
| 4 | Licence IEA tardive | §4.0 point 8 : pas de réponse avant T0 = pas de variante TIMSS ce pilote — la méthode principale ne dépend de rien d'externe |
| 5 | Pipeline défaillant découvert sur données réelles | P3 bloquant : répétition générale complète sur cohorte synthétique, y compris bootstrap et génération du rapport |
| 6 | Pression pour publier malgré critères manqués | §6 : chaque échec a une conséquence pré-écrite (provisoire/fourchette/non-publication) — décidée maintenant, pas sous pression |

---

*Ce protocole est le livrable C2 du Lot C. Son exécution est prévue pendant le pilote (cadrage §4, ligne « Exécution »). La version vendue aux écoles (D-C1 : la calibration comme livrable payé du pilote) reprend §1.5 et §7 côté école.*
