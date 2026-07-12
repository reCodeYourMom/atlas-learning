# Feuille de décision fondateur — Lots A, B, C

**Lot 4 du dossier de revue** · **Date** : 2026-07-12 · **Statut** : PROPOSITION — à valider
**Source** : §7 des trois cadrages (`01_strategie/Cadrage-LotA-Extension-Contenu.md`, `Cadrage-LotB-Curriculum-Produit.md`, `Cadrage-LotC-Mesure-Defendable.md`)
**Destinataire** : Nassim · **Budget cible : 30 minutes**

> Les 12 décisions ci-dessous sont **déjà recommandées** dans leurs cadrages respectifs. Ce document ne les rouvre pas : il les rassemble, dit **ce qui casse si vous ne tranchez pas**, et vous fait signer. **Deux d'entre elles sont déjà actées de fait** (§1) — un trait de plume suffit.

---

## ✅ RÉSULTAT — décisions prises par Nassim le 2026-07-12

| # | Décision | Choix retenu | vs reco |
|---|---|---|---|
| **D-A1** | Périmètre d'extension | **Décimaux G4–G5 d'abord** | = reco |
| **D-A2** | Experts externes | **Didacticien SEUL** (pas d'enseignant EAU) | ⚠️ diverge |
| **D-A3** | G6–G8 | **Chantier distinct** (nouveaux types d'items) | = reco |
| **D-B1** | Framework par défaut | **ATLAS neutre**, choix explicite à l'onboarding | = reco |
| **D-B2** | Codes côté parent | **Non en v1** | = reco |
| **D-B3** | Bi-curriculum | **Un framework par tenant** en v1 | = reco |
| **D-B4** | DataModel §7 | **Amendé** (alignment_type + confidence) — déjà appliqué, confirmé par défaut | = reco |
| **D-B5** | Couverture programme au rapport | **Oui dès la v1** (findings CRIT-1/MAJ-1 déjà corrigés) | = reco |
| **D-C1** | Calibration | **Faite en INTERNE** (pas vendue comme livrable pilote) | ⚠️ diverge |
| **D-C2** | Elo ou IRT | **Elo en prod, IRT offline** | = reco |
| **D-C3** | Référence externe | **Examens internes + ancrage TIMSS** (vérifier licence IEA) | = reco |
| **D-C4** | Revue psychométricien externe | **NON** (pas de revue externe avant lancement) | ⚠️ diverge |

**Conséquences des 3 divergences (assumées) :**
- **D-C1 interne + D-C4 non** → l'étude de calibration n'a plus AUCUN filet externe (ni engagement/revenu école, ni relecture métier). La qualité du protocole interne (C2/C3) devient le seul garde-fou ; les claims restent à l'**étage 0/1** de `Politique-Claims-Mesure.md` (« échelle interne », jamais « validée par un tiers »).
- **D-A2 didacticien seul** → la double lecture des décimaux (`Double-Lecture-Decimaux.md`) devient une **lecture experte simple** (doc à adapter) ; la confiance MoE reste **M** faute de canal enseignant EAU vers le document d'outcomes du ministère (livrable B7 sans porteur).
- **D-C3** → à inscrire au contrat de pilote : accès aux **examens internes** de l'école + calendrier ; et **vérifier la licence IEA/TIMSS dès maintenant**, pas au moment de la collecte.

*Enregistré par assistant le 2026-07-12 sur décisions directes de Nassim. Les checkboxes §1–§3 ci-dessous sont conservées comme trace du raisonnement ; ce bloc fait foi.*

---

## 0. Mode d'emploi

- **Ordre de lecture** : §1 (les 2 confirmations d'un trait) → §2 (les 4 décisions bloquantes) → §3 (les 6 décisions non bloquantes).
- **Bloquant** = un livrable en cours **attend** cette décision. **Non bloquant** = la reco s'applique par défaut si vous ne dites rien, mais l'écrire évite de la re-débattre dans 3 mois.
- Une décision non tranchée **n'est pas neutre** : elle est tranchée par défaut, par l'inertie, généralement dans le mauvais sens. La colonne « si on ne tranche pas » dit lequel.

---

## 1. Déjà actées de fait — à confirmer d'un trait ✍️

### D-A1 · Premier périmètre d'extension : **décimaux (G4–G5) d'abord**

| | |
|---|---|
| **Enjeu** | Aller *plus profond* dans le primaire (décimaux, opérations, mesure) ou *plus haut* (G6–G8) ? |
| **Recommandation du cadrage** | **Profondeur en primaire. Décimaux (G4–G5) en premier domaine.** Adjacence cognitive maximale avec les fractions, génération déterministe tractable, fréquence d'évaluation élevée, extension propre du crosswalk. |
| **État réel** | ✅ **Déjà fait.** `referentiel_decimals_draft.json` existe (14 nœuds, 26 arêtes), `Misconceptions-Decimaux.md` et `Spec-Generateurs-Decimaux.md` sont écrits, le plan de production AR est rédigé. **Le Lot 3 de ce dossier prépare la double lecture.** |
| **Si on ne tranche pas** | Rien ne casse tout de suite — mais la double lecture (Lot 3) mobilise 2 experts × 2 h **sur un domaine dont le principe n'est pas signé**. Vous payez une revue pour un choix implicite. |
| **Mon avis** | ✅ Confirmez. Le seul contre-argument (« un pilote collège nous demandera G6–G8 ») est traité par D-A3 : G6–G8 = **nouveaux types d'items**, donc un chantier séparé de toute façon. |

> ☐ **VALIDÉ** — décimaux d'abord · ☐ **AUTRE CHOIX** : ____________________________________

---

### D-B4 · Amendement du DataModel §7 : `alignment_strength` → `alignment_type` + `confidence`

| | |
|---|---|
| **Enjeu** | Le §7 du DataModel prévoyait une **force scalaire** d'alignement. Le crosswalk réel produit un **type** (EXACT/PARTIAL/BROADER/PREREQ/ENRICH) + une **confiance** (H/M). Amender le contrat écrit, ou laisser le doc diverger du code ? |
| **Recommandation du cadrage** | **Oui, amender §7.** La force scalaire était un placeholder ; la sémantique type+confiance pilote directement le wording produit. |
| **État réel** | ✅ **Déjà fait, des deux côtés.** Le code (`src/models/curriculum.py`, migration `0019`) porte `alignment_type` + `confidence`. Le doc **est amendé** : `DataModel-KnowledgeGraph.md` §7 (ligne 292) dit *« Implémenté v1 (Lot B, 2026-07), amendé par la décision D-B4 »*. |
| **Si on ne tranche pas** | Rien. La décision est appliquée. Mais elle n'est **signée nulle part** — et c'est précisément le genre d'écart doc/code qui, non tracé, refait surface en due diligence technique. |
| **Mon avis** | ✅ Confirmez. C'est une formalité, mais la discipline « le doc écrit reste la référence » est ce qui rend le projet auditable sans vous. |

> ☐ **VALIDÉ** — §7 amendé · ☐ **AUTRE CHOIX** : ____________________________________

---

## 2. Décisions bloquantes — un livrable attend 🔴

### D-C1 · L'étude de calibration est-elle un **livrable vendu** du pilote ?

| | |
|---|---|
| **Enjeu** | Le point faible d'Atlas est l'absence d'ancrage externe de l'échelle. On le cache, ou on le vend ? |
| **Recommandation du cadrage** | **Oui, le vendre.** *« Vous recevez, en fin de pilote, la calibration de l'échelle sur votre population et vos bandes de maîtrise établies avec vos enseignants »* — ça transforme le point faible en livrable payé, ça engage l'école (panel), et ça produit l'actif réutilisable pour toutes les ventes suivantes. |
| **Si on ne tranche pas** | 🔴 **Bloquant.** La collecte pilote est une **fenêtre unique** : si le protocole de calibration (panel enseignants, examens de référence, ancres) n'est pas dans le contrat de pilote **avant** le démarrage, les données nécessaires ne seront pas collectées et **ne pourront pas l'être après**. Vous perdez l'actif défendable pour un an. |
| **Mon avis** | ✅ Confirmez, et **vite** — c'est la décision la plus urgente des 12, parce qu'elle a une **date limite** (la signature du pilote), pas seulement un coût. Le risque à surveiller : vendre une calibration crée une **obligation de résultat**. Le contrat doit dire « étude de calibration sur votre population », pas « échelle calibrée » — cf. `Politique-Claims-Mesure.md`. |

> ☐ **VALIDÉ** — vendu comme livrable de pilote · ☐ **AUTRE CHOIX** : ____________________________

---

### D-C4 · Revue externe par un psychométricien (C6) : oui ou non ?

| | |
|---|---|
| **Enjeu** | 2–3 jours d'un psychométricien externe pour relire le protocole avant le lancement de l'étude. |
| **Recommandation du cadrage** | **Oui, avant le lancement de l'étude.** *« La différence entre "ils affirment" et "c'est relu par un tiers du métier" en due diligence. »* C'est aussi une assurance qualité sur C2/C3 avant de brûler l'unique fenêtre de collecte. |
| **Si on ne tranche pas** | 🔴 **Bloquant, par la même date limite que D-C1.** Une revue externe **après** la collecte ne sert à rien : elle constatera les erreurs de protocole au lieu de les éviter. Et un défaut de protocole = une fenêtre pilote perdue. |
| **Mon avis** | ✅ Confirmez. Le coût (2–3 j) est dérisoire face à ce qu'il assure : c'est une **assurance sur la fenêtre unique**, pas une dépense de crédibilité. Séquence : D-C1 (on vend l'étude) → **D-C4 (on la fait relire) → on signe le pilote**. Dans cet ordre. |

> ☐ **VALIDÉ** — revue externe avant lancement · ☐ **AUTRE CHOIX** : ____________________________

---

### D-C3 · Quelle référence externe pour l'étude de validité (C2) ?

| | |
|---|---|
| **Enjeu** | Contre quoi corrèle-t-on les scores Atlas pour prouver qu'ils mesurent quelque chose de réel ? |
| **Recommandation du cadrage** | **Examens internes des écoles pilotes en principal** ; items TIMSS libérés en ancres **si la licence IEA le permet**. L'examen blanc MoE serait idéal mais son accès est incertain — **ne pas conditionner l'étude à son obtention**. |
| **Si on ne tranche pas** | 🔴 **Bloquant.** La référence externe détermine ce qu'il faut **demander à l'école dans le contrat de pilote** (accès aux notes internes, calendrier des examens). Décidé après, c'est trop tard : l'école n'aura pas prévu de vous donner ses résultats. |
| **Mon avis** | ✅ Confirmez, avec une réserve. « Examens internes des écoles pilotes » est un choix pragmatique, mais **leur fiabilité est inconnue** : un examen maison mal construit corrèle mal avec *tout*, y compris avec la vérité. Si la corrélation est faible, vous ne saurez pas si c'est Atlas ou l'examen. **Mitigation** : demander **deux** références (examen interne + un ancrage TIMSS même partiel) — sinon vous n'avez aucun moyen de discriminer. **Vérifier la licence IEA dès maintenant, pas au moment de la collecte.** |

> ☐ **VALIDÉ** — examens internes en principal (+ TIMSS si licence) · ☐ **AUTRE CHOIX** : ______________

---

### D-A2 · Recours à des experts externes : lesquels, à quelles étapes ?

| | |
|---|---|
| **Enjeu** | Payer des experts (didacticien, enseignant EAU) et sur quoi précisément. |
| **Recommandation du cadrage** | **Oui, deux profils, sur des étapes précises — pas une revue générale.** Didacticien maths sur A1.8 + A3 + A4 (~3–4 j). Enseignant primaire EAU (idéalement école pilote) sur la 2ᵉ lecture du référentiel + contextes d'items (~2 j). *« C'est la revue référentiel + misconceptions qui fabrique la crédibilité de l'actif défendable ; la revue d'items unitaires peut rester interne. »* |
| **Si on ne tranche pas** | 🔴 **Bloquant immédiatement.** Le **Lot 3 de ce dossier** (`Double-Lecture-Decimaux.md`) est écrit **pour ces deux profils**. Sans eux, le gate A1.8 n'est pas franchissable, les 14 nœuds décimaux restent en `draft`, et **la production des ~140 items ne démarre pas**. C'est la décision qui débloque la suite du Lot A. |
| **Mon avis** | ✅ Confirmez. Un point d'attention : l'**enseignant primaire EAU** est aussi votre meilleur canal vers le **document d'outcomes par grade du MoE** (livrable B7, qui fait passer la confiance MoE de M à H). **Recrutez-le dans une école pilote et demandez-lui le document dès le premier échange** — c'est deux livrables pour un contact. |

> ☐ **VALIDÉ** — didacticien (3–4 j) + enseignant EAU (2 j), sur étapes ciblées
> ☐ **AUTRE CHOIX** : ______________________________________________________________
> **Noms pressentis** — didacticien : ____________________ · enseignant EAU : ____________________

---

## 3. Décisions non bloquantes — la reco s'applique par défaut

*Elles ne bloquent aucun livrable. Les signer coûte 5 minutes et évite de les re-débattre.*

### D-A3 · G6–G8 : mêmes mécaniques ou nouveaux types d'items ?

| | |
|---|---|
| **Recommandation** | **Trancher que G6–G8 = nouveaux types d'items** (saisie numérique libre, multi-étapes) → **chantier distinct**, hors de la première extension. Le MVP est bâti sur MCQ / numérique simple / réponse courte ; la proportionnalité et le pré-algèbre exigent de la saisie structurée et du scoring multi-étapes, ce qui touche le moteur d'items et la calibration. |
| **Si on ne tranche pas** | Le premier prospect collège vous fait dire « oui, on peut » en RDV. Vous découvrez ensuite que ça touche le moteur. **C'est la décision qui vous protège de vous-même en RDV.** |
| **Mon avis** | ✅ Confirmez. Et **écrivez la phrase de RDV** : *« Atlas mesure le primaire. Le collège demande d'autres formats d'items — c'est une roadmap, pas une case à cocher. »* |

> ☐ **VALIDÉ** — G6–G8 = chantier distinct · ☐ **AUTRE CHOIX** : ____________________________

---

### D-B1 · Framework curriculaire par défaut par type d'école ?

| | |
|---|---|
| **Recommandation** | **Aucun défaut « intelligent » — `ATLAS` (neutre) par défaut, choix explicite à l'onboarding.** Le mix EAU (privées US/UK/IB, publiques MoE) rend tout défaut faux une fois sur deux ; le choix explicite est un moment commercial utile (« quel est votre programme ? ») et évite un étiquetage erroné silencieux. |
| **État réel** | ✅ Déjà câblé : `Organization.curriculum_view` a pour défaut `ATLAS` (python **et** serveur) — zéro régression pour les tenants existants. |
| **Si on ne tranche pas** | Rien ne casse : le code fait déjà `ATLAS`. Le risque est **commercial** : quelqu'un « améliore » l'onboarding en devinant le framework depuis le nom de l'école, et une école IB se retrouve étiquetée CCSS. |
| **Mon avis** | ✅ Confirmez. Le défaut neutre est aussi ce qui rend la démo honnête : on **montre** le passage de ATLAS à CCSS, au lieu de prétendre que « c'était déjà aligné ». |

> ☐ **VALIDÉ** — `ATLAS` par défaut, choix explicite · ☐ **AUTRE CHOIX** : ____________________________

---

### D-B2 · Vue parent : codes de standards ou pas ?

| | |
|---|---|
| **Recommandation** | **Pas en v1.** La page parent est volontairement apaisée (pas de percentiles de pairs, pas de chaînes causales) ; des codes CCSS n'y apportent rien et ouvrent des questions de sur-interprétation. Réévaluer si les écoles le demandent. |
| **État réel** | ✅ Déjà câblé : `GET /students/{id}/trajectory` n'attache aucun `standard`. |
| **Si on ne tranche pas** | Rien. Mais la première école qui demande « les parents peuvent-ils voir les standards ? » rouvrira le débat sans trace de pourquoi c'était non. |
| **Mon avis** | ✅ Confirmez. Un parent à qui on montre « covers part of 4.NF.A.1 » entend « mon enfant ne couvre qu'une partie du programme ». C'est un **risque de plainte**, pas une feature. |

> ☐ **VALIDÉ** — pas de codes côté parent en v1 · ☐ **AUTRE CHOIX** : ____________________________

---

### D-B3 · Bi-curriculum (écoles IB / doubles programmes) : un ou deux frameworks simultanés ?

| | |
|---|---|
| **Recommandation** | **Un seul framework actif par tenant en v1.** Le bi-curriculum double les surfaces et le wording pour un cas minoritaire ; le modèle de données (map N:N) le permet **déjà** — c'est une évolution d'affichage, pas de schéma. À vendre comme « disponible sur demande », pas à construire d'avance. |
| **État réel** | ✅ Déjà câblé : `curriculum_view` est un enum **mono-valué** par organisation. |
| **Si on ne tranche pas** | Rien. Mais en RDV avec une école IB, sans position écrite, on promet le bi-curriculum. |
| **Mon avis** | ✅ Confirmez. **Phrase de RDV** : *« Le modèle de données le supporte, l'affichage se règle en quelques jours — on l'active pour vous si vous signez. »* C'est vrai, et ça vaut mieux que « oui » ou que « non ». |

> ☐ **VALIDÉ** — un framework par tenant en v1 · ☐ **AUTRE CHOIX** : ____________________________

---

### D-B5 · Le rapport école imprimable inclut-il la couverture programme dès la v1 ?

| | |
|---|---|
| **Recommandation** | **Oui.** C'est la matérialisation de l'argument « exprimé dans les codes de VOTRE programme » — la raison d'être du Lot B. Le garde-fou B5 (agrégation stricte : « standard couvert » **seulement si** toutes les compétences EXACT sont maîtrisées) rend l'inclusion sûre. |
| **État réel** | ✅ Câblé : `GET /schools/{id}/proof` → `curriculum_coverage`, section « Couverture du programme » du rapport imprimable. |
| **Si on ne tranche pas** | Rien ne casse — mais c'est **le seul écran qui justifie le Lot B** auprès d'un acheteur. Le retirer viderait le lot de son sens. |
| **Mon avis** | ⚠️ **Confirmez le principe, mais lisez d'abord les findings CRIT-1 et MAJ-1 de `Revue-Code-Findings.md` avant de montrer cet écran à un prospect.** Deux problèmes concrets s'y trouvent : (a) pour un tenant **MoE UAE**, le booléen « couvert » est **structurellement toujours faux** — la section est morte pour le marché public émirien ; (b) le calcul de maîtrise agrège la **moyenne de cohorte**, donc « couvert » peut s'afficher alors que la moitié de la classe est sous le seuil. **Ce n'est pas une raison de retirer la section — c'est une raison de la corriger avant la démo.** |

> ☐ **VALIDÉ** — couverture programme dans le rapport v1 (**après correction des findings CRIT-1 / MAJ-1**)
> ☐ **AUTRE CHOIX** : ______________________________________________________________

---

### D-C2 · Rester Elo ou migrer vers un IRT complet ?

| | |
|---|---|
| **Recommandation** | **Rester Elo en production, IRT en analyse offline.** Le pont C1.1 rend les deux mondes équivalents pour l'audit ; l'Elo garde ses avantages opérationnels (incrémental, pas de re-fit batch, robuste au flux) ; l'IRT offline (Rasch sur le journal) sert à valider/recalibrer périodiquement. *« Migrer le moteur serait un chantier lourd sans gain de crédibilité que le manuel n'apporte déjà. »* |
| **Si on ne tranche pas** | Rien à court terme. Mais **le premier psychométricien croisé en due diligence posera la question** (« pourquoi pas d'IRT ? »), et sans position écrite, la réponse aura l'air d'un aveu. |
| **Mon avis** | ✅ Confirmez, et **préparez la réponse d'une phrase** : *« Elo en ligne pour l'opérationnel, Rasch offline sur le journal pour l'audit et la recalibration — les deux sont équivalents, le manuel technique le démontre. »* C'est une position forte, à condition de l'avoir écrite avant qu'on vous la demande. |

> ☐ **VALIDÉ** — Elo en prod, IRT offline · ☐ **AUTRE CHOIX** : ____________________________

---

## 4. Récapitulatif — 12 décisions, une page

| # | Décision | Reco du cadrage | Bloquant ? | Ce qui casse si on ne tranche pas | ☐ VALIDÉ | ☐ AUTRE |
|---|---|---|---|---|---|---|
| **D-A1** | Périmètre d'extension | Décimaux G4–G5 d'abord | ✅ *acté de fait* | On paie une double lecture sur un choix non signé | ☐ | ☐ |
| **D-A2** | Experts externes | Didacticien 3–4 j + enseignant EAU 2 j | 🔴 **OUI** | **Gate A1.8 infranchissable → production décimaux bloquée** | ☐ | ☐ |
| **D-A3** | G6–G8 | Nouveaux types d'items → chantier distinct | non | On promet le collège en RDV | ☐ | ☐ |
| **D-B1** | Framework par défaut | `ATLAS` neutre, choix explicite | non *(câblé)* | Un « défaut intelligent » étiquette faux | ☐ | ☐ |
| **D-B2** | Codes côté parent | Non en v1 | non *(câblé)* | Sur-interprétation parentale, risque de plainte | ☐ | ☐ |
| **D-B3** | Bi-curriculum | Un framework par tenant en v1 | non *(câblé)* | On le promet à la première école IB | ☐ | ☐ |
| **D-B4** | DataModel §7 | `alignment_type` + `confidence` | ✅ *acté de fait* | Écart doc/code non tracé | ☐ | ☐ |
| **D-B5** | Couverture programme au rapport | Oui en v1 | non *(câblé)* | Le Lot B perd son seul écran de vente | ☐ | ☐ |
| **D-C1** | Calibration vendue | Oui, livrable de pilote | 🔴 **OUI** | **Fenêtre de collecte unique perdue** | ☐ | ☐ |
| **D-C2** | Elo ou IRT | Elo en prod, IRT offline | non | Pas de réponse en due diligence | ☐ | ☐ |
| **D-C3** | Référence externe | Examens internes (+ TIMSS si licence) | 🔴 **OUI** | **Le contrat pilote n'exige pas les données** | ☐ | ☐ |
| **D-C4** | Revue psychométricien | Oui, avant lancement | 🔴 **OUI** | **Défaut de protocole = pilote perdu** | ☐ | ☐ |

**Les 4 bloquantes (D-A2, D-C1, D-C3, D-C4) ont un point commun** : elles portent sur des **fenêtres qui se ferment** — le recrutement des experts, la signature du pilote, le protocole de collecte. Aucune ne peut être rattrapée après coup. **Ce sont celles à signer aujourd'hui.**

---

## 5. Ce que débloque cette signature

| Décisions | Débloque |
|---|---|
| **D-A1 + D-A2** | Le gate **A1.8** (double lecture, Lot 3 de ce dossier) → la production des ~140 items décimaux |
| **D-C1 + D-C3 + D-C4** | La rédaction du **contrat de pilote** (clauses de calibration, accès aux examens, panel enseignants) et le lancement de l'étude C |
| **D-B1..B5** | La démo commerciale du Lot B — **sous réserve** des corrections de `Revue-Code-Findings.md` |
| **D-A3 + D-C2** | Les réponses de RDV et de due diligence, écrites avant qu'on vous les demande |

---

## Signature

| | |
|---|---|
| **Nom** | Nassim Boughazi |
| **Date** | ____________________ |
| **Décisions validées** | ______ / 12 |
| **Décisions modifiées** | ______ / 12 — lesquelles : ______________________________________ |
| **Signature** | ____________________________________________ |

*Aucune décision de ce document n'affirme qu'une mesure Atlas est calibrée, alignée MoE ou validée. Le crosswalk est un mapping expert citant des frameworks publiés ; les priors sont expert-seeded ; l'échelle sera ancrée par l'étude du Lot C.*
