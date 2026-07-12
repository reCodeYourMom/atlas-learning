# Atlas Learning — Brief de Product Design (MVP)

**Version** : 1.0 · **Date** : 2026-06-20 · **Périmètre** : MVP vertical Fractions, marché GCC, SaaS B2B→B2G.
**À lire avec** : `PRD-Atlas-Learning.md` (stratégie, personas, RBAC), `Design-Starter-Inventaire-Ecrans.md` (liste écrans), `DataModel-KnowledgeGraph.md` (formes de données).

---

## 0. Mission du design en une phrase

Rendre **visible et crédible** une chose invisible — la trajectoire d'apprentissage d'un enfant — pour qu'une école GCC la vende aux parents et qu'un régulateur l'approuve. Le design ne décore pas un outil de quiz ; il met en scène une **preuve de progression** et un **diagnostic qui explique pourquoi**.

Le test de réussite du design : un directeur pédagogique regarde l'écran de diagnostic pendant 10 secondes et dit « ça, je peux le montrer aux parents ».

---

## 1. Contexte produit (l'essentiel pour designer)

Atlas mesure en continu la maîtrise d'un élève **compétence par compétence** (grain fin : « additionner des fractions à dénominateurs différents », pas « les fractions »). Un moteur adaptatif ajuste la difficulté en temps réel. Le produit ne contient pas de cours : sa valeur est la **mesure** et sa **restitution**.

Trois choses à intérioriser :
- **L'actif, c'est le diagnostic causal.** Atlas ne dit pas seulement « ton enfant bloque sur X ». Il dit « il bloque sur X *parce que* le prérequis Y n'est pas maîtrisé ». C'est ça qui n'existe nulle part ailleurs. Le design doit en faire son héros.
- **L'acheteur n'est pas l'utilisateur.** L'école (admin pédagogique) achète ; l'enseignant fait vivre l'usage ; le parent est le bénéficiaire qu'on rassure ; l'élève est l'utilisateur final. Quatre regards, quatre besoins.
- **Marché GCC, bilingue arabe/anglais, RTL natif.** Ce n'est pas une localisation tardive : c'est une contrainte de structure dès la première maquette.

---

## 2. Principes de design (la boussole)

1. **Preuve avant décoration.** Chaque écran doit répondre à « qu'est-ce que ça me prouve ? ». Si un élément ne sert pas la compréhension ou la preuve, il dégage.
2. **Honnête sur l'incertitude.** Une maîtrise mesurée (beaucoup de réponses) et une maîtrise *inférée* (déduite par propagation, peu de données) ne s'affichent pas pareil. Jamais de faux score précis. Montrer la confiance.
3. **Crédibilité institutionnelle, pas EdTech enfantine.** L'acheteur est une institution. Bannir le registre « appli pour enfants colorée » sur les écrans adultes (enseignant/admin/parent). L'élève peut être plus chaleureux, jamais infantilisant.
4. **Charge cognitive minimale pour l'enseignant.** Son écran doit répondre à une seule question — « où je concentre mon prochain cours ? » — en un coup d'œil. Zéro correction, zéro fouille.
5. **Bilingue par conception.** Tout composant est pensé EN *et* AR/RTL dès le départ. Un layout qui « marche en anglais et on verra l'arabe après » est un échec.
6. **Apaisant côté élève et parent.** L'évaluation génère de l'anxiété. Le design doit désamorcer : progression valorisée, lacune présentée comme « prochaine étape » et non comme échec.

---

## 3. Les utilisateurs (fiches orientées design)

Pour chaque persona : son contexte d'usage, son appareil probable, son état émotionnel, son « job » principal, et ce que « ça marche » signifie pour lui.

### Élève (≈ 8-12 ans, primaire)
- **Contexte** : en classe ou à la maison, sessions courtes (10-20 min).
- **Appareil** : tablette surtout, parfois desktop école. **Tactile prioritaire.**
- **État émotionnel** : peut être anxieux face à l'évaluation. À ménager.
- **Job** : répondre à des questions, comprendre où il en est sans se sentir jugé.
- **« Ça marche »** : il revient sans qu'on le force, il voit sa progression, il n'a pas peur de se tromper.
- **Implication design** : grandes cibles tactiles, feedback immédiat et bienveillant, zéro jargon, progression visible et motivante. Pas de score brut anxiogène.

### Enseignant (persona de rétention — le plus important pour l'usage)
- **Contexte** : prépare son cours, consulte entre deux classes. Temps très limité.
- **Appareil** : desktop/laptop principalement.
- **État émotionnel** : surchargé, sceptique face aux outils qui ajoutent du travail.
- **Job** : savoir en 30 secondes où sa classe bloque, sur quoi concentrer son cours, sans rien corriger.
- **« Ça marche »** : l'outil lui fait gagner du temps de préparation et l'aide à cibler.
- **Implication design** : tableau de bord scannable, lacunes triées par priorité, action de remédiation à un clic, **diagnostic causal lisible** (son arme pour expliquer aux parents).

### Admin pédagogique (décideur / acheteur)
- **Contexte** : pilotage, reporting familles et régulateur.
- **Appareil** : desktop.
- **État émotionnel** : responsable de la rétention des familles et de la conformité.
- **Job** : voir l'état de l'établissement, sortir des rapports crédibles, provisionner les classes.
- **« Ça marche »** : il a une vue macro fiable et des rapports qu'il peut présenter.
- **Implication design** : agrégations claires (classe, compétence, tendance), export propre, ton institutionnel et sobre.

### Parent (lecture seule, non-spécialiste)
- **Contexte** : à la maison, consulte ponctuellement.
- **Appareil** : mobile surtout. **Mobile-first pour cet écran.**
- **État émotionnel** : projette un rêve (université d'élite), mêlé d'anxiété (« mon enfant est-il on track ? »).
- **Job** : savoir si son enfant est sur la bonne trajectoire et que les lacunes se comblent.
- **« Ça marche »** : il est rassuré, il comprend sans être expert, il voit que l'école agit.
- **Implication design** : ultra-lisible pour un non-spécialiste, trajectoire vers le supérieur mise en avant, ton rassurant, mobile-first.

### Admin IT (rôle infra, minimal)
- **Job** : configurer SSO/sécurité. Gate d'achat.
- **Implication design** : fonctionnel, sobre, pas un chantier de design.

---

## 4. Tonalité émotionnelle par persona

| Persona | Registre | À éviter |
|---|---|---|
| Élève | Encourageant, ludique-sobre, valorisant l'effort | Infantilisant, score-sanction, rouge d'échec |
| Enseignant | Efficace, dense, respectueux de son expertise | Condescendant, surchargé, gadget |
| Admin pédagogique | Institutionnel, fiable, premium | Frivole, sur-coloré |
| Parent | Rassurant, clair, aspirationnel | Jargon technique, alarmiste, score brut |

Règle transverse : une **lacune** se présente toujours comme « prochaine étape à travailler », jamais comme « échec ». Le vocabulaire visuel de l'erreur (rouge vif, croix) est à manier avec une extrême parcimonie, surtout côté élève et parent.

---

## 5. Direction artistique (proposition concrète)

Aucune charte n'existe. Voici une direction défendable pour le contexte GCC institutionnel — à valider/ajuster, mais pas à partir de zéro.

### Parti pris général
**Crédible, calme, premium.** Atlas vend de la confiance et de la trajectoire vers l'élite. Le registre visuel = celui d'un outil de mesure sérieux (pense « instrument », pas « jouet »), réchauffé par des touches d'accomplissement. Surfaces claires, beaucoup de respiration, hiérarchie typographique forte, data lisible.

### Couleur (proposition)
- **Primaire — bleu profond / teal** : confiance, intellect, calme. La couleur de l'institution éducative sérieuse. Sert la navigation, les éléments structurants.
- **Accent — ambre / or** : accomplissement, progression, et résonance culturelle GCC (l'or signale le premium sans ostentation). Réservé aux moments de réussite et aux call-to-action clés. **Un seul focal point coloré par écran.**
- **Neutres** : une échelle de gris chauds pour le texte et les surfaces, généreuse en clair.
- **Sémantique avec prudence** : vert = maîtrisé/positif, ambre = en cours, gris = non encore mesuré. **Éviter le rouge** pour les lacunes côté élève/parent — préférer un « à travailler » neutre ou ambré. Le rouge reste pour les vraies erreurs système.
- À définir : une échelle complète (50→900) par teinte pour les data-viz et les états.

### Typographie (proposition forte)
Le vrai sujet, c'est le **bilingue**. Recommandation : **IBM Plex Sans + IBM Plex Sans Arabic** (famille pensée pour fonctionner en cohérence Latin/Arabe — hauteurs d'x et langage de dessin alignés, ce qui résout le problème n°1 du bilingue). Alternatives crédibles AR : Noto Sans Arabic, Tajawal, Almarai, Cairo.
- Définir une échelle typo claire (titres / corps / data / légendes).
- **L'arabe a besoin de plus de hauteur de ligne** que le latin : ne pas appliquer la même `line-height` aux deux scripts.
- Décider du traitement des **chiffres** : chiffres « arabes occidentaux » (0-9, usuels en maths GCC) vs chiffres « arabes orientaux » (٠١٢٣). En contexte mathématique, souvent 0-9. À trancher avec la linguiste.

### Iconographie
Style outline, trait fin, cohérent. **Les icônes directionnelles se miroitent en RTL** (flèches, progression, chevrons). Éviter toute iconographie culturellement marquée ou inappropriée pour le GCC.

### Imagerie
Sobre. Si imagerie il y a (onboarding, écrans vides), respecter les codes de représentation appropriés au GCC (modestie, diversité régionale). Privilégier l'abstrait/illustratif au photographique pour éviter les faux pas. **Au MVP, l'imagerie n'est pas prioritaire** — la data est le visuel.

### Style de data-visualisation
C'est le cœur visuel d'Atlas. Voir §9. Direction : épuré, lisible, pas de 3D, pas de fioritures. La donnée se lit en un coup d'œil. La confiance (mesuré vs estimé) est encodée visuellement (opacité, hachure, ou indicateur).

---

## 6. Bilingue & RTL (section critique)

À traiter en profondeur, pas en surface. C'est le piège n°1 d'un produit GCC.

### Miroir RTL — ce qui s'inverse
- La **direction de lecture** et donc tout le layout : navigation, alignements, ordre des colonnes.
- Les **icônes directionnelles** (flèches, chevrons, « suivant/précédent », barres de progression qui avancent).
- L'ordre de lecture d'un **parcours/trajectoire** : en RTL, une progression « avance » de droite à gauche.

### Ce qui ne s'inverse PAS
- Les **graphiques de données** quantitatifs (un axe de temps, une échelle) suivent des conventions à décider — ne pas inverser mécaniquement un graphe sans réfléchir à sa lecture.
- Les **nombres** et formules mathématiques (les maths se lisent gauche-droite même en contexte arabe).
- Les **logos**.

### Typographie arabe — points de vigilance
- Police arabe dédiée et bien dessinée (pas un fallback système).
- Hauteur de ligne supérieure au latin.
- Pas d'italique en arabe ; le gras existe mais se comporte différemment.
- Tester le rendu des diacritiques et la justification.

### Méthode
Concevoir **chaque écran en RTL et en LTR** dès la maquette, pas l'un puis l'autre. Avoir un jeu de contenus arabes réels (via la linguiste) pour tester, jamais du faux texte latin retourné.

---

## 7. Accessibilité & sécurité enfant (non négociable)

- **Cible WCAG 2.1 AA** : contrastes, tailles de cibles tactiles (élève sur tablette → grandes cibles), navigation clavier, lecteurs d'écran.
- **Mineurs** : aucune donnée personnelle exposée inutilement à l'écran, pas de mécaniques de rétention manipulatoires (pas de « streak » culpabilisant, pas de pression sociale entre élèves).
- **Anti-anxiété** : pas de chrono visible stressant par défaut, pas de classement public entre élèves, l'erreur n'est jamais punitive visuellement.
- Lisibilité : taille de texte minimale confortable, surtout côté élève et parent non-spécialiste.

---

## 8. Spécifications écran par écran

Pour chaque écran : persona, priorité, objectif, blocs de contenu, données affichées, états, interactions, défi de design. Priorité P0 = prototyper en premier (le flux de démo).

### A. Vue classe enseignant — **P0**
- **Persona** : enseignant.
- **Objectif** : « où concentrer mon prochain cours ? » en un coup d'œil.
- **Blocs** : liste des élèves de la classe ; lacunes agrégées triées par fréquence ; compétences à risque mises en avant ; entrée vers la fiche élève.
- **Données** : maîtrise agrégée par compétence sur la classe, nombre d'élèves concernés par lacune.
- **États** : nominal ; **vide** (classe sans données encore — premier usage, à soigner) ; chargement.
- **Interactions** : trier/filtrer ; cliquer un élève → fiche élève ; déclencher une remédiation de groupe.
- **Défi** : densité sans surcharge. L'enseignant doit comprendre sa classe en 30 secondes.

### B. Fiche élève + diagnostic causal — **P0 (l'écran héros)**
- **Persona** : enseignant (et base du rapport parent).
- **Objectif** : montrer le profil de maîtrise d'un élève ET **pourquoi** il bloque.
- **Blocs** :
  - Profil de maîtrise par compétence (le long de la trajectoire fractions).
  - **Le diagnostic causal** : pour une lacune, la chaîne de prérequis remontée jusqu'à la cause racine. Ex. « bloque sur l'addition à dénominateurs différents → parce que le dénominateur commun → parce que le PPCM ».
  - Distinction visuelle mesuré / estimé (confiance).
  - Action de remédiation ciblée.
- **Données** : ability par compétence + confiance ; graphe de prérequis ; cause racine identifiée.
- **États** : nominal ; élève sans assez de données (tout « estimé », à montrer honnêtement) ; aucune lacune (état positif à valoriser).
- **Interactions** : explorer la chaîne causale ; lancer la remédiation ; basculer AR/EN.
- **Défi** : **c'est ici que se gagne la vente.** Rendre la causalité immédiatement compréhensible pour un non-data-scientist. C'est le plus gros enjeu de design du produit. Voir §9.

### C. Déclenchement remédiation — **P0**
- **Persona** : enseignant.
- **Objectif** : depuis une lacune, lancer/assigner un exercice ciblé.
- **Blocs** : compétence ciblée (ou son prérequis racine) ; aperçu de l'exercice ; assignation.
- **États** : génération en cours ; exercice prêt ; erreur de génération.
- **Défi** : montrer que l'outil *agit*, pas seulement diagnostique. Boucler la promesse.

### D. Session adaptative élève — **P1**
- **Persona** : élève.
- **Objectif** : répondre aux items, ressentir la progression.
- **Blocs** : l'item (énoncé AR ou EN) ; zone de réponse selon format (MCQ / saisie numérique / réponse courte) ; feedback immédiat ; progression de session.
- **Données** : item servi par le moteur, format, langue.
- **États** : item affiché ; réponse soumise (feedback) ; transition ; fin de session.
- **Interactions** : tactile prioritaire, grandes cibles ; bascule langue.
- **Défi** : bienveillance. Le feedback d'erreur ne doit jamais punir. Gérer 3 formats de réponse proprement.

### E. Fin de session élève — **P1**
- **Objectif** : valoriser ce qui a été fait, sans score brut anxiogène.
- **Blocs** : récap des compétences travaillées, progression visible, encouragement.
- **Défi** : motivant sans gamification manipulatoire.

### F. Tableau de bord établissement (admin pédagogique) — **P1**
- **Objectif** : vue macro pour piloter et reporter.
- **Blocs** : agrégats par classe / par compétence ; tendances ; accès export.
- **Données** : agrégations établissement.
- **États** : nominal ; établissement en démarrage (peu de données).
- **Défi** : crédibilité institutionnelle, lisibilité macro.

### G. Gestion classes & licences (admin pédagogique) — **P2**
- **Objectif** : provisionner classes, licences, inviter enseignants/élèves.
- **Défi** : du CRUD propre, sobre. Pas de sophistication.

### H. Export rapport (admin pédagogique) — **P2**
- **Objectif** : sortir un rapport synthétique familles/régulateur.
- **Défi** : un document présentable, conforme au registre institutionnel.

### I. Trajectoire de mon enfant (parent) — **P1, mobile-first**
- **Persona** : parent non-spécialiste.
- **Objectif** : rassurer — « mon enfant est-il on track ? ».
- **Blocs** : positionnement vs attentes du supérieur ; lacunes en cours de comblement ; ton positif.
- **Données** : restitution (percentile / niveau / projection), lecture seule.
- **Défi** : traduire de la mesure complexe en lecture simple et rassurante pour un parent. Mobile d'abord.

### J. SSO / sécurité (admin IT) — **P2**
- **Objectif** : configurer l'authentification. Minimal, fonctionnel.

---

## 9. Le diagnostic causal — la pièce maîtresse de data-viz

C'est l'écran qui justifie tout le projet. Il mérite une réflexion de design dédiée.

**Le problème à résoudre visuellement** : montrer qu'une lacune sur une compétence a une **cause racine** située en amont dans une chaîne de prérequis, de façon qu'un enseignant ou un directeur le comprenne instantanément, sans connaître l'algorithme.

**Matière disponible** : un graphe de prérequis (32 nœuds pour les fractions), chaque compétence ayant un niveau de maîtrise (de « non maîtrisé » à « maîtrisé ») et une confiance. Les arêtes sont typées (prérequis bloquant « HARD » vs corrélation « SOFT ») et pondérées.

**Pistes de design à explorer** (à toi de trancher) :
- Une **chaîne/parcours** lisible de gauche à droite (LTR) / droite à gauche (RTL) : prérequis racine → … → compétence en échec, avec l'état de maîtrise codé par couleur, et la cause racine mise en évidence.
- Un **graphe partiel** centré sur la lacune et ses prérequis directs, plutôt que les 32 nœuds (trop dense).
- Une formulation **en langage naturel** doublant le visuel (« bloque sur X parce que Y »), parce que c'est ce qu'un directeur répétera.

**Contraintes** :
- Lisible par un non-spécialiste.
- Encoder la **confiance** (mesuré vs estimé).
- Fonctionner en AR/RTL.
- Ne pas afficher les 32 nœuds d'un coup — montrer le sous-graphe pertinent.

**Autres data-viz du produit** :
- Le **profil de maîtrise** d'un élève (par compétence le long de la trajectoire).
- Les **agrégats de classe / établissement**.
- La **trajectoire** côté parent (positionnement vs cible supérieur).
Toutes dans le même langage visuel sobre : pas de 3D, pas de surcharge, la confiance toujours visible.

---

## 10. Design system à définir

Le design doit produire les fondations, pas juste des écrans isolés.

### Tokens
- **Couleur** : échelle complète par teinte (primaire, accent, neutres, sémantiques) en 50→900, validée contraste AA. Définir les rôles (texte, surface, bordure, états).
- **Typographie** : échelle (display, titres h1-h3, corps, légende, data) × 2 scripts (latin/arabe) avec line-heights distinctes.
- **Espacement** : échelle cohérente (4/8 px base).
- **Rayons, ombres** : sobres. Pas d'effets lourds.

### Composants cœur (inventaire MVP)
- Carte de compétence (état de maîtrise + confiance).
- Indicateur de maîtrise (la primitive visuelle réutilisée partout).
- Indicateur de confiance (mesuré vs estimé).
- Item de session (3 variantes : MCQ, numérique, réponse courte).
- Ligne d'élève (liste classe).
- Bloc diagnostic causal (le composant héros).
- Carte de lacune + bouton remédiation.
- Sélecteur de langue AR/EN.
- Navigation (qui se miroite en RTL).
- États vides / chargement / erreur (à designer explicitement, pas en dernier).

---

## 11. Livrables attendus de la phase design

Dans l'ordre suggéré (du plus structurant au plus large) :

1. **Direction artistique validée** : moodboard, palette, typographie AR/EN, sur 1-2 écrans clés. Valider la DA avant de dérouler.
2. **Le flux de démo (P0)** prototypé : vue classe → diagnostic causal → remédiation, en haute fidélité, AR *et* EN. C'est le livrable à plus forte valeur (design + pitch).
3. **Design system** : tokens + composants cœur.
4. **Le reste des écrans (P1, P2)** déclinés sur le système.
5. **Spécifications de handoff** pour le dev : tokens, états, comportements RTL, comportements responsive.

---

## 12. Contraintes & hors-périmètre

- **MVP = preuve, pas perfection.** Sauf l'écran de diagnostic causal (P0), qui mérite le plus de soin car c'est l'argument de vente. Le reste : clair et utilisable suffit au MVP.
- **Pas de sur-conception** : pas de design pour des features hors backlog MVP (multi-curriculum, certification — ce sont des phases 2-3).
- **Mobile** : prioritaire pour l'élève (tablette) et le parent (mobile). Desktop pour enseignant et admin. Pas besoin de tout responsive parfait partout au MVP, mais penser les deux contextes.
- **L'API n'est pas figée** : les contrats précis viendront en codant l'Epic 4. Designer sur les formes de données du data model ; rester adaptable sur les payloads exacts.

---

## 13. Questions ouvertes pour le designer

- [ ] Direction artistique : valider/ajuster la proposition bleu-profond + accent or, ou explorer une autre piste crédible GCC.
- [ ] Typographie : confirmer IBM Plex (AR+Latin) ou choisir une autre paire bilingue cohérente.
- [ ] Chiffres : occidentaux (0-9) ou arabes orientaux (٠١٢٣) en contexte mathématique — à trancher avec la linguiste.
- [ ] Forme exacte du diagnostic causal : chaîne, sous-graphe, ou hybride visuel + langage naturel.
- [ ] Niveau de gamification côté élève : où placer le curseur entre motivation et anti-manipulation.
- [ ] Identité de marque Atlas : nom, logo, ton — existe-t-il déjà ou à créer ?
