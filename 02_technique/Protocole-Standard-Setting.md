# Protocole de Standard-Setting — Méthode Bookmark (Livrable C3)

**Version** : v1 · **Date** : 2026-07-11 · **Auteur** : cadrage produit (Nassim + Claude)
**Référence cadrage** : `01_strategie/Cadrage-LotC-Mesure-Defendable.md` §3/C3
**À lire avec** : `Protocole-Calibration-Pilote.md` (C2, articulation §9), `Manuel-Technique-Mesure.md` (C1, pont Elo↔logit), `src/models/item.py` (champs du livret), `src/restitution/scale.py` (`AnchorTable`, destination des cut scores), `src/engine/elo.py` (fonction de réponse).
**Statut** : protocole prêt à exécuter — l'exécution a lieu **pendant le pilote**, avec le panel enseignant de l'école (D-C1 : livrable vendu du pilote).

---

## 1. Objet et principe

**Objet.** Établir les **cut scores** (seuils de coupure) qui séparent les niveaux de maîtrise communiqués aux familles et à l'école — *Beginning / Developing / Proficient / Advanced* — sur l'échelle Elo interne d'Atlas, par une procédure standard, documentée et défendable face à un Head of Assessment.

**Méthode retenue : Bookmark** (Lewis, Mitzel & Green, 1996 ; Mitzel et al., 2001), pour une raison structurelle : la méthode exige un livret d'items **ordonnés par difficulté empirique** — et Atlas produit déjà `difficulty_elo` par item en continu. Le livret ordonné est donc *gratuit* là où d'autres contextes doivent d'abord calibrer. La variante **Angoff modifié** est fournie en annexe A comme méthode de secours (si le panel est < 6 juges ou si les items disponibles post-filtre sont < 30).

**Principe en une phrase.** Chaque juge parcourt un livret d'items classés du plus facile au plus difficile et pose un « marque-page » sur le **premier item** qu'un élève *tout juste* au niveau visé (le « borderline student ») n'aurait **plus** 2 chances sur 3 de réussir. La position du marque-page, convertie en Elo via la convention RP67 (§4), donne le cut score.

**Sortie.** 3 cut scores (B/D, D/P, P/A) sur l'échelle Elo, avec statistiques d'accord inter-juges (§7), transposables en logits via le pont C1.1 (1 logit = 173,72 Elo), injectés dans l'`AnchorTable` (§9), et un rapport de défendabilité (§8).

---

## 2. Préparation du livret d'items ordonnés (OIB — *Ordered Item Booklet*)

### 2.1 Champs source (modèle `Item`, `src/models/item.py`)

| Champ | Usage dans le livret |
|---|---|
| `difficulty_elo` | **Clé de tri** du livret (ordre croissant). C'est la difficulté vivante (mise à jour par le moteur après burn-in de 20 réponses), pas le prior. |
| `difficulty_prior` | Contrôle qualité : signaler tout item où \|elo − prior\| > 200 (recalibration forte → vérifier l'item avant inclusion). |
| `n_responses` | **Filtre d'éligibilité** : n ≥ 20 minimum (fin du burn-in item, `ITEM_BURN_IN` dans elo.py — en dessous, `difficulty_elo` = prior gelé, donc pas une difficulté empirique). Cible : n ≥ 30. |
| `status` | Filtre : `ACTIVE` uniquement. Jamais `QUARANTINED` (fit divergent) ni `AI_GENERATED`/`HUMAN_REVIEWED`/`LINGUIST_VALIDATED` (pipeline de validation non achevé). |
| `deleted_at` | Filtre : `IS NULL`. |
| `content_en` / `content_ar` | Contenu affiché (JSONB validé : `stem`, `options`, `answer`). Livret EN et livret AR séparés. |
| `ar_validated` | **Obligatoire = true** pour le livret arabe. Un panel qui juge en arabe sur un item non validé linguistiquement produit un cut score contestable. |
| `answer_format` | Affiché sur chaque page (MCQ / NUMERIC / SHORT) — pertinent pour le jugement RP67 (voir limite guessing, §4.4). |
| `competency_id` | Affiché (libellé de la compétence) : les juges doivent savoir *ce que mesure* l'item. Rappel data model §4 : 1 item = 1 compétence, donc l'étiquette est non ambiguë. |
| `context_tags` | Contrôle de couverture : équilibrer les contextes (éviter un livret mono-thème). |
| `provenance` | Non affiché aux juges ; conservé dans l'archive du livret (traçabilité). |

### 2.2 Requête d'extraction (exécutable)

```sql
SELECT i.id, i.difficulty_elo, i.difficulty_prior, i.n_responses,
       i.answer_format, i.content_en, i.content_ar, i.competency_id,
       c.code AS competency_code,
       c.label_en, c.label_ar                    -- libellé selon la langue du livret
FROM item i
JOIN competency c ON c.id = i.competency_id
WHERE i.status = 'active'                        -- valeur stockée = member value (native_enum, base.py)
  AND i.deleted_at IS NULL
  AND i.n_responses >= 20
  AND (:lang = 'en' OR i.ar_validated = true)   -- livret AR : validation linguistique requise
ORDER BY i.difficulty_elo ASC, i.id ASC;         -- tri stable (id départage les ex æquo)
```

### 2.3 Règles de construction

1. **Taille** : 40–60 items (standard OIB). Minimum absolu 30 — en dessous, basculer sur Angoff (annexe A).
2. **Couverture** : le livret doit couvrir la plage où tomberont les cuts, soit au moins [1000, 2100] Elo (bornes de l'`AnchorTable` actuelle). Densité cible : pas d'écart > 100 Elo entre deux items consécutifs dans la zone [1300, 1900] (zone probable des 3 cuts). **Tout trou > 100 Elo borne mécaniquement la précision du cut dans cette zone — le documenter dans le rapport (§8).**
3. **Une page = un item**, dans l'ordre, avec : numéro d'ordre (1..N), énoncé, options/format, réponse correcte encadrée, compétence mesurée. **La valeur `difficulty_elo` n'apparaît PAS** sur les pages (anti-ancrage numérique des juges) ; seule la table de correspondance ordre→Elo, détenue par l'animateur, sert au calcul.
4. **Item map animateur** (confidentielle pendant les rounds) : `ordre | item_id | difficulty_elo | n_responses | compétence | format`.
5. **Deux livrets** (EN et AR) au contenu identique en ordre : le panel juge dans la **langue d'enseignement** de l'école pilote. Si les deux langues coexistent, deux sous-panels ou un panel bilingue avec livret bilingue — le choix est consigné au rapport.
6. **Gel** : le livret est extrait à date fixe (snapshot), archivé (CSV + PDF), et n'est plus modifié même si `difficulty_elo` continue d'évoluer en prod. Le cut score se réfère au snapshot ; la dérive ultérieure est traitée par la maintenance (§10).

---

## 3. Définitions des niveaux de performance (PLD — *Performance Level Descriptors*)

Les PLD sont **co-écrits avec l'école** (session de travail de 2 h, AVANT le jour du panel — voir §6.0). Atlas apporte les gabarits ci-dessous ; l'école les reformule dans son vocabulaire (MoE / inspection : Beginning–Developing–Proficient–Advanced ou équivalent local type Outstanding/Good framework). Les juges ne peuvent pas poser un marque-page fiable sans une image mentale partagée de « l'élève borderline » de chaque niveau.

**Gabarit à instancier PAR matière et PAR grade** (exemple : maths G4) :

| Niveau | Gabarit (à compléter avec l'école) | Élève borderline (le personnage que le juge incarne) |
|---|---|---|
| **Beginning** | Mobilise des procédures isolées sur des cas directs et familiers ; a besoin d'étayage pour toute variation. Ex. maths G4 : *additionne des fractions de même dénominateur, mais ne compare pas des fractions de dénominateurs différents.* | L'élève qui vient tout juste de sortir du décrochage complet sur le domaine. |
| **Developing** | Applique les procédures du grade sur des cas standards ; échoue dès que le contexte change ou que deux étapes s'enchaînent. Ex. : *compare des fractions simples, mais échoue sur les problèmes verbaux à deux étapes.* | L'élève qui réussit *tout juste* les exercices d'entraînement typiques. |
| **Proficient** | Maîtrise les attendus du grade : résout des problèmes à étapes multiples dans des contextes variés ; erreurs occasionnelles, non systématiques. | L'élève qui atteint *tout juste* le niveau attendu par le programme en fin de période. |
| **Advanced** | Transfère à des contextes non familiers ; justifie ses démarches ; résout des problèmes du grade supérieur. | L'élève qui dépasse *tout juste* les attendus (pas le prodige : le premier cran au-dessus de Proficient). |

**Règles d'écriture** (à faire respecter en session) : formulations **observables** (« résout / compare / justifie », pas « comprend ») ; chaque descripteur se distingue du précédent par au moins un comportement concret ; les PLD finaux sont signés par la direction pédagogique de l'école → pièce n°1 du rapport de défendabilité.

---

## 4. Convention RP67 : justification et formule

### 4.1 Définition

**RP67** (*Response Probability 67 %*) : le cut score d'un niveau est l'ability θ à laquelle l'élève borderline de ce niveau a une probabilité de **0,67** (2 chances sur 3) de réussir l'item marqué. Concrètement, le juge pose son marque-page sur le **premier item du livret** pour lequel il juge que l'élève borderline n'a **plus** 2 chances sur 3 de réussir.

### 4.2 Justification du choix de 0,67

- **Standard de fait** : RP67 est la convention dominante de la méthode Bookmark (Mitzel, Lewis, Patz & Green, 2001 ; Cizek & Bunch, *Standard Setting*, 2007, chap. 10) — utilisée par la majorité des programmes d'évaluation d'État américains. L'adopter, c'est être auditable dans le langage du métier.
- **Interprétabilité cognitive** : « 2 chances sur 3 » est le seuil communément accepté où l'on peut dire qu'un élève *sait faire* plutôt qu'il *devine ou tâtonne*. RP50 (une chance sur deux) assimilerait la maîtrise à un pile-ou-face — indéfendable devant des parents. RP80 est utilisé (ex. cartographies NAEP) mais durcit les cuts et rend le jugement plus difficile pour les juges (discriminer 80 % de 90 % de réussite est cognitivement plus dur que discriminer 2/3 de 1/2).
- **Symétrie des erreurs** : à RP67, mal classer un élève maîtrisant (faux négatif) et un élève non maîtrisant (faux positif) restent tous deux improbables sans être asymétriquement punitifs.

### 4.3 Formule sur l'échelle Elo (vérifiée numériquement)

Fonction de réponse d'Atlas (`expected_score`, elo.py) :

```
P(correct) = 1 / (1 + 10^((b − θ)/400))
```

On cherche l'écart θ − b tel que P = 0,67 :

```
0,67 = 1 / (1 + 10^((b−θ)/400))
⇔ 10^((b−θ)/400) = 0,33/0,67
⇔ θ − b = 400 · log10(0,67/0,33) = 123,02 ≈ +123 Elo
```

**Vérification** (calcul contrôlé le 2026-07-11) : `400·log10(0,67/0,33) = 123,024` et, en sens inverse, `P(θ−b = 123,02) = 0,670` exactement. En logits (pont C1.1, ×ln10/400) : 123,02 Elo = **0,708 logit** = ln(0,67/0,33) — cohérence parfaite avec la forme Rasch.

**Règle opératoire du calcul de cut** : si le juge *j* pose son marque-page sur l'item de difficulté `b_j` (le premier item « au-delà » des 2/3), alors son cut individuel est :

```
θ_j = b_j + 123 Elo
```

**Nuance assumée (à consigner au manuel C1)** : « 2 chances sur 3 » exact (P = 2/3) donnerait 400·log10(2) = **120,41 Elo** ; la convention P = 0,67 donne **123,02 Elo**. Écart : 2,6 Elo = 0,015 logit — négligeable devant la SE du panel (§7). **Convention Atlas retenue : +123 Elo (P = 0,67), figée ici et réutilisée partout** (scripts, rapport, manuel).

### 4.4 Limite : le guessing des MCQ

Le modèle d'Atlas (type Rasch) n'a pas de paramètre de pseudo-chance ; or un MCQ à 4 options a un plancher de réussite ~25 % au hasard. Traitement retenu (simple et standard) : **consigne explicite aux juges** — « jugez la probabilité que l'élève borderline réponde correctement *en sachant*, pas en devinant ». La sur-correction formelle (RP67 ajusté = c + 0,67·(1−c)) est écartée en v1 : elle complexifie le jugement pour un gain marginal, et le moteur ne modélise pas c. Limite consignée au rapport (§8) et dans C1.6.

---

## 5. Panel : recrutement et gestion des biais

### 5.1 Composition (6–10 juges)

Critères de recrutement (via la relation école du Lot A / D-A2) :

| Critère | Exigence |
|---|---|
| Expérience | ≥ 3 ans d'enseignement de la matière, dont ≥ 1 an sur le grade cible (G4–G5 en premier) |
| Couverture grades | Au moins 1 juge du grade N−1 et 1 du grade N+1 (vision du continuum) |
| Langue | Maîtrise de la langue du livret ; pour un panel AR, enseignants enseignant effectivement en arabe |
| Diversité | Si multi-écoles : ≥ 2 écoles représentées ; mixité ancienneté (éviter un panel 100 % seniors ou 100 % juniors) |
| Disponibilité | Session PLD (2 h) + journée panel complète — engagement écrit avant recrutement |
| Conflits d'intérêts | Aucun juge n'ayant participé à la **rédaction** des items du livret (séparation auteur/juge) |

Taille : **8 juges visés** (6 = minimum de validité, 10 = maximum de gérabilité). En dessous de 6 → reporter ou basculer Angoff (annexe A, plus tolérant aux petits panels avec plus d'items jugés par juge).

### 5.2 Gestion des biais (dispositif intégré au script §6)

| Biais | Mitigation opératoire |
|---|---|
| **Dominance hiérarchique** | Pas de membre de la direction dans la salle pendant les jugements ; tours de parole en round-robin lors des discussions ; les marque-pages restent **individuels et non signés publiquement** (l'animateur affiche la distribution anonymisée). |
| **Ancrage sur les chiffres** | Aucune valeur Elo visible des juges ; l'ordre des pages est la seule information de difficulté. |
| **Conformisme (round 2)** | La consigne du round 2 est « révisez *si les arguments vous ont convaincu* », jamais « rapprochez-vous de la médiane ». La convergence doit venir de la discussion des items, pas de la pression du groupe. |
| **Pilotage par l'impact** | Les données d'impact (§6, étape 6) sont présentées comme *information de réalité*, jamais comme cible (« il faudrait X % de Proficient » est une phrase interdite à l'animateur). Aucun quota n'est imposé. |
| **Fatigue / effet d'ordre** | 3 cuts jugés dans l'ordre croissant (B/D → D/P → P/A) avec pauses ; la journée est bornée à 6 h de travail effectif. |
| **Biais de sévérité individuelle** | Round d'entraînement (étape 3) avec feedback : chaque juge voit où il se situe par rapport au groupe *sur les items d'essai* avant le round réel. |

Chaque juge signe un accord de confidentialité (items non diffusables) et remplit en fin de journée le **questionnaire de validité procédurale** (annexe B) — pièce du rapport de défendabilité.

---

## 6. Script d'animation — 2 rounds + données d'impact

**Rôles** : 1 animateur (fondateur ou coordinateur formé — neutre, ne juge pas), 1 analyste (calculs entre rounds ; peut être le même avec le script §7.3 préparé), 6–10 juges.

### 6.0 — Pré-session PLD (J−7 à J−3, 2 h, avec l'école)
Co-écriture/validation des PLD (§3) avec 2–3 enseignants référents + direction pédagogique. Sortie : PLD signés, distribués aux juges à J−3 avec la consigne de lecture. **Le jour J ne commence jamais par l'écriture des PLD** (trop long, trop instable).

### 6.1 — Jour J (déroulé minuté, ~6 h 30 dont pauses)

| Heure | Étape | Contenu et verbatims clés |
|---|---|---|
| 09h00 | **1. Cadrage** (20 min) | But (« établir OÙ commencent Developing, Proficient, Advanced sur la mesure Atlas »), confidentialité, rappel : « il n'y a pas de bonne réponse attendue ; votre jugement professionnel EST la donnée ». |
| 09h20 | **2. Formation** (40 min) | Les PLD (relecture commentée) ; le concept d'élève borderline (« pensez à UN élève réel, tout juste Proficient ») ; la mécanique Bookmark ; la règle RP67 en langage juge : *« avancez dans le livret tant que votre élève borderline a au moins 2 chances sur 3 de réussir ; posez le marque-page sur le PREMIER item où ce n'est plus le cas »*. Insister : le livret est ordonné par difficulté **réelle observée** sur les élèves — un désaccord ressenti avec l'ordre se note en marge, il ne change pas l'ordre. Consigne guessing (§4.4). |
| 10h00 | **3. Round d'entraînement** (30 min) | Mini-livret de 5 items (hors livret réel), pose d'un marque-page D/P, mise en commun, correction des malentendus (les 2 erreurs classiques : juger « mes élèves en général » au lieu du borderline ; chercher l'item que le borderline rate *à coup sûr* au lieu de « moins de 2/3 »). |
| 10h30 | Pause (15 min) | |
| 10h45 | **4. ROUND 1** (75 min) | Silencieux, individuel. Chaque juge pose 3 marque-pages (B/D, D/P, P/A) dans l'ordre croissant, sur le formulaire de saisie (annexe B) : `juge_id | cut | n° de page | commentaire libre`. L'animateur ne répond qu'aux questions de procédure, jamais de contenu. |
| 12h00 | Déjeuner (60 min) | **L'analyste calcule** : pour chaque cut, distribution des pages, conversion pages→Elo (item map), médiane, min–max, SD (script §7.3). Prépare l'affichage anonymisé + la liste des items situés entre le marque-page min et max de chaque cut (la « zone de désaccord »). |
| 13h00 | **5. Discussion inter-rounds** (60 min) | Affichage par cut : distribution anonymisée des marque-pages + zone de désaccord. Pour chaque cut, discussion **item par item de la zone de désaccord** (round-robin : chaque juge dit en 1 min pourquoi son borderline réussit/échoue cet item). L'animateur reformule, ne tranche jamais. |
| 14h00 | **6. Données d'impact** (20 min) | L'analyste projette : « avec les cuts médians du round 1, la cohorte pilote se répartirait ainsi : X % Beginning, Y % Developing, Z % Proficient, W % Advanced » (calcul sur la distribution des ability `Learner` de la cohorte pilote — ou de la cohorte synthétique `simulate_cohort.py` si le panel précède les données réelles, en le disant explicitement). Verbatim imposé : *« Ceci est une information de conséquence, pas une cible. Si ces pourcentages vous surprennent, demandez-vous si c'est votre jugement ou la réalité de la cohorte qui les explique. »* |
| 14h20 | **7. ROUND 2 (final)** (45 min) | Silencieux, individuel. Chaque juge repose ses 3 marque-pages (peut garder les mêmes). Saisie sur formulaire round 2. |
| 15h05 | **8. Clôture** (25 min) | Questionnaire de validité procédurale (annexe B) ; annonce des cuts finaux (médianes round 2) ; rappel : les cuts seront publiés avec leur incertitude ; remerciements + suite (rapport sous 2 semaines). |

**Règle de décision finale** : cut = **médiane** des θ_j du round 2 (robuste aux juges extrêmes sur petit panel ; la moyenne est reportée en comparaison). Contrainte de monotonie : cut(B/D) < cut(D/P) < cut(P/A) — garantie par construction si chaque juge a posé ses marque-pages en ordre, à vérifier par l'analyste.

---

## 7. Statistiques d'accord inter-juges

### 7.1 Indicateurs (calculés par cut, aux rounds 1 et 2)

| Statistique | Formule | Rôle |
|---|---|---|
| Cut final | médiane des θ_j (round 2) | Valeur publiée |
| Dispersion | SD des θ_j (n−1 au dénominateur) | Accord inter-juges brut |
| Erreur-type du cut | SE = SD/√n | Incertitude de la procédure |
| IC 95 % | cut ± t₀.₉₇₅,ₙ₋₁ · SE (loi de Student, car n = 6–10 ; ex. n=8 → t=2,365) | Fourchette publiable |
| Convergence | SD(round 2) / SD(round 1) | Preuve que la discussion a fait son travail (attendu < 1) |
| Étendue | min–max des θ_j | Détection d'un juge aberrant (à discuter, jamais à exclure silencieusement) |

### 7.2 Critères d'acceptation (chiffrés)

- **SD(round 2) ≤ 100 Elo** (≈ 0,58 logit) par cut : accord suffisant, cut publié en valeur ponctuelle + IC.
- **100 < SD ≤ 150 Elo** : cut publié en **fourchette** (IC 95 %) avec mention explicite — conforme au risque n°5 du cadrage (« si instable, retenir la fourchette et le dire ») et à l'étage 2 de la politique C5.
- **SD > 150 Elo** après round 2 : cut non publié ; le rapport documente le désaccord (items de la zone, arguments) et programme un round 3 ou un panel élargi. **On ne force jamais un consensus inexistant** — l'honnêteté est l'actif.
- Cohérence avec C2 : la SE de chaque cut doit rester **inférieure à la demi-largeur de la bande** qu'il sépare (même critère que C2 pour les percentiles).

### 7.3 Script de calcul (exécutable, à archiver avec les données)

```python
"""Cuts Bookmark : pages -> Elo -> stats. Entrée : item_map.csv + bookmarks.csv."""
import csv, statistics, math

RP67_OFFSET = 400 * math.log10(0.67 / 0.33)   # = 123.02 Elo (convention §4.3)
T975 = {6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262}  # t(0.975, n-1)

item_map = {int(r["ordre"]): float(r["difficulty_elo"])
            for r in csv.DictReader(open("item_map.csv"))}

cuts = {}  # cut_name -> [theta_j]
for r in csv.DictReader(open("bookmarks_round2.csv")):   # juge_id,cut,page
    b = item_map[int(r["page"])]
    cuts.setdefault(r["cut"], []).append(b + RP67_OFFSET)

for name, thetas in cuts.items():
    n, med = len(thetas), statistics.median(thetas)
    sd = statistics.stdev(thetas); se = sd / math.sqrt(n)
    lo, hi = med - T975[n] * se, med + T975[n] * se
    print(f"{name}: cut={med:.0f} Elo  SD={sd:.0f}  SE={se:.0f}  "
          f"IC95=[{lo:.0f},{hi:.0f}]  n={n}  min-max=[{min(thetas):.0f},{max(thetas):.0f}]")
```

---

## 8. Rapport de défendabilité

Structure calquée sur les trois familles de preuves de Cizek & Bunch (*Standard Setting: A Guide to Establishing and Evaluating Performance Standards on Tests*, Sage, 2007 — chap. 10 pour Bookmark, chap. 3 pour l'évaluation) et Kane (1994) :

1. **Validité procédurale** — la procédure était-elle raisonnable et bien exécutée ?
   - PLD signés par l'école (§3) ; composition et recrutement du panel (§5.1, CV anonymisés) ; matériel (livret gelé + item map archivés) ; déroulé effectif vs script §6 (écarts consignés) ; questionnaire de fin de session (annexe B) : compréhension de la tâche, confiance dans les cuts, absence de pression ressentie.
2. **Validité interne** — les jugements sont-ils cohérents ?
   - Stats §7 par cut et par round ; convergence R1→R2 ; monotonie des cuts ; analyse des zones de désaccord ; sensibilité : cuts recalculés en moyenne vs médiane, et avec RP2/3 (120,4) vs RP67 (123,0) — l'écart doit être ≪ SE, le montrer.
3. **Validité externe** — les cuts sont-ils plausibles hors de la salle ?
   - Données d'impact finales (répartition de la cohorte) commentées par l'école ; croisement avec C2 : les percentiles empiriques des cuts (via l'AnchorTable calibrée) sont-ils compatibles avec les attentes du programme ? ; à terme, concordance avec les classements enseignants (échantillon d'élèves classés à l'aveugle par leurs professeurs vs bandes Atlas).
4. **Limites assumées** — guessing MCQ (§4.4) ; trous de difficulté du livret (§2.3.2) ; taille du panel ; cohorte d'impact (réelle vs synthétique) ; validité locale (école(s) pilote(s), pas le pays) — en cohérence avec C1.6 et l'étage 2 de C5.
5. **Décision et signatures** — cuts adoptés (ou fourchettes), date d'entrée en vigueur dans l'`AnchorTable`, signataires (Atlas + direction pédagogique).

**Claim autorisé post-rapport (politique C5, étage 2)** : « niveaux de maîtrise établis par panel enseignant selon la méthode Bookmark » — jamais « certifié/endossé par MoE/KHDA ».

---

## 9. Articulation avec C2 (calibration) — remplir la même `AnchorTable`

Les deux protocoles alimentent le **même objet de restitution** (`src/restitution/scale.py`), sur deux axes orthogonaux :

| | C2 — Calibration | C3 — Standard-setting (ce document) |
|---|---|---|
| Question | « Où se situe un élève par rapport aux autres / à une référence externe ? » | « Que sait faire un élève, en niveaux communicables ? » |
| Méthode | Equating équipercentile vs référence externe (examens école, TIMSS si licence) | Bookmark, jugement enseignant RP67 |
| Remplit | Le champ `percentile` des `Anchor` | Le champ `level` des `Anchor` (les elo des cuts créent/positionnent les ancres) |
| Nature | Empirique (normatif) | Jugement expert structuré (critérié) |

**Mécanique d'injection.** `AnchorTable.level(elo)` retourne le niveau de la plus haute ancre ≤ elo : il suffit donc de poser une ancre **au Elo de chaque cut**, portant le nom du niveau qui y **commence**, plus une ancre plancher « Beginning » :

```python
# Cuts round 2 (exemple illustratif : 1280 / 1520 / 1840)
CALIBRATED_ANCHORS = AnchorTable([
    Anchor(elo=800,  percentile=pct_c2(800),  level="Beginning"),   # plancher
    Anchor(elo=1280, percentile=pct_c2(1280), level="Developing"),  # cut B/D (C3)
    Anchor(elo=1520, percentile=pct_c2(1520), level="Proficient"),  # cut D/P (C3)
    Anchor(elo=1840, percentile=pct_c2(1840), level="Advanced"),    # cut P/A (C3)
])  # pct_c2 = table équipercentile issue de C2 ; C2 peut ajouter des ancres
    # intermédiaires (percentiles) sans toucher aux niveaux, et réciproquement.
```

**Ordre d'exécution recommandé** : C2 d'abord (ou en parallèle), C3 ensuite — les données d'impact du panel (§6, étape 6) sont plus crédibles sur ancres empiriques. Si C3 passe en premier (contrainte de calendrier école), les impacts s'appuient sur la distribution interne + cohorte synthétique, et le rapport le dit. **Séparation moteur/restitution respectée** : ni C2 ni C3 ne touchent à l'Elo ; ils ne modifient que la table d'ancrage (garantie déjà inscrite dans le code : « changer la table d'ancrage ne touche pas l'Elo »).

---

## 10. Maintenance des cut scores

- Les cuts sont attachés au **snapshot du livret** (date, hash du CSV archivé). Si la distribution des `difficulty_elo` dérive de > 50 Elo en médiane sur les items du livret (recalibration continue du moteur), déclencher une revue : soit re-panel léger (1 round de confirmation), soit translation documentée des cuts.
- Tout nouveau grade / nouvelle matière = nouveau panel (les PLD ne se transfèrent pas).
- Ré-exécution complète recommandée après la première année pleine de données (n_responses ×10 sur la banque → difficultés bien plus stables).

---

## Annexe A — Variante de secours : Angoff modifié

**Quand basculer** : panel < 6 juges ; moins de 30 items éligibles (§2.2) ; ou école exigeant une méthode qu'elle connaît déjà.

**Principe** : pas de livret ordonné. Pour **chaque item** (l'ordre est aléatoire), chaque juge estime la probabilité `p̂_ij` (en pas de 0,05, bornée [0,05 ; 0,95]) que l'élève borderline du niveau visé réponde correctement. Le « score de coupure attendu » du juge est `S_j = Σ_i p̂_ij`.

**Conversion en Elo** (spécifique Atlas — l'Angoff classique s'arrête au score brut) : le cut θ_j est la valeur qui égalise le score attendu du modèle et le jugement du juge, via la courbe caractéristique de test :

```
trouver θ_j tel que  Σ_i 1/(1 + 10^((b_i − θ_j)/400)) = S_j
```

(résolution par bissection sur [0, 4000] — fonction strictement croissante en θ, solution unique ; 20 itérations suffisent pour une précision < 1 Elo). Puis mêmes agrégats et critères que §7 (médiane des θ_j, SD, SE, IC t de Student).

**Déroulé** : identique au script §6 (formation, entraînement, 2 rounds, impact entre rounds), en remplaçant « poser 3 marque-pages » par « remplir la grille de probabilités pour le cut en cours » — donc **3 passes** de grille (une par cut), ce qui limite le nombre d'items jugés à ~25–30 par cut (tirés pour couvrir la plage de difficulté) pour tenir dans la journée.

**Arbitrage** : Angoff est plus tolérant aux petites banques et panels, mais cognitivement plus exigeant (estimer des probabilités item par item) et plus long. Bookmark reste la méthode principale car l'ordre par `difficulty_elo` est l'avantage structurel d'Atlas.

## Annexe B — Formulaires (gabarits à imprimer)

**B.1 Formulaire de marque-pages** (1 par juge et par round) :
`Juge n° ___ · Round ___ · Cut B/D : page ___ · Cut D/P : page ___ · Cut P/A : page ___ · Commentaires (items contestés, hésitations) : ___`

**B.2 Questionnaire de validité procédurale** (fin de session, échelles 1–5 + commentaire libre) :
1. Les définitions des niveaux (PLD) étaient claires. 2. J'ai compris la tâche du marque-page et la règle des 2/3. 3. J'ai eu le temps nécessaire. 4. La discussion m'a apporté des arguments utiles (pas de pression à me conformer). 5. Les données d'impact ont été présentées comme information, pas comme cible. 6. J'ai confiance dans les cuts finaux du groupe. 7. Commentaire libre.

**B.3 Checklist logistique animateur (J−3)** : livrets EN/AR imprimés (1/juge + 2 réserve) · item map confidentielle · mini-livret d'entraînement (5 items hors livret) · formulaires B.1 ×2 rounds · questionnaires B.2 · script §7.3 testé sur données factices · distribution d'ability de la cohorte exportée (impact) · accords de confidentialité · PLD signés affichés dans la salle.

---

**Références** : Lewis, D.M., Mitzel, H.C. & Green, D.R. (1996), *Standard setting: A bookmark approach* ; Mitzel, H.C., Lewis, D.M., Patz, R.J. & Green, D.R. (2001), *The Bookmark procedure*, in Cizek (ed.), *Setting Performance Standards* ; **Cizek, G.J. & Bunch, M.B. (2007), *Standard Setting*, Sage** (référence pivot du rapport §8) ; Kane, M. (1994), *Validating the performance standards associated with passing scores* ; Kolen & Brennan, *Test Equating, Scaling, and Linking* (pour l'articulation C2).
