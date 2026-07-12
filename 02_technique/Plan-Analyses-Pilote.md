# Plan d'analyses de validité et d'équité — pilote

**Version** : v1 · **Date** : 2026-07-11 · **Livrable** : C4 du Cadrage-LotC (`01_strategie/Cadrage-LotC-Mesure-Defendable.md` §3/C4)
**Scripts** : `04_code/scripts/analysis/` — `dif_en_ar.py`, `item_fit.py`, `reliability.py`, `invariance.py`, `speededness.py`
**À lire avec** : Manuel Technique de Mesure (C1) pour le pont Elo↔logit et les limites du modèle ; `scripts/run_quarantine.py` (seul script autorisé à MODIFIER l'état des items).

---

## 1. Objet et principes

Cinq analyses sur le journal `Response` (append-only — support idéal : rien n'est jamais réécrit, tout est rejouable), qui transforment les promesses du produit en preuves ou en actions correctives pendant le pilote :

| # | Analyse | Script | Question à laquelle elle répond | Prérequis data |
|---|---|---|---|---|
| 1 | **DIF EN/AR** (Mantel-Haenszel) | `dif_en_ar.py` | Un item est-il plus dur dans une langue que dans l'autre, à niveau égal ? *(LA preuve de la promesse bilingue)* | **C-0** : `response.language` migrée ET alimentée |
| 2 | **Item fit** | `item_fit.py` | Le comportement observé de chaque item colle-t-il au modèle logistique ? | n ≥ 30 réponses/item |
| 3 | **Fidélité** (split-half pair/impair + Spearman-Brown) | `reliability.py` | La mesure par compétence est-elle stable ou du bruit ? | ≥ 6 réponses/élève×compétence, ≥ 10 élèves/compétence |
| 4 | **Invariance inter-écoles** | `invariance.py` | Les difficultés estimées sont-elles les mêmes d'une école à l'autre (±SE) ? | ≥ 2 écoles, ≥ 20 réponses/item×école |
| 5 | **Speededness** | `speededness.py` | Quelles réponses ne sont pas des mesures (rapid guessing < 2 s) ? | aucun — `response_time_ms` loggé depuis l'origine |

**Principes communs** (tous les scripts) :
- **Lecture seule.** Aucun script d'analyse n'écrit en base. La seule action d'état (quarantaine) reste le monopole de `run_quarantine.py` (dry-run par défaut, audité, verrouillé).
- **Stdlib + SQLAlchemy uniquement** (pas de pandas/scipy — les valeurs critiques χ²/z sont codées en dur et documentées). Sortie **JSON sur stdout** → archivable, diffable, agrégeable par le tableau de bord (§5).
- **Anti-bruit d'abord** : chaque script a des seuils de n minimal ; en dessous, il rend `insufficient` au lieu d'un chiffre trompeur. Sur un pilote, « pas encore mesurable » est une réponse honnête et défendable.
- **Dépendance C-0 (rappel bloquant).** La colonne `response.language` est ajoutée par un chantier séparé (migration Alembic + locale de session, Cadrage-LotC §3/C-0) ; au 2026-07-12 elle est présente dans le modèle ORM (`src/models/measurement.py`) mais les bases existantes peuvent ne pas être migrées. `dif_en_ar.py` y accède défensivement à DEUX niveaux : `getattr` sur le modèle ET inspection du schéma de la base réelle avant tout SELECT (un modèle plus récent que la base ferait planter la requête sinon). Tant que la colonne est absente ou vide, il sort un rapport vide avec `warning` explicite au lieu de planter — et les quatre autres scripts sélectionnent leurs colonnes explicitement (jamais l'entité complète), donc tournent sur une base pré-migration. **Aucune collecte pilote ne doit démarrer sans C-0 appliquée ET alimentée** — un journal append-only ne se backfille pas.

---

## 2. Calendrier d'exécution pendant le pilote

Pilote type : ~10 semaines (S0 = signature, S1 = premières réponses).

| Quand | Quoi | Pourquoi à ce moment |
|---|---|---|
| **S0 (avant toute donnée)** | Banc d'essai synthétique complet (§4) + vérification C-0 (une réponse de test porte bien `language`) | Le pipeline est validé AVANT la première vraie donnée ; la fenêtre de collecte du pilote est unique et ne se rejoue pas |
| **S1–S2, quotidien** | `speededness.py` | Détection immédiate des problèmes de démarrage : élèves qui cliquent au hasard (onboarding raté), items devinable sans lecture, client qui n'envoie pas `response_time_ms` (`n_missing_time` > 0 = bug de collecte à corriger sous 48 h) |
| **Dès S2, hebdomadaire** | `speededness.py` + `item_fit.py` (+ `run_quarantine.py --dry-run` en croisement) | L'item fit devient signifiant dès que des items passent n ≥ 30 ; retirer tôt un item défectueux limite la pollution des estimations |
| **S4–S5 (mi-pilote)** | **1er passage DIF** `dif_en_ar.py` + `reliability.py` | Premier point où assez d'items ont ≥ 10 réponses PAR langue ; un DIF C détecté à mi-pilote laisse le temps de régénérer et re-mesurer l'item avant la fin |
| **S4–S5** | `invariance.py` (si ≥ 2 écoles actives) | Détecter un biais de passation d'école (surveillance, aide des enseignants…) pendant qu'on peut encore le corriger |
| **Hebdomadaire dès S5** | Les 5 analyses + tableau de bord (§5) | Routine de croisière ; le tableau de bord alimente le point hebdo écoles |
| **S9–S10 (clôture)** | **Passage final complet**, réponses rapides EXCLUES (liste `rapid_response_ids` de speededness) | C'est le passage qui entre dans le rapport de calibration (C2) et le dossier de défendabilité ; l'exclusion des non-mesures est documentée, pas silencieuse |

Ordre d'exécution d'un passage complet : **speededness d'abord** (elle produit la liste d'exclusion), puis DIF / fit / fidélité / invariance sur les données filtrées.
*Limite v1 assumée : les squelettes ne consomment pas encore la liste d'exclusion (chaque script lit tout le journal) — le branchement `--exclude-rapid <fichier>` est la première évolution prévue (§6).*

Commande type (prod, lecture seule) :
```bash
cd 04_code
DATABASE_URL=postgresql://... .venv/bin/python scripts/analysis/speededness.py > out/speededness_$(date +%F).json
```

---

## 3. Seuils d'action

### 3.1 DIF EN/AR (`dif_en_ar.py`) — classification ETS

Odds ratio commun de Mantel-Haenszel sur strates par **déciles d'ability**, converti en delta ETS (ΔMH = −2.35·ln α_MH), significativité par χ² MH (correction de continuité) et SE Robins-Breslow-Greenland :

| Classe | Critère | **Action** | Délai |
|---|---|---|---|
| **A** (négligeable) | \|ΔMH\| < 1.0 OU non significatif (χ² < 3.841) | Aucune | — |
| **B** (modéré) | 1.0 ≤ \|ΔMH\| < 1.5, significatif | **Revue linguiste** : comparaison côte à côte EN/AR (wording, faux-amis, registre, chiffres arabes/occidentaux), correction de la version fautive, re-suivi au passage suivant | ≤ 1 semaine |
| **C** (sévère) | \|ΔMH\| ≥ 1.5 ET significativement > 1.0 | **Retrait immédiat** du pool (quarantaine via le circuit `review.promote`) + **régénération** de l'item (pipeline Lot A) ; l'item retiré reste dans le journal pour l'audit | ≤ 48 h |

Le champ `favors` indique la langue avantagée — un déséquilibre systématique dans un seul sens (ex. tous les C défavorisent l'arabe) incrimine le pipeline de traduction, pas les items un à un → escalade Lot A (`translate_bank_ar.py`, `check_ar_fidelity.py`).

### 3.2 Item fit (`item_fit.py`)

Mêmes seuils que le garde-fou quarantaine (cohérence voulue : tout item flaggé ici sera saisi par le cron) : n ≥ 30, divergence globale observé/attendu > 0.40, référence = ability moyenne réelle des répondants.

| Signal | Action |
|---|---|
| `flagged: true` | Vérifier qu'il apparaît au prochain `run_quarantine.py --dry-run` ; si urgent, exécuter le job |
| Divergence globale OK mais bins inversés (observé décroît quand l'ability monte) | Item piège / clé de réponse fausse → revue de contenu manuelle, croiser avec le DIF |
| `mean_abs_bin_divergence` > 0.15 sans flag global | Mettre l'item en observation (liste de suivi), ne pas quarantainer sur ce seul signal |

### 3.3 Fidélité (`reliability.py`)

Split-half pair/impair (positions chronologiques) par élève × compétence, corrélation inter-moitiés corrigée Spearman-Brown. Seuils indicatifs pilote (flux adaptatif : ordre de grandeur, pas un alpha de test fixe — limite documentée dans le manuel C1) :

| r_SB | Action |
|---|---|
| ≥ 0.7 | RAS — citable en restitution |
| 0.5 – 0.7 | Publier avec réserve (fourchette/SE affichée, conforme C5 étage 0-1) ; augmenter le nombre de réponses ciblées sur la compétence |
| < 0.5 | **Alerte** : suspendre la restitution de cette compétence (bande « en cours de mesure ») ; audit des items de la compétence (fit + DIF) avant réactivation |

### 3.4 Invariance inter-écoles (`invariance.py`)

Difficulté ré-estimée PAR ÉCOLE (inversion logistique + SE par méthode delta), comparaison par paires : non-invariant si z > 1.96.

| Signal | Action |
|---|---|
| Quelques items non-invariants, biais moyen d'école ≈ 0 | Revue item par item (croiser DIF + fit) : probable ambiguïté de contenu |
| `school_mean_bias_elo` décalé constant pour UNE école (> ~50 Elo) | Cause école, pas items : conditions de passation (aide, temps, matériel) → visite/entretien coordinateur avant toute décision sur les items |
| Non-invariance massive (> 20 % des items comparables) | Geler l'interprétation inter-écoles ; ne restituer qu'intra-école tant que la cause n'est pas comprise |

### 3.5 Speededness (`speededness.py`)

| Signal | Seuil | Action |
|---|---|---|
| Réponse rapide | < 2 000 ms (`--threshold-ms`) | Exclusion de TOUTES les analyses et de la calibration C2 (liste `rapid_response_ids`) ; le journal reste intact |
| Élève désengagé | > 10 % de réponses rapides sur ≥ 10 réponses | Signal enseignant via la restitution (« résultats non interprétables cette semaine ») ; exclusion de l'étude de calibration |
| Item à médiane < 2 s | ≥ 10 réponses | Item devinable sans lecture → revue de contenu |
| `n_missing_time` > 0 | dès 1 | Bug de collecte côté client → correctif prioritaire (donnée irrécupérable) |

---

## 4. Banc d'essai synthétique (avant toute vraie donnée)

Objectif : **le pipeline complet tourne et détecte des défauts PLANTÉS avant la première réponse réelle** — on ne découvre pas un bug d'analyse pendant l'unique fenêtre de collecte.

Support : `scripts/simulate_cohort.py` paramétré (errata E10 du Lot A). Aujourd'hui la simulation rejoue les fonctions pures sans DB ; l'extension prévue (`--emit-db sqlite:///bench.db`) matérialise la cohorte synthétique dans une base jetable au schéma réel :

1. **Monde synthétique** : 2 écoles (School), 40+ élèves à ability vraie cachée, items à difficulté vraie connue, réponses tirées selon `expected_score` — exactement la mécanique actuelle de `simulate_cohort.py`, écrite dans `Response`/`Student`/`StudentCompetencyAbility` au lieu de rester en mémoire. Langue `en`/`ar` alternée par élève (50/50) — exige C-0 sur le schéma de la base jetable.
2. **Défauts plantés** (chacun vise UN script) :
   - 2 items dont la version AR est durcie de **+85 Elo** (≈0.5 logit — cible DIF B) et 1 item durci de **+280 Elo** (≈1.6 logit — cible DIF C) ; pénalités posées sur l'échelle Elo/logit et non en probabilité absolue, pour que la classe ETS visée ne dépende pas de la difficulté de l'item porteur (validé sur le prototype du banc, cf. §4.4) ;
   - 1 item dont les réponses sont tirées à difficulté vraie décalée de +400 Elo par rapport à sa difficulté déclarée (cible item fit / quarantaine) ;
   - 1 école dont toutes les réponses sont tirées avec un bonus d'ability de +100 (cible invariance, biais d'école constant) ;
   - 5 % des réponses avec `response_time_ms` tiré < 2 s ET is_correct aléatoire 50/50, concentrées sur 3 élèves (cible speededness) ;
   - 1 compétence dont les réponses sont du bruit pur (p = 0.5 quel que soit l'élève — cible fidélité < 0.5).
3. **Critères de réussite du banc** (bloquants avant pilote) :
   - chaque défaut planté est détecté par le script visé (DIF classé B/C sur les bons items, etc.) ;
   - **zéro faux positif** sur les items/écoles/élèves sains (même exigence que l'AC4 de la simulation moteur) ;
   - `DATABASE_URL=sqlite:///bench.db` : les 5 scripts sortent un JSON valide, parsable par le tableau de bord ;
   - reproductible (seed fixe, même convention que `simulate_cohort.py`).
4. **État v1 (validé 2026-07-12)** : les 5 squelettes passent `py_compile` ET ont tourné sur deux bases :
   - **base de dev non migrée C-0** (`atlas_dev.db`, 144 réponses seed) — dégradation propre vérifiée : `dif_en_ar` sort son `warning` C-0 (colonne absente de la base), `speededness` compte 144 `n_missing_time` (seeds sans temps), aucun crash malgré le modèle ORM plus récent que la base ;
   - **base synthétique jetable au schéma réel** (préfiguration du banc §4 : 2 écoles, 160 élèves, 16 items, 2 560 réponses, seed fixe) avec les défauts plantés ci-dessus (pénalités DIF posées sur l'échelle Elo : +85 Elo ≈ 0.5 logit pour la cible B, +280 Elo ≈ 1.6 logit pour la cible C) — **tous détectés, zéro faux positif** : DIF B classé B (ΔMH = −1.89), DIF C classé C (ΔMH = −3.50), tous deux `favors: en` (défavorisent l'arabe, direction plantée), item misfit seul flaggé (divergence 0.64), compétence bruit seule en alerte (r_SB = 0.09 vs 0.66 pour la saine), biais d'école retrouvé dans `school_mean_bias_elo` (signe et école corrects — magnitude atténuée par l'hétérogénéité des abilities, lecture qualitative), les 3 rapid-guessers exactement identifiés.

   L'extension `--emit-db` de simulate_cohort (E10) reste le support officiel du banc ; la leçon du prototype à reprendre : planter les pénalités DIF en **logit/Elo** (uniformes) et non en probabilité absolue, sinon la classe ETS obtenue dépend de la difficulté de l'item porteur.

---

## 5. Tableau de bord de synthèse

Produit à chaque passage hebdomadaire (S5+) à partir des 5 JSON, pour le point interne et le point école. Un indicateur par ligne, trois états : 🟢 (RAS) / 🟠 (action en cours) / 🔴 (action bloquante en retard).

| Indicateur | Source (champ JSON) | 🟢 | 🟠 | 🔴 |
|---|---|---|---|---|
| Couverture langue | `dif_en_ar.n_language_unknown` / `n_responses_total` | 0 % | < 1 % | ≥ 1 % ou `warning` C-0 |
| Items DIF B ouverts | `counts_by_class.B` moins revues linguiste closes | 0 | ≤ 3 en revue < 1 sem | > 3 ou revue > 1 sem |
| Items DIF C | `counts_by_class.C` | 0 | retrait fait < 48 h | item C encore servi |
| Items en dérive (fit) | `item_fit.n_flagged` | 0 | flaggés = quarantainés | flaggé non quarantainé |
| Fidélité | `reliability` : min des `r_spearman_brown` | ≥ 0.7 partout | 0.5–0.7 quelque part | `n_alerts` > 0 |
| Invariance | `invariance.n_items_non_invariant` / `n_items_comparable` | < 5 % | 5–20 % en revue | > 20 % ou biais école > 50 Elo inexpliqué |
| Rapid guessing | `speededness.rapid_rate_global` | < 3 % | 3–10 % | > 10 % ou `n_missing_time` > 0 |
| Élèves désengagés | `speededness.n_students_flagged` | 0 | signalés à l'enseignant | récurrents 2 passages de suite |

Complété par 3 compteurs de contexte : nb réponses cumulées, nb items ayant atteint n ≥ 30 (donc jugeables), nb items ayant ≥ 10 réponses par langue (donc DIF-analysables) — ces compteurs disent quand les analyses deviennent signifiantes, et calibrent les attentes de l'école.

Implémentation v1 : agrégation manuelle des JSON dans une note hebdo (les champs ci-dessus sont stables par contrat) ; un `dashboard.py` qui lit les 5 fichiers et sort le markdown est l'évolution naturelle une fois les formats gelés.

**Usage conforme C5** : ce tableau de bord est un outil INTERNE + point école. Aucun chiffre ne sort dans un deck sans passer la politique de claims (`Politique-Claims-Mesure.md`) — au stade pilote on est à l'étage 0/1 : « données pilote, n=…, SE=… », jamais « calibré ».

---

## 6. Limites v1 et évolutions prévues

1. **Ability actuelle, pas ability au moment de la réponse** (`item_fit`, `dif_en_ar`, `invariance`) : le journal ne fige pas l'ability du répondant à l'instant t. Approximation acceptable sur un pilote court ; si besoin, l'ability à l'instant t est reconstructible en rejouant le journal (append-only) — évolution candidate.
2. **Pas encore de filtre d'exclusion partagé** : brancher `--exclude-rapid <json>` sur les 4 autres scripts pour consommer la sortie de speededness (première évolution, cf. §2).
3. **DIF : MH seul en v1** — la régression logistique (DIF non uniforme, réf. Swaminathan & Rogers, citée au cadrage) viendra en complément ; MH détecte le DIF uniforme, qui est le mode de défaillance attendu d'une traduction.
4. **Fidélité sur flux adaptatif** : r_SB est un ordre de grandeur (items non parallèles entre moitiés) ; la stabilité re-test des θ sur sessions rapprochées (citée en C4.3) complétera quand les sessions seront assez denses.
5. **`response.language` défensif** : la colonne est fusionnée dans le modèle ORM ; quand toutes les bases cibles (dev, CI, prod) seront migrées C-0, retirer le chemin défensif de `dif_en_ar.py` (`getattr` + inspection du schéma + `warning`) et rendre la colonne obligatoire dans l'analyse (échec bruyant si absente). Le rapport expose d'ici là `language_column_in_model` et `language_column_present` (présence dans la base interrogée) pour diagnostiquer une base en retard de migration.
