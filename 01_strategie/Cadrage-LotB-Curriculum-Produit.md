# LOT B — Câbler le crosswalk curriculaire dans le produit

**Version** : Cadrage v1 · **Date** : 2026-07-11 · **Auteur** : cadrage produit (Nassim + Claude)
**État produit de référence** : 2026-07-11 — crosswalk = document expert seul (`03_referentiel/Crosswalk-Curriculum-Fractions.md`), aucune table/champ/API curriculum dans le produit ; hook phase 2 spécifié dans `DataModel-KnowledgeGraph.md` §7.
**À lire avec** : `02_technique/DataModel-KnowledgeGraph.md` (§7 — le contrat à respecter), `03_referentiel/crosswalk_fractions_draft.json` (livrable B1, **livré en draft**), `03_referentiel/One-Pager-Alignement-Curriculaire.md` (wording commercial), Cadrage-LotA (règle CI inter-lots), Cadrage-LotC (politique de claims C5).

---

## 1. Objectif et definition of done

**Objectif.** Faire du crosswalk une **capacité produit** : une école choisit son référentiel (MoE / CCSS-M / UK NC) et voit la maîtrise de ses élèves exprimée dans les codes de **son** programme — avec un wording qui respecte le type d'alignement (jamais « atteint le standard X » sur un mapping PARTIAL). Le moteur ne change pas : le curriculum reste une **étiquette projetée** (DataModel §7), jamais une dépendance.

**Pourquoi maintenant.** C'est le quick win commercial n°1 identifié par la revue sales-readiness : le travail intellectuel (32/32 compétences mappées, types + confiances) est fait, il ne manque que la tuyauterie. Réponse produit à l'objection « ça mappe sur quel programme ? » : une démo, plus un PDF.

**Definition of done.**
- [ ] B1 : pivot JSON validé **0 erreur** par le validateur CI (dont réconciliation des types par framework — voir §3/B1, découverte 2026-07-11).
- [ ] B2 : tables `curriculum_standard` + `competency_curriculum_map` migrées (Alembic), seed idempotent depuis le pivot.
- [ ] B3 : `Organization.curriculum_view` configurable (console IT + API), fallback vue Atlas neutre.
- [ ] B4 : codes du framework affichés sur profil élève + lacunes classe + vue école + rapport imprimable, wording par type d'alignement en EN **et** AR.
- [ ] B5 : règle d'agrégation « couverture d'un standard » implémentée et documentée — aucun booléen « standard atteint » hors cas 100 % EXACT maîtrisés.
- [ ] B6 : validateur CI actif — toute compétence `active` non mappée dans un framework activé = build fail.
- [ ] Démo bout-en-bout : école seed en vue CCSS → rapport école avec codes CCSS.

---

## 2. Périmètre (in / out) et dépendances

**In.** Pivot machine-readable + réconciliation ; modèle de données + migration + seed ; réglage par tenant ; surfaces d'affichage (prof, direction, exports) ; règle d'agrégation + tables de wording EN/AR ; validateur CI ; plan de fiabilisation MoE (M → H).

**Out (explicitement).**
- Le **standard-setting** (faire correspondre les *scores* aux bandes de maîtrise) → **Lot C**. B étiquette les *compétences*, C ancre les *niveaux*. Ne jamais confondre les deux en RDV.
- L'ingestion automatique de documents curriculaires par RAG (évoquée §7) → outil de production future, pas nécessaire pour 3 frameworks × 1 domaine.
- CBSE et tout autre framework → à l'apparition d'un prospect qui l'exige.
- La vue parent → décision D-B2 (reco : exclue en v1).

**Dépendances.**
- **B2 conforme au DataModel §7** — avec un amendement à acter (D-B4) : §7 prévoit `competency_curriculum_map (competency_id, standard_id, alignment_strength)` ; le crosswalk réel porte un **type** (EXACT/PARTIAL/BROADER/PREREQ/ENRICH) + une **confiance** (H/M), pas une force scalaire. Le cadrage propose de remplacer `alignment_strength` par `alignment_type` + `confidence` et de mettre à jour §7.
- **A → B** : toute compétence livrée par le Lot A (ex. décimaux) doit arriver avec ses mappings dans le pivot — règle CI B6. Le draft décimaux (`referentiel_decimals_draft.json`) devra être mappé (standards CCSS 4.NF.C.5–7, 5.NBT) **avant** son passage `active`.
- **B → C5** : les tables de wording B5 sont contraintes par la politique de claims du Lot C (on n'affiche pas plus que ce que la maturité de mesure autorise).

---

## 3. Livrables détaillés

### B1 — Pivot machine-readable (source de vérité) — **LIVRÉ EN DRAFT, réconciliation requise**

`03_referentiel/crosswalk_fractions_draft.json` (créé 2026-07-11) : registre des 3 frameworks (éditions, grain, stabilité), légende des types, **32 mappings complets** (CCSS codes + UK years/descriptors + MoE domaine/strand/grade-band/cognitif), chaque alignement portant `derivation: "note" | "row"`.

**Règle structurante** : le JSON devient la source ; le markdown `Crosswalk-Curriculum-Fractions.md` devient une **vue générée** (script `generate_crosswalk_md.py` à créer). Fin du double entretien.

**Deux incohérences découvertes à la construction du pivot (validation du 2026-07-11) — à résoudre AVANT seed :**
1. **Les comptes par framework ne se réconcilient pas.** La table source porte UN type par ligne ; la synthèse authored dit CCSS 22 EXACT / 5 PARTIAL / 5 ENRICH et UK 24/2/4 ; la dérivation ligne-par-ligne (avec les overrides explicites des notes) donne CCSS 22/4/6 et UK 26/3/3. → L'expert fixe le type **par framework** pour chaque ligne divergente ; le pivot porte déjà le champ pour ça.
2. **12/32 niveaux cognitifs MoE contredisent l'enum du référentiel** (ex. `EQUIVALENCE_VISUAL` : MoE *Knowing* vs Atlas `REASON` ; `ADD_UNLIKE_LCM` : *Applying* vs `REASON`) alors que le doc revendique un pont 1:1 avec `CognitiveLevel`. → Arbitrage expert : soit le cognitif du référentiel est trop généreux (à corriger côté A1.5), soit la colonne MoE est indicative et doit être **alignée sur l'enum** (reco : l'enum Atlas fait foi ; la colonne MoE du pivot devient dérivée, avec override documenté si un cas le justifie vraiment).

**Critère d'acceptation B1** : validateur (B6) à 0 erreur = couverture 32/32 ✓ (déjà), types par framework explicites, cognitif MoE cohérent avec l'enum ou override noté, comptes de synthèse recalculés (plus jamais écrits à la main).

### B2 — Modèle de données + migration + seed

Conforme §7, amendé (D-B4) :

```
curriculum_standard
  id UUID PK
  framework ENUM('CCSS_M','UK_NC','MOE_UAE')      -- §7 : enum, pas de table registre en v1
  code STR                                         -- '4.NF.A.1' | 'Y5' | 'NUM_OPS/G4-G5' (MoE : clé composée domaine+band)
  label_en STR / label_ar STR
  grade_hint STR NULL                              -- affichage ('G4', 'Y5', 'G4-G5')
  UNIQUE(framework, code)

competency_curriculum_map
  competency_id FK competency.id (CASCADE)
  standard_id  FK curriculum_standard.id (CASCADE)
  PK(competency_id, standard_id)
  alignment_type ENUM('EXACT','PARTIAL','BROADER','PREREQ','ENRICH')
  confidence ENUM('H','M')
  note STR NULL
  weight_source ENUM réutilisé (EXPERT|...)        -- même pattern de provenance que CompetencyPrerequisite
  weight_version INT DEFAULT 1
```

- **MoE sans codes** : les « standards » MoE sont des clés composées `domaine + grade-band` (+ cognitif porté par la compétence elle-même). Le wording d'affichage MoE dit « domaine Numbers & Operations, Cycle 1 (G4) » — jamais un pseudo-code inventé (ligne rouge du doc source : « affirmer un code MoE serait faux »).
- **Migration Alembic** : 2 tables + enums natifs (piège connu enum/SQLite vs Postgres — cf. mémoire Alembic du projet). Aucun changement sur `competency`.
- **Seed** : `scripts/seed_crosswalk.py`, idempotent (upsert par `(framework, code)` et `(competency_id, standard_id)`), source = pivot JSON, refuse de tourner si le validateur B6 échoue.

### B3 — Réglage par tenant

- `Organization.curriculum_view ENUM('ATLAS','CCSS_M','UK_NC','MOE_UAE') DEFAULT 'ATLAS'` — `ATLAS` = vue neutre actuelle (aucune étiquette), comportement identique à aujourd'hui → zéro régression pour les tenants existants.
- Exposé dans la console IT (`/admin/integration` GET/POST étendu ou endpoint dédié `/admin/curriculum`) + audit log `curriculum.set_view`.
- Toutes les vues de restitution lisent ce réglage ; un seul framework actif par tenant en v1 (D-B3 pour le bi-curriculum).

### B4 — Surfaces d'affichage (par persona, endpoints réels)

| Surface | Endpoint | Ce qui s'ajoute |
|---|---|---|
| Profil élève (héros prof) | `GET /students/{id}/profile` | Badge code standard à côté de chaque compétence (ex. `4.NF.A.1`), tooltip = label officiel + type d'alignement |
| Lacunes classe | `GET /classrooms/{id}/gaps` | Cause racine étiquetée avec son code standard |
| Vue école | `GET /schools/{id}/overview` | Colonne « standard » dans le tableau de maîtrise par compétence |
| Rapport d'impact imprimable | `GET /schools/{id}/proof` + page report | Section « Couverture du programme » : progression agrégée par standard (règle B5) — **l'argument commercial** |
| Exports/API | payloads ci-dessus | Champ `standard: {framework, code, label_en, label_ar, alignment_type}` par compétence |
| Parent | `GET /students/{id}/trajectory` | **Rien en v1** (D-B2) |

**Tables de wording par type d'alignement** (EN + AR, à valider linguiste) — c'est le garde-fou anti-sur-claim :

| Type | EN | AR (à valider) |
|---|---|---|
| EXACT | "aligned to {code}" | "متوافق مع {code}" |
| PARTIAL | "covers part of {code}" | "يغطي جزءًا من {code}" |
| BROADER | "one of several skills within {code}" | "إحدى مهارات {code}" |
| PREREQ | "building block for {code}" | "لبنة أساسية لـ {code}" |
| ENRICH | "beyond {code} expectations" | "يتجاوز متطلبات {code}" |

Confiance M → suffixe « (indicative mapping) » tant que non fiabilisé (B7).

### B5 — Règle d'agrégation « couverture d'un standard »

Pour un standard S dont les compétences mappées sont {c₁…cₙ} :
- **Affichage** : « k/n compétences alignées sur S maîtrisées » (maîtrise = règle moteur existante : `ability_elo ≥ 1500` **et** `n_direct > 0` — inchangée).
- **« Standard couvert »** (booléen, rapport école uniquement) : autorisé **seulement si** toutes les compétences EXACT de S sont maîtrisées ; les PARTIAL/PREREQ n'y contribuent jamais positivement seuls.
- **Jamais** de formulation « meets/atteint {code} » au niveau élève individuel en v1 — c'est une affirmation de standard-setting qui appartient au Lot C. Formulation : « progresse sur les compétences alignées sur {code} ».
- Implémentation : agrégation en lecture dans `views_service` (pas de table dérivée en v1 ; volumes triviaux : 32 compétences).

### B6 — Gouvernance : validateur CI

`scripts/validate_crosswalk.py` (mode CI + mode pré-seed) :
1. Toute compétence `active` du référentiel est mappée dans **chaque** framework du pivot (32/32, puis 46/46 avec décimaux).
2. Tout `alignment_type` est explicite par framework (aucun `derivation: "row"` résiduel non confirmé).
3. Cognitif MoE ≡ `cognitive_level` de la compétence (ou override avec `note` non vide).
4. Les comptes de synthèse sont **calculés**, jamais saisis.
5. Codes standards syntaxiquement valides par framework (regex CCSS `\d\.\w+\.\w\.\d`, UK `Y[1-6]`, MoE clé composée).
Échec = build fail. Même mécanique que le validateur DAG du Lot A : le garde-fou est dans la CI, pas dans la discipline.

### B7 — Fiabilisation MoE (M → H)

1. Obtenir le **document d'outcomes par grade** du MoE via le coordinateur curriculum d'une école pilote (ou contact ADEK/KHDA) — action déjà identifiée dans le doc source (§Provenance).
2. Réviser les grade-bands estimés → confiance H, retirer le suffixe « indicative ».
3. Tant que M : le wording MoE reste au grain honnête (« domaine + cycle »), jamais de pseudo-code.

---

## 4. Plan de travail séquencé (jalons vérifiables)

| Phase | Contenu | Jalon vérifiable | Dépend de |
|---|---|---|---|
| **B-0** | Réconciliation du pivot (types par framework + 12 cognitifs MoE) | Validateur B6 à 0 erreur sur le pivot | expert (0,5–1 j) |
| **B-1** | B2 : migration + modèles + seed | `alembic upgrade head` sur PG vierge ; seed idempotent (2 runs = mêmes comptes) | B-0 |
| **B-2** | B6 : validateur en CI + markdown généré | CI rouge si mapping manquant ; `Crosswalk-*.md` régénéré identique au contenu actuel réconcilié | B-1 |
| **B-3** | B3 : `curriculum_view` + console IT + audit | École de test basculée en `CCSS_M` via l'UI ; log d'audit présent | B-1 |
| **B-4** | B4 : surfaces + wording EN/AR | Profil élève et lacunes classe affichent les codes ; wording conforme aux tables ; AR validé linguiste | B-3 |
| **B-5** | B5 : agrégation + rapport école | Rapport imprimable avec section « Couverture du programme » ; aucun « meets » individuel | B-4 |
| **B-6** | Démo + doc commerciale | Screencast vue CCSS + vue MoE sur école seed ; One-Pager mis à jour | tout B |

**Chemin critique** : B-0 (expert) → B-1. Tout le reste est du développement sans inconnue. **B est le lot le plus court des trois** — à exécuter en premier.

---

## 5. Ressources : profils et effort

| Livrable | Profil | Effort |
|---|---|---|
| B-0 réconciliation | Fondateur + didacticien (le même que Lot A/A1.8) | 0,5–1 j |
| B1 pivot | **fait** (draft) + corrections B-0 | 0,5 j |
| B2 migration/seed | Fondateur + Claude | 1–1,5 j |
| B3 tenant + console | Fondateur + Claude | 1 j |
| B4 surfaces + wording | Fondateur + Claude + **linguiste AR** (tables de wording) | 1,5–2 j |
| B5 agrégation + rapport | Fondateur + Claude | 1 j |
| B6 validateur CI + md généré | Fondateur + Claude | 1 j |
| B7 MoE M→H | École pilote / réseau (asynchrone) | dépend de l'accès au doc |
| **Total dev** | | **~6–8 j** |

---

## 6. Risques et mitigations (top 5)

| # | Risque | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Sur-claim** : un écran affiche « meets 4.NF.A.1 » et un Head of Assessment démonte la crédibilité | M | Élevé | Tables de wording B4 fermées (pas de texte libre) ; règle B5 « jamais au niveau individuel » ; revue croisée avec politique C5 avant mise en prod |
| 2 | **Pseudo-codes MoE** inventés pour « faire propre » | M | Élevé | Ligne rouge écrite (B2) ; le modèle de données MoE n'a pas de champ code standard classique — clé composée uniquement |
| 3 | **Dérive doc/produit** : le markdown est corrigé mais pas le pivot (ou l'inverse) | H sans garde-fou | M | Markdown généré depuis le JSON (B-2) ; interdiction d'éditer le md à la main (note d'en-tête) |
| 4 | **Confusion UK Year vs US Grade** (Y5 ≈ G4 en âge) : un élève G4 étiqueté « Y5 » perturbe un prof habitué à l'autre convention | M | M | `grade_hint` affiché avec le préfixe du framework (« UK Y5 ») + note d'équivalence d'âge dans le rapport ; jamais de conversion silencieuse |
| 5 | **Le référentiel évolue sans les mappings** (décimaux activés non mappés) | M | Élevé | Validateur B6 règle 1 en CI : compétence `active` non mappée = build fail ; procédure Lot A mise à jour (livrer référentiel + mappings ensemble) |

---

## 7. Décisions à prendre par le fondateur (avec recommandation)

**D-B1 — Framework par défaut par type d'école.**
> **Recommandation : aucun défaut « intelligent » — `ATLAS` (neutre) par défaut, choix explicite à l'onboarding.** Le mix EAU (privées US/UK/IB, publiques MoE) rend tout défaut faux une fois sur deux ; le choix explicite est un moment commercial utile (« quel est votre programme ? ») et évite un étiquetage erroné silencieux.

**D-B2 — Vue parent : codes standards ou pas ?**
> **Recommandation : pas en v1.** La page parent est volontairement apaisée (pas de percentiles de pairs, pas de chaînes causales) ; des codes CCSS n'y apportent rien à un parent et ouvrent des questions de sur-interprétation. Réévaluer si les écoles le demandent.

**D-B3 — Bi-curriculum (écoles IB / doubles programmes) : un ou deux frameworks simultanés ?**
> **Recommandation : un seul framework actif par tenant en v1.** Le bi-curriculum double les surfaces et le wording pour un cas minoritaire ; le modèle de données (map N:N) le permet déjà — c'est une évolution d'affichage, pas de schéma. À vendre comme « disponible sur demande », pas à construire d'avance.

**D-B4 — Amendement du DataModel §7 (`alignment_strength` → `alignment_type` + `confidence`).**
> **Recommandation : oui, amender §7.** La force scalaire était un placeholder ; le crosswalk réel a produit une sémantique plus riche (type + confiance) qui pilote directement le wording. Mettre à jour le doc §7 pour que le contrat écrit reste la référence (même discipline que l'errata du Lot A).

**D-B5 — Le rapport école imprimable inclut la couverture programme dès la v1 ?**
> **Recommandation : oui.** C'est la matérialisation de l'argument « exprimé dans les codes de VOTRE programme » — la raison d'être du lot. Le garde-fou B5 (agrégation stricte) rend l'inclusion sûre.
