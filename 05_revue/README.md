# `05_revue/` — Dossier de validation humaine

**Créé le** : 2026-07-12 · **Contexte** : aval du chantier Lots A/B/C (code vert — 441 tests, documents livrés).
**Objet** : il ne reste que des **validations humaines**. Ce dossier prépare le travail de chaque validateur pour qu'il tienne en **une session courte**.

> **Aucun document de ce dossier ne remplace une validation.** Tout ce qui y est proposé est marqué **« PROPOSITION — à valider »**.

> **⚑ Mise à jour 2026-07-12 (soir) — les 3 findings CRITIQUES de la revue de code sont CORRIGÉS.**
> CRIT-1 (gate AR aveugle au stem), CRIT-2 (seed insert-only), CRIT-3 (pseudo-code MoE + couverture morte) ont été traités et vérifiés — **450 tests verts, typecheck TS propre**. Les 5 items faux de CRIT-1 sont **quarantainés** (banque : 279 actifs / 20 quarantainés) et rejoignent la file de retraduction du Lot 2 (**20 items** au total, pas 15). Deux majeurs adjacents (MAJ-1 couverture sur la moyenne, MAJ-2 suffixe anglais en arabe) ont été corrigés au passage. Détail à jour dans `Revue-Code-Findings.md`. **Ne reste bloquant pour le commit que MAJ-3** (réponses synthétiques en prod — à voir avant de provisionner le tenant pilote).

---

## Qui lit quoi, dans quel ordre

| Ordre | Fichier | Qui | Budget | Ce qu'il/elle fait |
|---|---|---|---|---|
| **1** | **`Decisions-Fondateur.md`** | **Nassim** | **30 min** | Signe 12 décisions (D-A1..3, D-B1..5, D-C1..4). **2 sont déjà actées de fait** (un trait suffit), **4 sont bloquantes**. |
| **2** | **`Revue-Code-Findings.md`** | **Nassim** | **45 min** | Lit 3 findings critiques. **Deux d'entre eux doivent être traités AVANT que les Lots 1 et 3 servent à quelque chose.** |
| **3** | **`Revue-Pivot-Crosswalk.md`** | **Didacticien** / auteur du crosswalk | **45 min** | Confirme 22 décisions de réconciliation + tranche 2 questions ouvertes. Signe. |
| **4** | **`Retraduction-15-Items.md`** | **Linguiste AR** | **1 h** | Valide ou corrige 15 propositions de retraduction. Signe. |
| **5** | **`Double-Lecture-Decimaux.md`** | **Didacticien** *et* **Enseignant primaire EAU** — **séparément** | **2 h chacun**, puis 1 h de réconciliation | Remplit la grille A1.8 (14 nœuds, 26 arêtes) **seul**, sans voir l'autre. Puis séance de réconciliation, arbitrages journalisés. Double signature. |

**Charge totale par personne**

| Personne | Documents | Temps |
|---|---|---|
| **Nassim (fondateur)** | Décisions + Revue de code | **~1 h 15** |
| **Didacticien** | Pivot crosswalk + Double lecture (lecteur A) | **~2 h 45** |
| **Enseignant primaire EAU** | Double lecture (lecteur B) | **~2 h** |
| **Linguiste AR** | Retraduction 15 items | **~1 h** |
| **Réconciliation décimaux** (didacticien + enseignant) | séance commune | **~1 h** |

---

## ✅ Findings critiques — TOUS CORRIGÉS le 2026-07-12 (détail dans `Revue-Code-Findings.md`)

| Finding | Statut |
|---|---|
| **CRIT-2** — `seed_crosswalk.py` était **insert-only** | ✅ **Corrigé** : vrai upsert (met à jour type/confiance/labels/note, `weight_version++` si le type change ; compteurs `*_updated`). La clôture du Lot 1 (reseed après confirmation experte) propage désormais les corrections. Test dédié. |
| **CRIT-1** — le gate de fidélité AR était aveugle au stem | ✅ **Corrigé** : détecteur `ar_stem_numbers_preserved` + `ar_mcq_structure_ok`, câblés en dur dans le gate G3 (`validate_arabic`). **Les 5 items faux sont quarantainés** ; ils rejoignent la file du Lot 2. Vérifié : les 15 retraductions proposées passent le nouveau gate. |
| **CRIT-3** — pseudo-code MoE affiché + « couverture » morte en vue MoE | ✅ **Corrigé** : `display_code` (null pour MoE → label affiché, jamais la clé technique) ; wording MoE dédié sans code ; `shows_covered=false` en MoE (pas de verdict). Concerne toujours la décision **D-B5** du Lot 4 (à confirmer). |

*Reste ouvert (non bloquant pour le commit sauf MAJ-3) : MAJ-3 (réponses synthétiques dans un tenant de prod — à régler AVANT de provisionner le tenant pilote), MAJ-4, MIN-1..5.*

---

## Ce que débloque chaque signature

```
Lot 4 — Decisions-Fondateur.md ─── D-A2 (experts) ──────┐
                                └── D-C1/C3/C4 ─────────┼──▶ contrat de pilote + étude de calibration (Lot C)
                                                        │
Lot 3 — Double-Lecture-Decimaux.md (double signature) ──┴──▶ gate A1.8 franchi
                                                             └──▶ 14 nœuds décimaux passent `active`
                                                                  └──▶ PRODUCTION DES ~140 ITEMS DÉCIMAUX (A-5/A-6)

Lot 1 — Revue-Pivot-Crosswalk.md (signature didacticien)
        └──▶ expert_confirmation_pending = false
             └──▶ validateur à 0 erreur
                  └──▶ SEED PROD DU CROSSWALK  ⚠️ conditionné par CRIT-2
                       └──▶ affichage des codes de standards (B4) + rapport « Couverture du programme » (B5)

Lot 2 — Retraduction-15-Items.md (signature linguiste)
        └──▶ set_arabic → validate_arabic → promote_to_active
             └──▶ RÉACTIVATION DES 15 ITEMS (banque fractions : 284 → 299 actifs)

Lot 5 — Revue-Code-Findings.md (CRIT-1, CRIT-2, CRIT-3 traités)
        └──▶ COMMIT du chantier
```

**Dépendances croisées à connaître** :

- **Lot 1 → CRIT-2 corrigé** : la confirmation du didacticien se propage désormais en base au reseed (upsert).
- **Lot 2 → recoupe CRIT-1** : les 5 items défectueux sont maintenant quarantainés → **20 items** à retraduire (les 15 initiaux + ces 5). Ajouter les 5 au kit `Retraduction-15-Items.md` / `retraductions_proposees.json`.
- **Production décimaux → dépend des Lots 3 ET 4** (D-A1 confirme le périmètre, D-A2 finance les experts, A1.8 valide le référentiel).
- **Commit → les 3 critiques du Lot 5 sont corrigés** ; ne reste que MAJ-3 à arbitrer avant provisioning pilote.

---

## Contenu du dossier

| Fichier | Type |
|---|---|
| `README.md` | ce document |
| `Revue-Pivot-Crosswalk.md` | Lot 1 — dossier de confirmation experte du pivot crosswalk |
| `Retraduction-15-Items.md` | Lot 2 — kit de validation linguiste (15 fiches) |
| `retraductions_proposees.json` | Lot 2 — **sortie machine**, prête pour la réimport **APRÈS** validation linguiste (format `[{"id", "content_ar"}]`) |
| `Double-Lecture-Decimaux.md` | Lot 3 — grille A1.8 pré-remplie (14 nœuds, 26 arêtes, 4 points d'arbitrage, registre) |
| `Decisions-Fondateur.md` | Lot 4 — feuille de décision (12 décisions consolidées des §7 des cadrages) |
| `Revue-Code-Findings.md` | Lot 5 — revue adversariale en lecture seule (3 critiques, 4 majeurs, 5 mineurs) |

---

## Vérifications faites pendant la préparation de ce dossier

*Tout est rejouable. Rien n'est déclaratif.*

| Contrôle | Résultat |
|---|---|
| Suite de tests `04_code` (`pytest -q`) | **441 passed, 1 skipped** ✅ |
| `scripts/validate_crosswalk.py` sur le pivot actuel | **0 erreur** ✅ |
| Cohérence des 32 cognitifs MoE du pivot avec l'enum du référentiel | **0 écart** ✅ |
| Synthèse du crosswalk recalculée (CCSS 18/6/8 · UK 22/7/3) | somme = **32** par framework ✅ *(l'authored UK 24/2/4 = 30 était faux)* |
| Les 15 propositions de retraduction × 3 checks (`ar_math_preserved`, `ar_content_latin_tokens`, `ar_content_suspect_glyphs`) | **15/15 passent** ✅ |
| Contraintes structurelles du draft décimaux (densité, DAG, bornes de poids, monotonie des priors sur les HARD) | **conformes** ✅ *(26/26 HARD monotones, 0 cycle sur le graphe combiné)* |
| Invariants de la banque (answer AR ∈ options AR ; index EN = index AR) sur 284 items actifs | **0 défaut** ✅ |
| Working tree `04_code/` | **inchangé** ✅ (lecture seule, aucun `git commit`) |

---

*Les priors, types d'alignement et mappings curriculaires manipulés dans ce dossier sont des **choix experts**. Aucun n'est calibré, aligné MoE, ni validé — c'est précisément l'objet des signatures demandées ici.*
