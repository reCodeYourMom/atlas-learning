# Revue de code adversariale — findings

**Lot 5 du dossier de revue** · **Date** : 2026-07-12 · **Mode : LECTURE SEULE — aucun fichier de `04_code/` n'a été modifié.**
**Périmètre** : le chantier Lots A/B/C — `src/models/`, `alembic/versions/0019` (+ retouches 0003/0017), `src/api/app.py`, `src/api/views_service.py`, `src/engine/service.py`, `src/items/arabic.py`, `scripts/`, `web/app/`, `tests/`.
**Base de référence** : suite verte — **441 passed, 1 skipped** (rejouée le 2026-07-12). Le validateur crosswalk rend **0 erreur**.

> **Ce document ne contient aucun patch appliqué.** Chaque correction est décrite en texte. Rien n'est commité (le projet vit en working tree non commité, c'est voulu).

---

## Synthèse

| Sévérité | Nb | Findings |
|---|---|---|
| 🔴 **Critique** | **3** | CRIT-1 (gate AR aveugle → **5 items faux servis en production**) · CRIT-2 (seed non-idempotent en **update** → les corrections de l'expert seront ignorées) · CRIT-3 (**pseudo-code MoE affiché** — ligne rouge du cadrage — et section « couverture » morte pour le marché MoE) |
| 🟠 **Majeur** | **4** | MAJ-1 (« standard couvert » calculé sur la **moyenne de cohorte**) · MAJ-2 (**texte anglais injecté dans le wording arabe**) · MAJ-3 (réponses **synthétiques** dans un tenant de prod, journal append-only) · MAJ-4 (wording ENRICH trompeur) |
| 🟡 **Mineur** | **5** | MIN-1 à MIN-5 |

**Ce qui a été cherché et NON trouvé** (§4) : je n'ai trouvé **aucune** régression sur le payload de la vue ATLAS, **aucune** fuite tenant dans les vues enrichies, **aucun** chemin de création de `Response` sans langue, **aucune** divergence migration/modèles, **aucun** défaut du pattern enum SQLite/Postgres. **Ces axes sont propres — je le dis explicitement plutôt que de gonfler le rapport.**

---

## 1. 🔴 CRITIQUE

---

### CRIT-1 · Le gate de fidélité arabe (G3) est structurellement aveugle au stem — **5 items ACTIFS sont mathématiquement faux en arabe**

**Fichiers** : `src/items/arabic.py:60–75` (`ar_math_preserved`) · `scripts/check_ar_fidelity.py` · gate G3 (`src/items/review.py`)

**Le défaut.** `ar_math_preserved()` ne compare que les nombres de `answer` et de `options`. Elle **ne lit jamais le `stem`** — et sa docstring l'assume :

```python
# src/items/arabic.py:66-70
# Le texte — stem inclus — reste le travail du linguiste : un nombre écrit en
# toutes lettres (« ثمانية ») n'est volontairement pas comparé.
```

Le lint de tokens latins (F2) ne voit rien non plus (l'arabe n'a pas de lettres latines) et le détecteur de glyphes (F3) ne voit rien (le texte est de l'arabe valide). **Un stem arabe peut donc énoncer un problème complètement différent de l'anglais, avec la clé de correction anglaise, et franchir les trois checks.**

**Scénario d'échec — ce n'est pas théorique, c'est en base.** Scan des 284 items `active` de `04_code/atlas_bank.db` :

| ID | Compétence | Stem EN | Stem AR (traduit) | Conséquence |
|---|---|---|---|---|
| `4ace2985` | `NF.FRACTION_OF_SET` | *A set has 12 objects. **3/4** are red* → clé **9** | « **ثلث** هذه الأجسام حمراء » = **un tiers** | 1/3 × 12 = **4**, la clé dit 9 |
| `7037c1cc` | `NF.FRACTION_OF_SET` | *16 objects. **3/8** are red* → clé **6** | « **ثلث** » = **un tiers** | 1/3 × 16 ≈ **5,33**, la clé dit 6 |
| `547997f0` | `NF.FRACTION_OF_SET` | *30 objects. **4/5** are red* → clé **24** | « **ربعها** » = **un quart** | 1/4 × 30 = **7,5**, la clé dit 24 |
| `2dd2318f` | `NF.FRACTION_OF_SET` | *28 objects. **3/7** are red* → clé **12** | « ثلث وسبعون » = charabia | énoncé insoluble |
| `5302e9e7` | `NF.EQUIVALENCE_COMPUTE` | *Find the missing **numerator**: 1/4 = x/20* → clé **5** | « اوجد **المقام المشترك**… » = *trouver le **dénominateur commun*** | **autre question** ; la clé (5) est un numérateur |

Les 5 sont `status=active`, `ar_validated=True`, et passent `ar_math_preserved` = **True**, `ar_content_latin_tokens` = **[]**, `ar_content_suspect_glyphs` = **[]**.

**Ce que ça produit en pilote.** Un élève servi en arabe échoue ces items — non par manque de compétence, mais parce que l'énoncé est faux. Son `ability_elo` chute sur `FRACTION_OF_SET` et `EQUIVALENCE_COMPUTE`. Le **diagnostic causal** (l'argument de vente) remonte alors une lacune inventée, et la **remédiation** propose du travail sur une compétence maîtrisée. Le biais est **systématique et corrélé à la langue** — exactement le signal que la colonne `response.language` (C-0) doit détecter, sauf qu'ici ce n'est pas du DIF psychométrique : **ce sont des items faux**.

C'est aussi le trou par lequel les 15 items quarantainés sont passés : l'item `7a25bb9b` (`COMPARE_BENCHMARK`) n'a **aucun** glyphe suspect — son stem est du charabia arabe pur. Il n'a été attrapé que par une inspection manuelle.

**Correction proposée** (texte, non appliquée) :

1. **Nouveau check F1-bis dans `src/items/arabic.py`** — invariant : *tout token numérique du stem EN doit apparaître dans le stem AR*.
   ```
   def ar_stem_numbers_preserved(content_en, content_ar) -> bool:
       return set(_num_multiset(content_en["stem"])) <= set(_num_multiset(content_ar["stem"]))
   ```
   *(inclusion, pas égalité : l'arabe peut légitimement ajouter un nombre, jamais en perdre.)*
   Ce check aurait attrapé **les 5 items ci-dessus** et **14 des 15 quarantainés**.
2. **Câbler F1-bis dans le gate G3** (`review.py`, garde `promote_to_active`) et dans `check_ar_fidelity.py --flag` → `provenance.ar_stem_numbers_lost`.
3. **Ajouter l'invariant structurel MCQ** (coût nul, valeur immédiate) : `content_ar["answer"] in content_ar["options"]` **et** `options_ar.index(answer_ar) == options_en.index(answer_en)`. *(Vérifié : la banque actuelle est **saine** sur cet invariant — 0/284 en défaut. Le check protège l'avenir, pas le présent.)*
4. **Immédiat, avant tout pilote arabophone** : quarantaine des 5 items (`run_quarantine.py`) + ajout à la file de retraduction du Lot 2.

**Note de portée** : le scan complet montre **28 items actifs sur 284** dont le stem AR perd au moins un nombre du stem EN. Les 23 autres sont **mathématiquement corrects** (nombres écrits en toutes lettres : « أربعة أجزاء » pour « 4 parts ») mais violent la convention E7 (chiffres occidentaux 0–9). Non bloquant — mais le check F1-bis les flaguera tous : prévoir une passe de nettoyage, ou tolérer une liste blanche.

---

### CRIT-2 · `seed_crosswalk.py` se dit « upsert » mais il est **insert-only** — les corrections de l'expert ne seront jamais appliquées

**Fichier** : `scripts/seed_crosswalk.py:144` et `:162`

```python
# ligne 5 (docstring) : « Idempotent : upsert par (framework, code) pour les
#                        standards et par (competency_id, standard_id) pour les mappings. »

# ligne 143-149 — standards
for (framework, code), attrs in defs.items():
    if (framework, code) in existing_std:
        continue                      # ← aucun UPDATE des labels / grade_hint
    ...

# ligne 160-176 — mappings
for comp_code, framework, std_code, alignment, confidence, note in map_rows:
    key = (comp_by_code[comp_code], existing_std[(framework, std_code)].id)
    if key in existing_maps:
        continue                      # ← aucun UPDATE d'alignment_type / confidence / note
    ...
```

Ce n'est pas un upsert : c'est un **insert-if-absent**. La ré-exécution est *idempotente au sens « ne duplique pas »*, mais elle **n'applique aucune modification** du pivot sur les lignes existantes.

**Scénario d'échec — il est certain, pas hypothétique.** C'est exactement la séquence prévue par le Lot 1 de ce dossier :

1. Le crosswalk est seedé en base (démo, staging).
2. Le didacticien confirme le pivot et **corrige** `#30 IMPROPER_TO_MIXED [ccss_m]` : `PARTIAL → PREREQ` (question ouverte Q1, `Revue-Pivot-Crosswalk.md` §4).
3. On met le pivot à jour, le validateur rend 0 erreur, on relance `seed_crosswalk.py`.
4. Le script affiche `{"maps_created": 0}` — **et la base contient toujours PARTIAL**.
5. Le produit affiche *« covers part of 4.NF.B.3b »* au lieu de *« building block for 4.NF.B.3b »*. **Aucune erreur, aucun log, aucun test rouge.** L'écart entre le pivot signé et ce que voit le client est silencieux.

Le même piège frappe les `note` (la trace de réconciliation), le `grade_hint` et les labels.

**Correction proposée** :

- Remplacer les deux `continue` par une **mise à jour des champs** quand la clé existe :
  ```
  std = existing_std[(framework, code)]
  std.label_en, std.label_ar, std.grade_hint = attrs["label_en"], attrs["label_ar"], attrs["grade_hint"]
  ```
  ```
  m = existing_maps_by_key[key]
  m.alignment_type, m.confidence, m.note = alignment, confidence, note
  m.weight_version += 1 if (m.alignment_type != alignment) else 0
  ```
- Retourner dans le compte-rendu `standards_updated` / `maps_updated` (aujourd'hui invisibles).
- **Test à ajouter** : seeder, muter un `alignment_type` dans le pivot, reseeder, **assert que la DB reflète la mutation**. Le test actuel (`test_crosswalk_pipeline.py`) vérifie qu'un double seed ne duplique pas — il ne vérifie pas qu'un seed **met à jour**.
- **Alternative acceptable** (si l'on veut garder l'insert-only) : faire **échouer** le seed quand une ligne existante diverge du pivot, avec un message explicite (« purger les tables ou utiliser --force »). Silence = le pire choix.

**⚠️ Conséquence opérationnelle immédiate** : la procédure de clôture du Lot 1 dit de reseeder après confirmation experte. **Tant que ce finding n'est pas corrigé, il faut vider `competency_curriculum_map` et `curriculum_standard` avant de reseeder.**

---

### CRIT-3 · MoE UAE : le produit affiche un **pseudo-code** (`NUM_OPS.G4-G5`) — c'est la ligne rouge écrite du cadrage — et la « couverture programme » est **structurellement morte** sur ce framework

**Fichiers** : `scripts/seed_crosswalk.py:118–119` · `src/api/views_service.py:59–72, 102–116, 416–424` · `web/components/StandardBadge.tsx:21` · `web/app/admin/[schoolId]/report/page.tsx:236`

**La ligne rouge, telle qu'écrite.**

> `Cadrage-LotB` §3/B2 : « Le wording d'affichage MoE dit **« domaine Numbers & Operations, Cycle 1 (G4) »** — **jamais un pseudo-code inventé** (ligne rouge du doc source : « affirmer un code MoE serait faux »). »
> `Cadrage-LotB` §6, risque n°2 : « **Pseudo-codes MoE inventés pour "faire propre"** — probabilité M, impact **Élevé**. »
> `Crosswalk-Curriculum-Fractions.md` §MoE : « Affirmer un code MoE serait faux et **détruirait la crédibilité en due diligence**. »

**Ce que le code fait.**

1. Le seed fabrique la clé composée `NUM_OPS.G4-G5` (`moe_composed_key`) et la stocke dans `curriculum_standard.code` — **c'est correct**, c'est bien la clé composée prévue, et le `label_en` est propre : `"Numbers & Operations — Cycle 1 (G4-G5)"`.
2. Mais le **badge affiché** ne rend pas le label : il rend le **code**.
   ```tsx
   // web/components/StandardBadge.tsx:16-22
   <span className="… font-mono text-[10px] …" title={…wording…} data-ltr>
     {standard.code}          // ← "NUM_OPS.G4-G5"
   </span>
   ```
   `font-mono`, `data-ltr`, chip gris : **exactement la typographie utilisée pour `4.NF.A.1`**. Un chef d'établissement émirien voit `NUM_OPS.G4-G5` présenté comme un code officiel de son ministère. **Il n'existe pas.**
3. Le rapport école imprimable fait pareil : `report/page.tsx:236` affiche `{s.code}` en `font-mono` dans la colonne de gauche.
4. Le **wording** aggrave : le seed force `AlignmentType.BROADER` pour **tous** les mappings MoE (`seed_crosswalk.py:118-119`), donc le tooltip dit *« one of several skills within **NUM_OPS.G4-G5** »* — une phrase qui traite la clé composée comme un standard.

**Second défaut, du même mécanisme.** Puisque **tous** les mappings MoE sont `BROADER`, il n'existe **aucun** mapping `EXACT` sur ce framework. Or :

```python
# src/api/views_service.py:416-424
exact_mastered = [ok for m, ok in zip(ms, mastered)
                  if m.alignment_type == AlignmentType.EXACT]
...
"covered": bool(exact_mastered) and all(exact_mastered),
```

`exact_mastered` est **toujours vide** ⇒ `covered` est **toujours `False`** ⇒ pour un tenant `MOE_UAE`, la section « Couverture du programme » du rapport école — **l'argument commercial du Lot B** (D-B5) — affiche une colonne de croix, quelles que soient les performances de l'école. **La feature vendue est morte sur le marché public émirien, c'est-à-dire la cible B2G.**

**Scénario d'échec concret.** Démo à une école publique de Dubaï, vue `MOE_UAE` : le rapport affiche 6 lignes `NUM_OPS.G2` … `NUM_OPS.G5`, toutes marquées non couvertes, avec des badges `NUM_OPS.G4-G5` que personne ne reconnaît. Le Head of Assessment demande d'où sort ce code. Réponse honnête : « nous l'avons fabriqué ». C'est le scénario que le cadrage voulait éviter.

**Correction proposée** (trois pièces, indépendantes) :

1. **Affichage** — introduire un champ `display_code` dans `_standard_payload` (`views_service.py:108-116`) : `std.code` pour CCSS/UK, **`std.grade_hint` ou `null`** pour MoE. `StandardBadge` n'affiche rien si `display_code` est `null`, et rend le `label` (« Numbers & Operations — Cycle 1 (G4) ») en texte normal, **pas en font-mono**. La clé composée reste la clé technique, jamais un affichage.
2. **Wording MoE** — sortir MoE des tables `_ALIGNMENT_WORDING_*` : un wording dédié, sans `{code}`, du type *« domaine Numbers & Operations, Cycle 1 »* / « مجال الأعداد والعمليات — الحلقة الأولى ».
3. **Règle B5 pour MoE** — décider explicitement ce que « couvert » veut dire quand le framework n'a pas de standards codés. **Ma recommandation : ne pas afficher la colonne `covered` du tout en vue MoE** (afficher uniquement « k/n compétences maîtrisées » par domaine/band). Un booléen « couvert » sur un domaine entier serait de toute façon un sur-claim. **Une colonne absente est honnête ; une colonne toujours fausse est un bug qui a l'air d'un verdict.**

**Décision à remonter au fondateur** : le type `BROADER` attribué d'office aux mappings MoE **n'est validé par personne** — il n'apparaît ni dans le pivot, ni dans les 10 décisions soumises à l'expert (le validateur R2 exempte explicitement MoE). C'est un choix pris **dans le script de seed**. Il doit être soit remonté dans le pivot (et validé), soit remplacé par la règle d'affichage ci-dessus.

---

## 2. 🟠 MAJEUR

---

### MAJ-1 · « Standard couvert » est calculé sur la **moyenne de la cohorte** — un standard peut être « couvert » avec la moitié de la classe sous le seuil

**Fichier** : `src/api/views_service.py:398–401` (et docstring `:372–374`)

```python
comp_mastered = {
    cid: _is_mastered(mean([r.ability_elo for r in rr]), sum(r.n_direct for r in rr))
    for cid, rr in by_comp.items()
}
```

La docstring annonce : *« Maîtrise cohorte = règle moteur **INCHANGÉE** (`_is_mastered`) »*. **C'est inexact.** La règle moteur est **par élève** (`ability_elo ≥ 1500` **et** `n_direct > 0`). Ici on l'applique à la **moyenne** des abilities de l'école et à la **somme** des `n_direct`. Ce n'est pas la même règle : c'est une **règle nouvelle, non spécifiée**, qui répond à une autre question.

**Scénario d'échec.** École de 20 élèves sur une compétence EXACT de `4.NF.A.1` : 10 élèves à 1200, 10 élèves à 1800. Moyenne = **1500** ⇒ `_is_mastered(1500, …)` = **True** ⇒ le rapport imprimable affiche **« ✓ couvert »** sur `4.NF.A.1`, alors que **la moitié de l'école ne maîtrise pas la compétence**. Ce rapport est le document que l'école montre à ses parents et à son inspection.

Le cadrage B5 dit : *« k/n **compétences alignées sur S maîtrisées** »* — sans préciser « par qui ». L'implémentation a comblé le silence par la moyenne. C'est le choix le plus flatteur et le moins défendable.

**Correction proposée** :

- Remplacer la maîtrise-par-moyenne par un **taux de maîtrise** : `pct_mastered = nb d'élèves mastered / nb d'élèves mesurés` (c'est déjà ce que `school_overview` calcule, ligne 346 — **deux définitions coexistent dans le même fichier**).
- Réserver `covered: true` à un **seuil explicite et écrit** (ex. « ≥ 80 % des élèves mesurés maîtrisent **toutes** les compétences EXACT de S »), et **afficher ce seuil dans le rapport**.
- Aligner la docstring : dire ce que le code fait, pas ce qu'on aurait aimé qu'il fasse.
- **Vérifier avec `Politique-Claims-Mesure.md`** : un booléen « couvert » adossé à une moyenne est une affirmation qu'on ne peut pas défendre devant un psychométricien.

---

### MAJ-2 · Le suffixe **anglais** « (indicative mapping) » est concaténé au wording **arabe**

**Fichier** : `src/api/views_service.py:75, 105–107`

```python
_INDICATIVE_SUFFIX = " (indicative mapping)"
...
if m.confidence == MappingConfidence.M:
    wording_en += _INDICATIVE_SUFFIX
    wording_ar += _INDICATIVE_SUFFIX      # ← texte anglais dans une chaîne RTL arabe
```

Le commentaire l'assume : *« Le cadrage ne fixe qu'un suffixe EN ; appliqué aux deux langues en attendant la validation linguiste. »* Mais le résultat est servi **en production** :

> `متوافق مع 4.NF.A.1 (indicative mapping)`

Un fragment anglais LTR au milieu d'un texte arabe RTL, dans un produit dont **la parité bilingue est un argument de vente GCC**.

**Ampleur — ce n'est pas un cas marginal.** Dans le pivot actuel, **les 32 mappings MoE portent `confidence: M`** (le seed calcule `min(domain, grade_band)` et `grade_band` est M partout — `seed_crosswalk.py:112-114`). Donc pour un tenant `MOE_UAE` en interface arabe, **100 % des badges** afficheront ce suffixe anglais. Côté CCSS/UK, seuls #9 et #23 sont en M.

**Correction proposée** : suffixe arabe dédié — `_INDICATIVE_SUFFIX_AR = " (تعيين استرشادي)"` (à faire valider par la linguiste ; le glossaire n'a pas encore de terme pour *indicative mapping*). Coût : 2 lignes. À traiter **avec** le lot de wording AR de la linguiste (Lot 2), pas séparément.

---

### MAJ-3 · `provision_prod_tenant.py` injecte des réponses **synthétiques** dans un tenant de **production**, dans un journal **append-only**, étiquetées `language='en'` par défaut

**Fichier** : `scripts/provision_prod_tenant.py:118–125` (et son jumeau `scripts/seed_demo_movements.py:144–150`)

```python
for k in range(3):
    s.add(Response(school_id=school.id, student_id=st.id, item_id=it.id,
                   competency_id=comp[code].id, is_correct=(k == 0), created_at=old))
for k in range(3):
    s.add(Response(school_id=school.id, student_id=st.id, item_id=it.id,
                   competency_id=comp[code].id, is_correct=(k != 0), created_at=recent))
```

**Trois problèmes qui se composent.**

1. **Ce sont de fausses réponses dans un tenant de prod.** Le script s'appelle `provision_prod_tenant`. Il crée ~6 `Response` par élève pour fabriquer un « avant/après » de démo. La table `Response` est **append-only** (« ni update, ni delete » — `measurement.py:57`). Ces lignes ne partiront jamais.
2. **Elles n'ont pas de langue explicite** ⇒ défaut python `ResponseLanguage.EN`. Or **toute la raison d'être de la colonne `language` (C-0)** est écrite dans la migration `0019` : *« Sans la langue servie, aucune analyse DIF EN/AR ne sera jamais possible sur le journal append-only du pilote (**pas de backfill**) »*. On injecte donc du bruit étiqueté `en` dans la population même qui servira à mesurer le biais de langue.
3. **Rien ne les distingue des vraies.** `Response` n'a **aucun** marqueur `synthetic` / `seeded`. Une requête d'analyse (`scripts/analysis/`, étude de calibration C2) ne peut pas les exclure autrement qu'en filtrant sur des `student_id` connus — donc en pratique, elle ne les exclura pas.

**Scénario d'échec.** Pilote lancé sur le tenant provisionné. À la fin, l'étude de calibration (Lot C, D-C1 — **un livrable vendu**) tourne sur `response`. Elle inclut les ~6 réponses fabriquées par élève, aux `created_at` antidatés, toutes `language='en'`. La corrélation avec l'examen de référence se dégrade sans raison visible, et l'analyse DIF EN/AR compare une population réelle à une population partiellement synthétique. **Le défaut est indétectable a posteriori** — c'est ce qui le rend majeur, pas la taille de l'échantillon.

**Correction proposée** :

- **Court terme, sans migration** : marquer les réponses de seed via un champ déjà libre — il n'y en a pas sur `Response`. À défaut, **isoler les élèves de démo** par une convention d'`external_ref` (`demo:*`) et **exclure explicitement ces `student_id`** dans tous les scripts de `scripts/analysis/`.
- **Propre** : ajouter `Response.origin ENUM('live','seed','simulation') NOT NULL DEFAULT 'live'` (migration 0020). Coût : une colonne, un `server_default` — même pattern que `language` en 0019. Ça rend la population d'analyse **explicitement filtrable**, pour toujours.
- **Immédiat** : passer `language=` explicitement dans les deux scripts, et **ne jamais utiliser `provision_prod_tenant.py` sur le tenant du pilote réel**. Renommer en `provision_demo_tenant.py` si c'est son usage.

---

### MAJ-4 · Le wording `ENRICH` — « beyond {code} expectations » — sera lu comme « hors programme » alors qu'il veut dire « en avance »

**Fichier** : `src/api/views_service.py:64` (`_ALIGNMENT_WORDING_EN[AlignmentType.ENRICH] = "beyond {code} expectations"`)

Dans le pivot confirmé, **8 des 32 lignes CCSS** sont `ENRICH` — et dans **6 cas sur 8** (#4, #11, #17, #18, #19, #23), la raison n'est **pas** que l'exigence est absente du standard : c'est qu'**Atlas la place un grade plus tôt** (règle R3, Divergence 1 : *« le graphe Atlas est ordonné par prérequis cognitifs, pas par grade »*).

Le type `ENRICH` couvre les deux sens (*« avance de grade, **ou** exigence absente du standard »*), mais **le wording n'en rend qu'un**. Un enseignant ou un parent qui lit *« beyond 5.NF.A.1 expectations »* sur `ADD_UNLIKE_LCM` comprendra « hors programme » — alors que le message juste est « **le programme le demande en G5, nous le mesurons dès G4** », ce qui est un **argument**, pas un avertissement.

**Correction proposée** : deux wordings pour un même type, discriminés par une clé du mapping (le pivot a déjà l'information — la `reconciliation_note` cite explicitement R3) :

| Cas | EN | AR |
|---|---|---|
| ENRICH-de-grade (R3/R2) | *« taught earlier than {code} »* | « يُدرَّس قبل {code} » *(à valider linguiste)* |
| ENRICH-d'exigence (ex. #23 CCSS : la réduction n'est pas exigée) | *« beyond {code} expectations »* (inchangé) | « يتجاوز متطلبات {code} » |

Mineur techniquement, **majeur commercialement** : c'est le texte que lit l'acheteur.
*(Lié à `Revue-Pivot-Crosswalk.md` §6 — le didacticien doit voir ce point avec les décisions D3/D4/D5.)*

---

## 3. 🟡 MINEUR

### MIN-1 · Les plages UK sautent les années intermédiaires

`scripts/seed_crosswalk.py:79` et `:106` — `m["uk_nc"]["years"].split("-")`.
Pour `"Y5-Y6"` → `["Y5","Y6"]` ✅. Mais pour **`"Y3-Y5"`** (#13 `WHOLE_AS_FRACTION`) → `["Y3","Y5"]` : **Y4 est silencieusement omis**. La plage est traitée comme une paire de bornes, pas comme un intervalle.
**Correction** : expanser l'intervalle (`range(int(a[1]), int(b[1])+1)`), ou interdire les plages > 2 ans dans le validateur R5 (aujourd'hui `UK_RE = ^Y[1-6](-Y[1-6])?$` accepte `Y1-Y6`). **Choisir l'un des deux — le silence actuel est le pire cas.**

### MIN-2 · L'index `ix_ccm_standard` existe dans la migration, pas dans le modèle

`alembic/versions/0019_curriculum_language.py:126` crée `ix_ccm_standard` ; `src/models/curriculum.py` ne le déclare pas.
Conséquences : (a) les tests applicatifs, qui construisent le schéma via `Base.metadata.create_all`, tournent **sans** cet index ; (b) un futur `alembic revision --autogenerate` proposera de le **supprimer**.
**Correction** : ajouter `Index("ix_ccm_standard", "standard_id")` dans `__table_args__` de `CompetencyCurriculumMap`. *(Le test `test_0019_schema_from_scratch_coherent_avec_les_modeles` compare tables/colonnes/nullabilité et contraintes — il ne compare pas les index côté modèle, d'où le silence.)*

### MIN-3 · La règle R3 du validateur devient un no-op dès qu'une note existe

`scripts/validate_crosswalk.py:133–138` :
```python
if expected and got != expected and not (moe.get("cognitive_note") or "").strip():
    errors.append(...)
```
La réconciliation a posé une `cognitive_note` sur **les 12 mappings** qu'elle a alignés. Une note **non vide** suffit à désarmer la règle — sans qu'elle ait besoin de dire quoi que ce soit de pertinent. Si quelqu'un change un `cognitive_level` MoE demain sur l'une de ces 12 lignes, **R3 ne le verra plus**.
**Correction** : n'accepter l'override que si la note contient un marqueur explicite (`"override:"`) — et vérifier que les 12 notes actuelles, qui documentent un **alignement** et non un override, n'en portent pas.

### MIN-4 · Le type d'alignement de la ligne est appliqué à **tous** les standards cités

`scripts/seed_crosswalk.py:101–109`. #28 `ADD_MIXED` cite `4.NF.B.3c` **et** `5.NF.A.1` → les deux reçoivent `EXACT`. #21 (`years: "Y5-Y6"`, PARTIAL) → **Y5 et Y6 reçoivent PARTIAL**, alors que la note dit que Y5 couvre exactement le cas.
Conséquence : l'enseignant UK verra « covers part of Y5 » sur un standard que la compétence couvre entièrement.
**Correction** : hors périmètre de la v1 — le schéma (`PK (competency_id, standard_id)`) supporte déjà un type **par standard** sans migration. C'est un enrichissement du **pivot**. *(Soumis à l'expert : `Revue-Pivot-Crosswalk.md` §4, question Q2.)*

### MIN-5 · `/admin/curriculum` est ouvert au `PED_ADMIN`, alors que le cadrage B3 disait « console IT »

`src/api/app.py:432–443` — `_require_curriculum_admin_org` accepte `IT_ADMIN`, `PED_ADMIN`, `SUPER_ADMIN`. Le cadrage B3 spécifiait *« Exposé dans la console IT (`/admin/integration` … ou endpoint dédié `/admin/curriculum`) »*.
La docstring justifie l'écart (« réglage d'**affichage pédagogique** — ouvert au ped admin en plus de l'IT admin »), et l'argument tient : choisir son curriculum est une décision pédagogique, pas une décision de sécurité. L'audit log (`curriculum.set_view`) est bien posé.
**Correction** : **aucune sur le code** — mais **acter l'écart** dans le cadrage B3, sinon le prochain lecteur du doc croira à un défaut de RBAC. *(Rappel : le `curriculum_view` est org-wide — un `ped_admin` d'une école bascule le framework de **toute l'organisation**. Si une org a plusieurs écoles avec des programmes différents, c'est un vrai problème — mais D-B3 dit « un framework par tenant en v1 », donc c'est cohérent avec la décision.)*

---

## 4. Ce qui a été cherché — et qui est **propre**

*Dit explicitement, plutôt que gonflé en findings.*

| Angle imposé | Ce que j'ai vérifié | Verdict |
|---|---|---|
| **Non-régression : le payload de la vue ATLAS doit être identique à avant** | `_attach_standard()` (`views_service.py:153-162`) retourne l'entrée **inchangée** quand `crosswalk is None` ; `_curriculum_context()` rend `None` en vue `ATLAS` ; `curriculum_coverage()` rend `None` et `app.py:1451-1453` n'ajoute la clé que si le retour n'est pas `None`. **Le diff `git diff HEAD -- src/api/views_service.py` ne montre aucune clé ajoutée hors de ce garde-fou.** | ✅ **Aucune régression.** Le payload ATLAS est identique champ pour champ. |
| **La langue doit être écrite sur TOUT chemin de création de `Response`** | Un seul point de création dans le moteur : `engine/service.py:139-146`, paramètre `language` (défaut `EN`), **coercition par valeur** `ResponseLanguage(language)` pour les appels passant un `str`. Le chemin API : `session_service.py:186` → `language=session.locale`. Colonne `NOT NULL` + `server_default 'en'` (migration 0019) : **un NULL est impossible**. | ✅ **Aucun chemin sans langue.** *(Deux scripts de seed utilisent le défaut EN implicite — traité en MAJ-3, qui est un problème de **provenance**, pas d'absence de valeur.)* |
| **Isolation tenant : les vues enrichies ne doivent pas fuiter entre organisations** | Les tables ajoutées (`curriculum_standard`, `competency_curriculum_map`) sont des **référentiels globaux** — elles ne contiennent **aucune donnée élève**. `curriculum_view_of_school()` résout l'organisation **depuis la `school_id` du path**, qui est elle-même filtrée en amont par `can_access_school(ctx, school_id)` et `_get_live_school()` (404 sur soft-delete). `_crosswalk_by_code()` ne joint aucune table tenant. `_require_curriculum_admin_org` exige `len(ctx.org_ids) == 1`. | ✅ **Aucune fuite trouvée.** Le crosswalk n'ouvre aucun nouveau chemin de données élève. |
| **Intégrité : migration 0019 vs modèles** | `tests/test_migrations.py::test_0019_schema_from_scratch_coherent_avec_les_modeles` compare, sur base vierge, le schéma **migré** au schéma des **modèles** (`Base.metadata`) : tables, colonnes, nullabilité, PK, FK (+ `ondelete`), UNIQUE, index des objets 0019. Le second test vérifie les `server_default` sur lignes préexistantes **et** la réversibilité (downgrade → re-upgrade). | ✅ **C'est le bon test, et il passe.** *(Seule lacune : les index ne sont pas comparés dans le sens modèle → migration — cf. MIN-2.)* |
| **Enums SQLite vs Postgres** | Pattern correct : sur PG, les 5 types sont créés **explicitement avant** l'`ADD COLUMN` (`checkfirst` en online, bloc `DO … EXCEPTION WHEN duplicate_object` en offline `--sql`), puis référencés en `create_type=False`. `weight_source` (préexistant depuis 0001) est **exclu de `ENUMS`** et donc ni recréé ni droppé. Le fallback SQLite `_enum("weight_source")` → `("expert","empirical")` correspond **exactement** à `WeightSource`. Le downgrade ne drope que les types créés par 0019. | ✅ **Correct.** Le piège connu du projet est bien traité. |
| **Retouche `0003_item_ar_nullable` (`copy_from`)** | La table reproduite par `_item_table()` est **fidèle à 0002** : mêmes 15 colonnes, même FK `fk_item_competency` (`ondelete=RESTRICT`), **et** l'index `ix_item_competency_id` — que la recréation batch SQLite aurait sinon perdu silencieusement. | ✅ **Bonne correction**, et le risque qu'elle adresse (perte d'index en batch mode) est réel. |
| **Retouche `0017_role_linguist`** | Chemin offline ajouté (`ALTER TYPE role ADD VALUE IF NOT EXISTS`), chemin online inchangé (garde d'existence via `pg_enum`, compatible PG < 12). | ✅ Correct. |
| **Idempotence du seed (au sens « ne duplique pas »)** | Double exécution → aucun doublon (clés `(framework, code)` et `(competency_id, standard_id)`). | ✅ Vérifié — **mais insuffisant, cf. CRIT-2** : l'idempotence en **insert** ne vaut pas l'idempotence en **update**. |
| **Invariants de la banque d'items** | Scan des 284 items `active` : **0** item dont l'`answer` AR est absente des options AR · **0** décalage d'index entre la bonne réponse EN et AR · **0** échec de `ar_math_preserved`. | ✅ **La banque est saine sur ces trois axes.** *(Les défauts trouvés sont ailleurs — dans le stem, cf. CRIT-1.)* |
| **Suite de tests** | `441 passed, 1 skipped` — rejouée intégralement le 2026-07-12, working tree inchangé. | ✅ |

**Concurrence / verrouillage `on_response`** : hors périmètre (le fichier `engine/service.py` n'a été modifié que pour le threading de la langue — 6 lignes de diff). Le verrouillage pessimiste et l'ordre déterministe d'acquisition des verrous, hérités de la revue du 2026-07-07, sont intacts.

---

## 5. Ordre de traitement recommandé

| Ordre | Finding | Pourquoi maintenant |
|---|---|---|
| **1** | **CRIT-1** (quarantaine des 5 items) | Des items faux sont **servis**. C'est la seule action qui ne peut pas attendre. |
| **2** | **CRIT-2** (seed upsert) | **Bloque la procédure de clôture du Lot 1.** Sans lui, la signature du didacticien n'atteint jamais la base. |
| **3** | **CRIT-3** (pseudo-code MoE + `covered` mort) | Bloque toute démo crédible sur le marché B2G. À corriger **avant** le premier RDV en vue MoE. |
| **4** | **MAJ-1** (moyenne de cohorte) | Le rapport école est imprimé et diffusé. Un « ✓ couvert » faux est plus dangereux qu'une absence de section. |
| **5** | **MAJ-3** (réponses synthétiques en prod) | À traiter **avant** le provisioning du tenant pilote — après, c'est irréversible (append-only). |
| **6** | **MAJ-2, MAJ-4** | À grouper avec la passe de wording AR de la linguiste (Lot 2). |
| **7** | **MIN-1 → MIN-5** | Dette propre, sans urgence. |

**Sur le commit** : le chantier est verrouillé par CRIT-1 (correctness produit), CRIT-2 (le seed ne propage pas les décisions) et CRIT-3 (ligne rouge écrite du cadrage). Ce sont trois défauts **de conception ou de contrat**, pas des bugs de frappe — ils ne se corrigent pas en relisant le diff. **Une fois les trois traités et la suite reverte, le chantier est committable.**

---

*Revue effectuée en lecture seule. Aucun fichier de `04_code/` n'a été modifié, aucun item n'a été réactivé, aucun `git commit` n'a été effectué. Les scans de banque ont été faits en `SELECT` seul sur `atlas_bank.db`.*
