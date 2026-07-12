# Architecture « matière pluggable » — réplicabilité au scaling

**Statut** : actif · **Date** : 2026-06-21
**But** : garantir qu'ajouter une matière (sciences, langue arabe, anglais…) ne touche
PAS le cœur du moteur. Les maths/fractions sont la 1ʳᵉ implémentation, pas un cas particulier figé.

## Principe : séparer la machinerie du savoir-métier

Tout objet d'évaluation adaptatif a besoin, par item, d'une **difficulté** et de
**features de contexte**. La façon de les calculer est propre à la matière ; la façon
de les exploiter ne l'est pas.

```
GÉNÉRIQUE (partagé, jamais dupliqué)            SPÉCIFIQUE MATIÈRE (1 module / matière)
──────────────────────────────────             ───────────────────────────────────────
src/items/difficulty.py                         src/items/deterministic.py (= matière "fractions")
  difficulty_from_score(base, complexity)         GENERATORS        : génère le contenu exact
  weighted_score(features, weights)               fraction_features : content → context_tags
src/models/item.py (Item, ItemContent)            fraction_complexity(features) → [0,1]
src/items/review.py (workflow, états)             FRACTION_FEATURE_WEIGHTS
src/items/quarantine.py (dérive, pool)          03_referentiel/* (graphe de la matière)
moteur Elo (Epic 3)
```

## Le contrat d'une nouvelle matière

Pour brancher une matière, fournir **trois** choses — rien d'autre :

1. **Générateurs de contenu** — produisent des items `{stem, options, answer}` corrects.
   (Déterministe quand c'est possible = correction garantie ; LLM possible pour l'habillage,
   jamais pour la vérité de la réponse.)
2. **Extracteur de features** `features(content) -> dict` — des `context_tags` porteurs de
   sens, propres à la matière (ex. fractions : `needs_lcm`, `simplify_required`,
   `max_denominator` ; sciences : `n_steps`, `requires_unit_conversion` ; langue :
   `vocab_level`, `clause_depth`).
3. **Fonction de complexité** `complexity(features) -> [0,1]` — combine les features
   normalisées (via `weighted_score` + un dict de poids = le savoir-métier).

La couche générique fait le reste :
`difficulty_prior = difficulty_from_score(competency_prior, complexity)`
borné à ± `BAND` autour du prior de la compétence. Le moteur Elo (Epic 3) affine ensuite
`difficulty_elo` avec le trafic réel — identiquement pour toutes les matières.

## Ce qui NE change jamais d'une matière à l'autre

- Le modèle `Item` (content JSONB bilingue, `context_tags` JSONB, `difficulty_prior`/`elo`).
- Le workflow de revue/validation AR/quarantaine (statuts, transitions, garde-fous).
- La sélection d'item (`active_pool`) et le moteur Elo + propagation par prérequis.
- L'échelle de difficulté et son interprétation.

## Pourquoi c'est cohérent avec « objet adaptatif »

L'adaptativité **intra-compétence** exige des items de difficultés VARIÉES et CONNUES au
sein d'une même compétence (sinon le sélecteur n'a rien pour ajuster au niveau de l'élève).
La difficulté par item — issue de features structurelles, pas d'un prior plat — fournit
exactement ce signal, dès le démarrage à froid, avant même la première réponse.
L'adaptativité **inter-compétences** vient du graphe de prérequis + Elo (Epic 3).

Référence d'implémentation : `src/items/difficulty.py` (générique),
`src/items/deterministic.py` (matière fractions), `tests/test_difficulty.py`
(prouve la neutralité matière), `tests/test_deterministic.py`
(prouve la variation intra-compétence + correction math).
```
