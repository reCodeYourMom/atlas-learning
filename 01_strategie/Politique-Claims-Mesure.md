# Politique de communication des claims de mesure (C5)

**Version** : 1.0 · **Date** : 2026-07-11 · **Statut** : OPPOSABLE dès adoption — s'applique à tout support externe (decks, one-pagers, site, e-mails commerciaux), à toute surface produit (UI, wording B4/B5, rapports imprimables, exports API) et à tout document remis en due diligence.
**Étage courant** : **0** (ancres expertes, aucune donnée de cohorte réelle — voir registre §6.4).
**Source** : Cadrage-LotC-Mesure-Defendable.md §3/C5 (tableau des 3 étages, développé ici). Contraint le wording B4/B5 (Cadrage-LotB §B4/B5).
**Propriétaire** : fondateur. Toute exception nécessite une décision écrite consignée au registre §6.4.

---

## 1. Objet et principe

Un claim de mesure sur-vendu se retourne en due diligence et devant un Head of Assessment ; un claim honnête et précis est un avantage compétitif (personne d'autre ne le fait sur ce marché). Cette politique définit **ce qu'Atlas a le droit d'affirmer à chaque étage de maturité de sa mesure**, fournit le **langage de remplacement** pour les situations commerciales réelles, et organise **l'audit** des supports et le **passage d'étage**.

**Règle d'or** : chaque affirmation doit être traçable à une preuve existante — et le type de preuve doit être nommé (simulation / jugement d'expert / données pilote / panel). Ce qu'on ne peut pas prouver aujourd'hui se formule comme **engagement daté** (« livrable du pilote »), jamais comme fait acquis.

### 1.1 Les trois familles de claims (à ne jamais confondre)

| Famille | Exemple | Preuve requise | Statut aujourd'hui |
|---|---|---|---|
| **Claims de contenu** (crosswalk curriculaire) | « Nos 32 compétences sont mappées sur CCSS-M / UK NC / MoE » | Crosswalk d'expert versionné, avec type d'alignement + confiance | ✅ Autorisé dès l'étage 0 — **à condition d'être nommé « correspondance documentée par expert », pas « alignement de la mesure »** |
| **Claims de mesure** (échelle, scores, bandes, équivalences) | « Calibré », « niveau G5 », « SAT-ready » | Étude de calibration (C2), standard-setting (C3), analyses (C4) | ❌ Étage 0 : uniquement « échelle interne, ancres expertes, validée par simulation » |
| **Claims d'impact** (efficacité pédagogique, prédiction) | « Améliore les notes de X % », « prédit la réussite au SAT » | RCT / étude longitudinale — **hors périmètre** | ❌ Interdit à tous les étages (invariant) |

La plupart des sur-claims viennent d'un glissement de la famille 1 vers la famille 2 : « mappé sur CCSS » (vrai) devient « aligné sur les standards » (ambigu) devient « calibré sur les standards » (faux). Cette politique verrouille ce glissement.

---

## 2. Étages de maturité — définitions

| Étage | Nom | Condition d'entrée | État de la preuve |
|---|---|---|---|
| **0** | Ancres expertes | — (état actuel) | Modèle documenté (Manuel C1), validation par simulation (`simulate_cohort.py`), ancres de restitution posées par expert (`scale.py`), crosswalk curriculaire d'expert. Aucune donnée de cohorte réelle. |
| **1** | Ancres empiriques | Rapport de calibration C2 **accepté** (critères §6.2) | `AnchorTable` remplacée par des ancres issues des données pilote ; corrélation documentée avec une référence externe ; SE connues. |
| **2** | Cut scores standard-set | Rapport de standard-setting C3 **accepté** (critères §6.2) | Bandes de maîtrise établies par panel enseignant (Bookmark, 2 rounds), stats d'accord publiées. |
| **∞** | Invariants permanents | — | Règles valables à tous les étages, pour toujours (§3.4). |

---

## 3. Tableau des claims autorisés / interdits par étage

### 3.1 Étage 0 — aujourd'hui (ancres expertes)

| ✅ AUTORISÉ | ❌ INTERDIT |
|---|---|
| « Échelle interne, documentée dans un Manuel Technique de Mesure auditable » | « **Calibré** » (sauf au sens strict « les difficultés d'items s'ajustent en continu » — et alors le dire ainsi, jamais le mot seul) |
| « Modèle validé **par simulation** (cohorte synthétique : erreur médiane < 150 Elo, corrélation des difficultés > 0.8) » — l'étiquette « simulation » est **obligatoire** | Présenter les chiffres de validation synthétique comme des résultats terrain |
| « Percentiles / repères de niveau **indicatifs**, ancres expertes, remplacées par des ancres empiriques pendant le pilote » | Toute équivalence de grade/niveau (« votre enfant a un niveau G5 ») présentée comme **mesurée** |
| « Modèle à précédents établis à grande échelle (Math Garden — Klinkenberg et al. 2011 ; Pelánek 2016) ; équivalence mathématique exacte avec Rasch (1 logit ≈ 173.72 Elo) » | « **Aligné sur les standards** MoE/CCSS » au sens de la **mesure/du scoring** (le crosswalk de **contenu** reste autorisé, nommé comme tel) |
| « Correspondance curriculaire **documentée par expert**, versionnée, avec type d'alignement (exact/partiel/enrichissement) et niveau de confiance » (claim de contenu) | « **Validé** » sans complément — toujours dire validé *par quoi* (simulation ≠ terrain) |
| « La calibration sur votre population et vos bandes de maîtrise établies avec vos enseignants sont **des livrables du pilote** » (transforme la faiblesse en offre — D-C1) | Percentile ou score affiché **sans source** (simulation ? expert ? pilote ?) |
| « Le système distingue structurellement mesure directe et inférence : jamais de "maîtrisé" sans réponse directe (`n_direct > 0`) » | « SAT-ready », « prédit les résultats à {examen} », toute projection d'examen présentée comme fiable |
| « Diagnostic causal des lacunes via un graphe de prérequis **construit par expertise pédagogique** (validation empirique prévue au pilote) » | Parité EN/AR présentée comme **démontrée** (l'étude DIF nécessite C-0 + données pilote) — dire « conçu pour la parité, équité vérifiée pendant le pilote » |
| « Bilingue EN/AR par conception : chaque item existe dans les deux langues, validé par linguiste native » (claim de conception) | « Progresse sur le standard {code} » présenté en booléen « atteint/meets {code} » au niveau élève individuel (règle B5 — réservé à l'étage 2) |

### 3.2 Étage 1 — post-calibration (C2 accepté)

Tout l'étage 0, **plus** :

| ✅ AUTORISÉ | ❌ INTERDIT |
|---|---|
| « Bandes ancrées sur données pilote (**n = …, SE = …**) » — les chiffres accompagnent le claim | Généraliser hors population pilote **sans le dire** (« ancré sur données réelles » tout court → non ; « ancré sur données de N écoles UAE, grades 4–5 » → oui) |
| « Corrélation r = … avec {référence externe nommée : examens école / items TIMSS} sur la population pilote » (validité **concurrente**) | Transformer la validité concurrente en claim **prédictif** (« donc prédit les résultats à… ») |
| « Percentiles empiriques de la population pilote » | Étendre les ancres à des grades / langues / curricula non couverts par l'échantillon |
| Si n < cible : publication autorisée uniquement avec la mention « **provisoire**, n = …, SE = … » | Masquer un échantillon insuffisant |

### 3.3 Étage 2 — post-standard-setting (C3 accepté)

Tout l'étage 1, **plus** :

| ✅ AUTORISÉ | ❌ INTERDIT |
|---|---|
| « Niveaux de maîtrise établis par un panel de {k} enseignants selon la méthode Bookmark (2 rounds, accord inter-juges = …) » | « **Certifié / endossé / approuvé par** MoE / KHDA / ADEK » — **jamais, sauf accord écrit** du régulateur (invariant) |
| « Atteint le niveau {Proficient/…} » au niveau élève, **sur les grades et la population couverts par le panel** | Étendre les cut scores à des grades / matières hors panel |
| Rapport de défendabilité citable (méthode, panel, stats d'accord, données d'impact) | Présenter les cut scores comme définitifs si le panel était instable (dans ce cas : publier la fourchette et le dire) |

### 3.4 Invariants permanents (tous étages, pour toujours)

| ✅ TOUJOURS AUTORISÉ | ❌ TOUJOURS INTERDIT |
|---|---|
| « Mesure de compétences, diagnostic causal des lacunes » | « Améliore les résultats de X % » — aucun claim d'efficacité pédagogique chiffrée sans RCT (hors périmètre, Cadrage-LotC §2) |
| « Jamais de maîtrise par inférence seule » (garde-fou structurel du moteur) | « Détecte la dyslexie / la dyscalculie / les troubles de l'apprentissage / le TDAH » — **jamais**. Atlas mesure des compétences, ne pose aucun diagnostic clinique |
| Distinguer explicitement **mesuré** / **estimé** (inféré) / **projeté** dans toute restitution | « Certifié / endossé par un régulateur ou un éditeur de curriculum » sans accord écrit |
| Nommer le type de preuve derrière chaque chiffre | Prédire la réussite individuelle à un examen ou l'admission dans le supérieur |
| Assumer les limites par écrit (section « Limites » du Manuel C1) — c'est un argument, pas un aveu | Utiliser « KHDA/ADEK-aligned » comme si ces inspectorats publiaient un programme (ils n'en publient pas — voir One-Pager §« Précision utile ») |

---

## 4. Formulations de remplacement — les 10 situations commerciales les plus fréquentes

Prêtes à l'emploi à l'étage 0. À chaque passage d'étage, seules les mentions entre ⟨crochets⟩ évoluent (§6.3).

### S1 — RDV admin pédagogique : « C'est aligné sur le MoE / notre programme ? »

**Piège** : répondre « oui » tout court (glissement contenu → mesure).
**FR** : « Oui pour le contenu : les 32 compétences fractions sont mappées sur le curriculum MoE — domaine, grade-band et niveau cognitif — par une correspondance d'expert versionnée et auditable, comme sur CCSS-M et UK NC. Pour le **scoring**, notre échelle est interne aujourd'hui ; son ancrage sur votre population et vos bandes fait partie des livrables du pilote — vous repartez avec une échelle calée sur vos élèves, établie avec vos enseignants. »
**EN**: "Yes on content: all 32 fraction competencies are mapped to the MoE curriculum — domain, grade band and cognitive level — through a versioned, auditable expert crosswalk, same as for CCSS-M and the UK National Curriculum. On **scoring**, our scale is internal today; anchoring it to your student population and setting mastery bands with your teachers are deliverables of the pilot — you end the pilot with a scale calibrated on your own students."

### S2 — Parent : « Il a quel niveau, mon enfant ? Il est au niveau G5 ? »

**Piège** : donner une équivalence de grade comme si elle était mesurée.
**FR** : « Atlas vous montre exactement quelles compétences votre enfant maîtrise, lesquelles sont en cours, et où sont les lacunes — c'est plus précis qu'un niveau global. Les repères de niveau affichés sont indicatifs ⟨à ce stade : établis par expertise, en cours d'ancrage sur données réelles⟩ ; ce qui est solide dès aujourd'hui, c'est la carte compétence par compétence. »
**EN**: "Atlas shows you exactly which competencies your child has mastered, which are in progress, and where the gaps are — that's more precise than a single grade level. The level markers shown are indicative ⟨at this stage: expert-set, being anchored on real cohort data⟩; what is solid today is the competency-by-competency map."

### S3 — Due diligence investisseur : « Votre mesure est validée ? »

**Piège** : « oui » sans qualifier, ou se laisser pousser vers « calibré ».
**FR** : « Validée par simulation, documentée, pas encore calibrée empiriquement — et nous sommes les seuls à vous le dire avec cette précision. Concrètement : un Manuel Technique formalise le modèle avec son équivalence mathématique exacte vers Rasch — auditable par n'importe quel psychométricien dans son propre langage ; la validation synthétique donne une erreur médiane < 150 Elo ; les protocoles de calibration et de standard-setting sont écrits, avec critères d'acceptation chiffrés, et s'exécutent pendant le pilote. Vous pouvez faire relire le manuel par qui vous voulez. »
**EN**: "Validated by simulation, fully documented, not yet empirically calibrated — and we are the only ones in this market who will state it that precisely. Concretely: a Technical Manual formalizes the model with its exact mathematical equivalence to Rasch — auditable by any psychometrician in their own language; synthetic validation shows a median error < 150 Elo; calibration and standard-setting protocols are written, with quantified acceptance criteria, and run during the pilot. Have the manual reviewed by anyone you like."

### S4 — Head of Assessment / psychométricien : « Vous êtes calibrés comment ? C'est de l'IRT ? »

**FR** : « Le moteur temps réel est un Elo par compétence — mathématiquement, c'est un Rasch estimé par approximation stochastique : la conversion est exacte, 1 logit ≈ 173,72 points Elo, testée unitairement. Précédents : Math Garden (Klinkenberg 2011), Pelánek 2016. Les difficultés s'ajustent en continu sur le flux ; la calibration au sens où vous l'entendez — ancrage sur référence externe — est le protocole C2, exécuté pendant le pilote, avec equating équipercentile puis co-calibration Rasch offline. Le manuel technique détaille tout, limites comprises. »
**EN**: "The real-time engine is a per-competency Elo — mathematically a Rasch model estimated by stochastic approximation: the conversion is exact, 1 logit ≈ 173.72 Elo points, unit-tested. Precedents: Math Garden (Klinkenberg 2011), Pelánek 2016. Item difficulties adjust continuously on the response stream; calibration in your sense — anchoring to an external reference — is our C2 protocol, executed during the pilot: equipercentile equating first, offline Rasch co-calibration where anchor items allow. The technical manual covers all of it, stated limitations included."

### S5 — Directeur d'école : « Vos scores prédisent les résultats au SAT / IGCSE ? »

**Piège** : la prédiction d'examen — interdite à tous les étages tant qu'aucune donnée longitudinale n'existe.
**FR** : « Non, et personne ne peut l'affirmer honnêtement sans données longitudinales. Ce qu'Atlas fait : mesurer en continu les fondations — compétence par compétence — dont ces examens dépendent, et détecter les lacunes des années avant qu'elles ne coûtent des points. ⟨Étage 1 : et notre échelle est corrélée à r = … avec {référence} sur la population pilote.⟩ »
**EN**: "No — and nobody can claim that honestly without longitudinal data. What Atlas does: continuously measure the foundations — competency by competency — that those exams build on, and surface gaps years before they cost points. ⟨Tier 1: and our scale correlates at r = … with {reference} on the pilot population.⟩"

### S6 — Inspection / préparation KHDA-ADEK : « Ça peut servir de preuve d'outcomes ? »

**Piège** : « preuve d'outcomes » tout court (sur-claim à l'étage 0).
**FR** : « Atlas vous donne un suivi continu, granulaire et traçable au standard de la progression de vos élèves sur votre programme — chaque lacune et chaque progrès porte son code (CCSS, UK NC, domaine MoE). C'est exactement le type d'évidence interne que les inspecteurs demandent sur les student outcomes. Précision qui joue pour vous : KHDA et ADEK inspectent la délivrance de votre programme — le rapport Atlas parle donc le langage de **votre** curriculum, pas d'un référentiel maison. »
**EN**: "Atlas gives you continuous, granular, standard-traceable tracking of your students' progression on your own curriculum — every gap and every gain carries its code (CCSS, UK NC, MoE domain). That is exactly the kind of internal evidence inspectors ask for on student outcomes. One precision that works in your favour: KHDA and ADEK inspect how well you deliver your chosen curriculum — so the Atlas report speaks the language of **your** curriculum, not a proprietary scale."

### S7 — Enseignant : « Donc l'élève a atteint le standard 4.NF.A.1 ? »

**Piège** : le booléen « meets {code} » individuel — réservé à l'étage 2 (règle B5).
**FR** : « Il maîtrise k des n compétences alignées sur 4.NF.A.1 — voici lesquelles, et voici celle qui bloque. "Atteint le standard" est une décision de seuil : elle sera posée avec un panel d'enseignants — dont les vôtres, pendant le pilote. En attendant, vous avez mieux qu'un oui/non : le détail. »
**EN**: "He has mastered k of the n competencies aligned to 4.NF.A.1 — here's which ones, and here's the one blocking him. 'Meets the standard' is a threshold decision: it will be set with a teacher panel — including your teachers, during the pilot. Meanwhile you have something better than a yes/no: the detail."

### S8 — École / parent : « Et en arabe, c'est aussi fiable qu'en anglais ? »

**Piège** : affirmer une équité démontrée avant l'étude DIF (C4, qui exige C-0).
**FR** : « Chaque item existe en anglais et en arabe, validé par une linguiste native — c'est la parité de conception. Et nous sommes équipés pour la **vérifier**, pas seulement l'affirmer : le système journalise la langue de chaque réponse, et l'analyse d'équité linguistique item par item (DIF) fait partie du plan d'analyses du pilote. Un item qui se comporte différemment en arabe est détecté, revu ou retiré. »
**EN**: "Every item exists in English and in Arabic, validated by a native linguist — that's parity by design. And we are instrumented to **verify** it, not just claim it: the system logs the language of every response, and item-by-item linguistic fairness analysis (DIF) is part of the pilot analysis plan. An item behaving differently in Arabic gets flagged, reviewed or retired."

### S9 — Prospect : « Ça améliore les notes de combien ? »

**Piège** : l'efficacité chiffrée — invariant, interdit pour toujours (pas de RCT).
**FR** : « Aucun chiffre honnête n'existe sans étude contrôlée, et ceux qui vous en donnent un n'en ont pas fait. Ce qu'on garantit : vos enseignants voient chaque lacune de chaque élève, avec sa cause, au moment où elle est encore rattrapable — au lieu de la découvrir à l'examen. L'effet sur les notes dépend de ce que vous faites de cette visibilité ; le pilote inclut les métriques d'usage pour l'objectiver chez vous. »
**EN**: "No honest number exists without a controlled study — and vendors who quote one haven't run one. What we guarantee: your teachers see every gap of every student, with its root cause, while it can still be fixed — instead of discovering it at exam time. The effect on grades depends on what you do with that visibility; the pilot includes usage metrics to measure it in your school."

### S10 — Parent inquiet : « Mon enfant a peut-être un trouble (dyslexie, dyscalculie) — Atlas le détecte ? »

**Piège** : tout vocabulaire clinique — invariant, interdit pour toujours.
**FR** : « Non — Atlas mesure des compétences scolaires, il ne pose aucun diagnostic médical ou clinique, et aucun outil de ce type ne devrait prétendre le faire. Ce qu'Atlas vous donne : une image précise et objective de ce que votre enfant maîtrise et de ce qui bloque — un support factuel utile si vous consultez un professionnel qualifié, qui reste le seul à pouvoir diagnostiquer. »
**EN**: "No — Atlas measures academic competencies; it does not make any medical or clinical diagnosis, and no tool of this kind should claim to. What Atlas gives you: a precise, objective picture of what your child has mastered and what's blocking progress — factual input that can help if you consult a qualified professional, who remains the only one able to diagnose."

---

## 5. Checklist d'audit d'un deck / écran / rapport (10 points)

À passer sur **tout** support avant diffusion externe et à chaque passage d'étage. Un point ❌ = correction avant diffusion. Auditeur : fondateur (ou C6 pour les supports de due diligence). Consigner l'audit (date, support, verdict) au registre §6.4.

| # | Point de contrôle | Test concret |
|---|---|---|
| 1 | **Mots sous licence** : « calibré », « validé », « aligné », « certifié », « endossé », « approuvé », « prouvé », « prédit », « garantit » | Rechercher chaque occurrence (FR + EN : *calibrated, validated, aligned, certified, endorsed, proven, predicts*). Chacune est-elle autorisée à l'étage courant, avec son complément (validé *par simulation*, aligné *en contenu, par crosswalk d'expert*) ? |
| 2 | **Équivalences de niveau** | Toute mention de grade/niveau/percentile porte-t-elle « indicatif » + la source (⟨expert / pilote n = …⟩) ? |
| 3 | **Étiquette simulation** | Tout chiffre issu de `simulate_cohort.py` (erreur < 150 Elo, corrélation > 0.8…) est-il explicitement étiqueté « simulation / cohorte synthétique » ? |
| 4 | **Booléen standard** | Aucun « atteint / meets {code} » au niveau élève individuel (avant étage 2) ? Formulation conforme B5 : « k/n compétences alignées sur {code} maîtrisées » ? |
| 5 | **Contenu vs mesure** | Les claims de crosswalk (contenu) sont-ils distinguables des claims de scoring (mesure) ? Le mot « alignement » seul est-il levé d'ambiguïté ? |
| 6 | **Mesuré / estimé / projeté** | Toute restitution distingue-t-elle ce qui est mesuré directement, inféré (propagation) et projeté ? Aucune maîtrise affichée sans mesure directe ? |
| 7 | **Efficacité et prédiction** | Zéro claim « améliore de X % », zéro prédiction d'examen ou d'admission ? |
| 8 | **Vocabulaire clinique** | Zéro occurrence de dyslexie / dyscalculie / trouble / TDAH / diagnostic (au sens médical) ? |
| 9 | **Parité EN/AR** | Le bilinguisme est-il formulé comme parité **de conception** (+ vérification DIF prévue/faite), jamais comme équité démontrée avant les résultats C4 ? |
| 10 | **Traçabilité** | Le support mentionne-t-il sa date et est-il rattachable à l'étage courant (registre §6.4) ? Les régulateurs (KHDA/ADEK) sont-ils traités en inspectorats, pas en éditeurs de programme ? |

---

## 6. Procédure de passage d'étage

### 6.1 Qui décide

- **Décideur** : le fondateur, par décision écrite consignée au registre §6.4.
- **Avis externe fortement recommandé** (quasi obligatoire pour les supports de due diligence) : le psychométricien C6 relit le dossier de preuve avant les passages 0→1 et 1→2. Coût marginal, crédibilité maximale (« reviewed by… »).
- Personne d'autre (commercial, partenaire, école) ne peut faire monter un claim d'étage — y compris oralement en RDV.

### 6.2 Sur quelle preuve

**Passage 0 → 1** — dossier requis, tous éléments réunis :
1. C-0 vérifié en production (`Response.language` alimenté sur 100 % des réponses du pilote) ;
2. Rapport de calibration C2 avec ses critères d'acceptation atteints : SE de chaque cut < demi-largeur de la bande qu'il sépare ; corrélation Atlas/référence ≥ 0.6 ; échantillon ≥ 50–100 élèves **par grade** (sinon : étage 1 possible uniquement avec mention « provisoire, n = …, SE = … » sur chaque claim) ;
3. `AnchorTable` empirique déployée en production (les claims doivent décrire ce que l'utilisateur voit) ;
4. Périmètre écrit du passage : grades, écoles, langues couverts — les claims d'étage 1 ne valent **que** sur ce périmètre.

**Passage 1 → 2** — dossier requis :
1. Rapport de standard-setting C3 : méthode Bookmark, panel 6–10 enseignants, 2 rounds avec données d'impact, stats d'accord inter-juges publiées ;
2. Cut scores déployés (bandes visibles en production = bandes standard-set) ;
3. Si le panel est instable : pas de passage plein — publication de la fourchette avec mention explicite, claims « atteint le niveau X » suspendus.

**Rétrogradation** : si une preuve est invalidée (échantillon disqualifié, erreur de calcul, révision du crosswalk, retrait d'une référence), retour immédiat à l'étage inférieur ; correction de tous les supports actifs sous **10 jours ouvrés** ; entrée au registre.

### 6.3 Mécanique de mise à jour (à chaque passage)

1. Entrée au registre §6.4 (date, étage, dossier de preuve, périmètre, signataire).
2. Mise à jour de ce document (bandeau « Étage courant » + mentions ⟨crochets⟩ du §4).
3. Ré-audit checklist §5 de **tous** les supports actifs : decks, One-Pager, site, écrans B4/B5, rapport imprimable, templates e-mail.
4. Mise à jour du wording UI (tables B4/B5) — EN **et** AR.
5. Information de toute personne qui pitche (le langage autorisé change).

### 6.4 Registre des décisions d'étage et des audits

| Date | Objet | Étage | Preuve / support | Décision | Signataire |
|---|---|---|---|---|---|
| 2026-07-11 | Adoption de la politique | **0** | Cadrage-LotC §3/C5 | Politique v1.0 adoptée ; audit initial §7 réalisé | Nassim |
| 2026-07-12 | Contre-vérification de l'audit §7 (citations One-Pager + PRD contrôlées contre les sources) | **0** | One-Pager-Alignement-Curriculaire.md ; PRD-Atlas-Learning.md | Citations OP-1→OP-6 et PRD-1→PRD-7 confirmées exactes ; ajout du point de vigilance PRD-8 (motif « preuve/prouver » hors TL;DR) | Nassim |
| | | | | | |

---

## 7. Audit du matériel existant (étage 0) — 2026-07-11

Documents audités : `03_referentiel/One-Pager-Alignement-Curriculaire.md` (support **externe** — priorité haute) et `01_strategie/PRD-Atlas-Learning.md` (document **interne**, mais son langage alimente les pitchs — corrections requises avant tout copier-coller vers un deck).

### 7.1 One-Pager-Alignement-Curriculaire.md

Verdict global : document **largement conforme** — la section « Ce que nous disons — et ce que nous ne disons pas » et la précision KHDA/ADEK ≠ programme sont exemplaires et anticipent cette politique. **4 non-conformités** et 2 points de vigilance :

| # | Localisation | Citation | Problème (règle) | Correction proposée | Gravité |
|---|---|---|---|---|---|
| OP-1 | §« Ce que cet alignement vous donne » (enseignant) | « Élève faible sur **4.NF.A.2 / comparaison de fractions** » | Formule la lacune **au niveau du standard**, comme si la mesure était posée sur le code — glissement contenu→mesure ; contredit la règle B5 (pas d'affirmation individuelle au grain standard avant l'étage 2) | « Lacune sur *comparer des fractions* — compétence **alignée sur** 4.NF.A.2 » | Moyenne |
| OP-2 | §« Ce que cet alignement vous donne » (inspection) | « une **preuve** continue, granulaire, traçable au standard, des *student outcomes* exigés » | « Preuve des outcomes » = claim de mesure/impact à l'étage 0 (échelle non ancrée) ; §3.1 | « un **suivi** continu, granulaire, traçable au standard, de la progression des élèves — le type d'évidence interne attendu en inspection sur les *student outcomes* » | **Haute** (support remis en RDV) |
| OP-3 | §« Pourquoi ce n'est pas du maison » | « ce qui rend la mesure plus **précise** et la lacune plus actionnable » | « Plus précise » = claim de qualité de mesure sans preuve empirique. La **granularité** est un fait structurel, la **précision** se démontre (SE, fidélité — C4) | « ce qui rend la mesure plus **granulaire** et la lacune plus actionnable » | Moyenne |
| OP-4 | §« Précision utile », dernier ¶ | « Le niveau cognitif que nous mesurons **correspond directement** à la taxonomie cognitive du MoE. » | Équivalence présentée comme établie + « que nous mesurons » suggère une mesure validée du niveau cognitif | « Chaque item Atlas est étiqueté par niveau cognitif selon une **correspondance d'expert** avec la taxonomie du MoE (Knowing / Applying / Reasoning). » | Moyenne |
| OP-5 | Tableau des programmes | « Couverture : 32/32 compétences » (×3) | Vigilance, pas une violation : « couverture » sans rappel du type d'alignement peut se lire comme alignement intégral exact | Ajouter une note de tableau : « couverture = correspondance documentée (exact / partiel / enrichissement) — détail dans le Crosswalk » | Basse |
| OP-6 | §« Ce que cet alignement vous donne » (coordinateur) | « rapport de couverture par programme […] **prêt pour l'inspection** » | Vigilance : acceptable en claim de contenu, à condition que le rapport lui-même passe la checklist §5 (points 2, 4, 6) | Conserver ; auditer le template du rapport avant première remise | Basse |

### 7.2 PRD-Atlas-Learning.md

Verdict global : le PRD contient le **cœur du sur-claim à surveiller** — l'échelle « ancrée trajectoire-supérieur » présentée au présent, et la promesse de « preuve » de trajectoire vers l'université d'élite. **7 non-conformités** :

| # | Localisation | Citation | Problème (règle) | Correction proposée | Gravité |
|---|---|---|---|---|---|
| PRD-1 | TL;DR | « restitue le résultat sur une échelle **ancrée sur les attentes de l'enseignement supérieur** » | « Ancrée » au présent = ancrage empirique inexistant (ancres expertes, `scale.py`) ; §3.1 | « restitue le résultat sur une échelle **conçue pour être ancrée** sur des repères externes de trajectoire supérieur — ancres expertes en v1, calibration empirique livrée pendant le pilote » | **Haute** (le TL;DR se recopie tel quel dans les decks) |
| PRD-2 | TL;DR | « pour **prouver** aux parents que leur enfant est **sur la trajectoire vers l'université d'élite** » | Double violation : « prouver » (claim de preuve à l'étage 0) + prédiction de trajectoire individuelle (invariant §3.4 — jamais autorisé) | « pour donner aux parents une lecture continue et objective de la progression de leur enfant, située par rapport à des repères externes exigeants » | **Haute** (invariant) |
| PRD-3 | §Solution, vue d'ensemble | « échelle **ancrée trajectoire-supérieur** (percentile + **équivalent niveau** + projection) » | « Ancrée » au présent + « équivalent niveau » sans mention indicative (interdit étage 0) | « échelle de restitution (percentile **indicatif** + repère de niveau **indicatif** + projection **modélisée, non prédictive**) — ancres expertes v1, ancrage empirique = C2 » | **Haute** |
| PRD-4 | §Les trois couches (1) | « **S'auto-calibre** sur le trafic réel » | Emploi de « calibre » pour l'ajustement en ligne — entretient la confusion avec la calibration psychométrique (ancrage externe) ; mot sous licence §5.1 | « **Ajuste en continu** ses estimations de difficulté sur le trafic réel (estimation en ligne) ; la **calibration** au sens psychométrique — ancrage externe — relève de l'étude C2 » | Moyenne |
| PRD-5 | §Les trois couches (3) | « bande type « **SAT-ready** » » | Prédiction d'examen — interdite à l'étage 0, et de portée invariant tant qu'aucune donnée longitudinale n'existe (§3.1, §3.4) | Marquer comme concept cible non publiable : « bande de restitution cible (type readiness) — **conditionnée à l'ancrage empirique C2 ; jamais en surface client en v1** » | **Haute** |
| PRD-6 | §User journeys, Parent (2) | « Voit où l'enfant se situe **vs attentes du supérieur** » | Positionnement vs supérieur affiché comme fait, sans statut indicatif | « Voit où l'enfant se situe par rapport à des repères **indicatifs** (ancres expertes v1, empiriques post-pilote) et les lacunes en cours de comblement » | Moyenne |
| PRD-7 | §Risques, mitigation ligne 3 | « Échelle de restitution **ancrée sur repères externes** ; transparence… » | Mitigation écrite au présent alors que c'est un état cible — le PRD se contredit avec l'état réel du code (`scale.py` : « à remplacer par cohorte réelle ») | « Échelle **à ancrer** sur repères externes (protocole C2, pendant le pilote) ; en attendant : transparence explicite sur les ancres expertes » | Basse |
| PRD-8 | §Problème (« système de **preuve** continue »), §Personas admin (« **prouver** les outcomes »), §User journeys admin (5) (« via **preuve** continue ») | Motif « preuve / prouver » répété hors TL;DR | Vigilance, pas une violation en soi : acceptable en cadrage du problème marché (c'est le besoin du client qui est décrit), mais tout copier-coller vers un pitch reproduit le sur-claim PRD-2 | Dans toute reprise externe : « **suivi / évidence** continue » et « **objectiver** les outcomes » ; réserver « preuve » aux claims de contenu (crosswalk versionné) | Basse |

### 7.3 Synthèse de l'audit

- **11 non-conformités** (4 One-Pager, 7 PRD) dont **5 de gravité haute** — toutes concentrées sur deux motifs : (a) l'ancrage/la calibration présentés au présent, (b) la promesse de trajectoire/preuve vers le supérieur (dont 1 violation d'invariant permanent : PRD-2). S'y ajoutent **3 points de vigilance** (OP-5, OP-6, PRD-8).
- **Aucune violation** des invariants cliniques (dyslexie/troubles) ni de certification régulateur — les deux documents sont sains sur ces points.
- **Action** : appliquer les corrections OP-1 à OP-4 et PRD-1 à PRD-7 avant toute réutilisation externe de ces textes ; OP-5/OP-6/PRD-8 au fil de l'eau. Consigner l'application au registre §6.4.
- **Vérification 2026-07-12** : chaque citation de cet audit a été recontrôlée mot à mot contre les documents sources — toutes exactes ; PRD-8 ajouté à cette occasion.

---

*Politique C5 — v1.0. Toute évolution du tableau §3 ou des critères §6.2 constitue une nouvelle version, consignée au registre.*
