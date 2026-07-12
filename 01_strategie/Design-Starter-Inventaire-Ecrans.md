# Atlas Learning — Design Starter (inventaire d'écrans MVP)

**But** : point de départ pour le product design front. Dérivé des personas, parcours et features du PRD — pour ne pas avoir à les rechasser. À lire avec le PRD (personas/journeys) et le Data Model (formes de données affichées).

## Contraintes de design transverses (valent pour tous les écrans)

- **Bilingue AR / EN avec RTL** dès le MVP. L'arabe impose un layout miroir (RTL), pas juste une traduction. À penser dès les premières maquettes, pas en rattrapage.
- **4 personas = 4 expériences distinctes** (cf. RBAC). Un écran n'est jamais "générique" : il est cadré par le rôle.
- **L'écran héros, c'est le diagnostic causal** (« bloque sur X *parce que* Y »). C'est l'argument de vente. Il mérite le plus de soin visuel.
- **Honnêteté mesuré vs estimé** : quand une compétence est inférée par propagation (confiance basse), l'UI doit le montrer (ex. fourchette, pastille « estimation ») — pas un faux score précis.
- **MVP = preuve, pas léché.** Utilisable et clair prime sur joli. La beauté vient après la validation moteur.

---

## Inventaire d'écrans par persona

### Élève (utilisateur des activités)
1. **Session adaptative** — l'écran central élève. Affiche un item (AR ou EN), recueille la réponse, enchaîne. Doit gérer MCQ / saisie numérique / réponse courte. Feedback immédiat.
2. **Fin de session** — récap léger : ce qui a été travaillé, progression visible (sans jargon Elo). Motivant, pas anxiogène.

### Enseignant (persona de rétention — le plus important pour l'usage)
3. **Vue classe (tableau de bord)** — lacunes prioritaires de SA classe, triées par fréquence. « Où concentrer mon prochain cours ». Zéro correction manuelle.
4. **Fiche élève** — profil de maîtrise par compétence d'un élève, avec le **diagnostic causal** (l'écran héros). C'est ici que l'enseignant voit « bloque sur l'addition à dénominateurs différents parce que le PPCM n'est pas maîtrisé ».
5. **Déclenchement remédiation** — depuis une lacune, assigner/lancer un exercice ciblé.

### Admin pédagogique (persona d'acquisition / décideur)
6. **Tableau de bord établissement** — agrégat par classe / par compétence, tendances. Vue macro pour piloter et pour le reporting familles/régulateur.
7. **Gestion classes & licences** — provisionner classes, affecter licences, inviter enseignants/élèves.
8. **Export rapport** — sortir un rapport synthétique (familles / régulateur).

### Parent (lecture seule)
9. **Trajectoire de mon enfant** — où il se situe vs attentes du supérieur, lacunes en cours de comblement. Lecture seule, rassurant et clair, pensé pour un non-spécialiste.

### Admin IT (rôle infra — minimal)
10. **Écran SSO / sécurité** — config authentification, MFA. Minimal, gate d'achat, pas un chantier de design.

---

## Le parcours qui porte la démo (à prototyper en priorité)

Pour un pitch B2B/B2G, l'enchaînement vendeur est :
**Vue classe enseignant (3)** → on clique sur un élève en difficulté → **Fiche élève + diagnostic causal (4)** → « voilà *pourquoi* il bloque » → **déclenchement remédiation (5)**.

Si tu ne prototypes qu'un seul flux pour commencer, c'est celui-là. C'est lui qui produit le « aha » chez un directeur pédagogique.

---

## Données disponibles pour les écrans (côté back)

Ce que le back peut déjà fournir (ou fournira via le backlog) :
- Par élève × compétence : `ability_elo`, `confidence` (mesuré vs estimé), `n_direct`.
- Agrégations : compétence → strand → matière (pondérées par confiance).
- Restitution : percentile, équivalent niveau, projection trajectoire (couche dédiée, configurable).
- Diagnostic causal : chaîne de prérequis HARD non maîtrisés (la cause racine).
- Le graphe de prérequis lui-même (32 nœuds fractions) — visualisable si utile à l'UI.

Les contrats d'API précis (endpoints, payloads) ne sont **pas encore figés** — ils seront définis en codant l'Epic 4 (T4.3). Pour le design, les *formes de données* ci-dessus suffisent à maquetter. Si tu veux un contrat d'API formel avant de designer, c'est un livrable à demander.

---

## Ce qui n'est PAS encore défini (et que le design va produire ou révéler)

- **Identité visuelle / charte** : aucune direction artistique posée. À créer.
- **États d'écran** : empty states, loading, erreurs, premier lancement (aucune donnée encore).
- **Sitemap / navigation** : l'arborescence exacte entre écrans.
- **Contrat d'API formel** : payloads précis (dérivables du data model, à figer en codant T4.3).

C'est normal : c'est le travail du product design. Le présent dossier te donne le quoi/pourquoi/pour-qui ; le design produit le comment-ça-se-voit.
