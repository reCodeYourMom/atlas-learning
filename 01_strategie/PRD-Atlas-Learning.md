# Atlas Learning — PRD (MVP : Moteur d'évaluation adaptative K-12 GCC)

**Statut** : Draft
**Auteur** : Nassim
**Date** : 2026-06-20
**Version** : 0.1

---

## TL;DR

Atlas Learning est un moteur d'évaluation adaptative pour le K-12 du GCC, vendu en SaaS aux écoles privées. Il mesure en continu la maîtrise de chaque élève **compétence par compétence**, détecte les lacunes tôt, et restitue le résultat sur une échelle ancrée sur les attentes de l'enseignement supérieur — pour prouver aux parents que leur enfant est sur la trajectoire vers l'université d'élite. L'actif défendable n'est pas le contenu (non produit en interne) : c'est le **moteur de mesure** et sa **couche de restitution / projection de trajectoire**.

---

## Problème

**Le trou noir de visibilité K-12.** Entre la maternelle et les examens d'admission au supérieur (AP, SAT, IGCSE/A-Level, IB), les parents du GCC n'ont aucune mesure objective, standardisée et continue de la trajectoire académique de leur enfant. Les bulletins scolaires ne sont ni comparables entre écoles, ni prédictifs de la performance aux examens qui comptent.

**Qui souffre :**
- **L'école privée** (acheteur B2B) vend des placements universitaires mais manque d'un système de preuve continue pour rassurer/retenir les familles et se différencier dans un marché saturé.
- **Les parents** projettent un rêve d'université d'élite sans instrument pour savoir si l'enfant est *on track*.
- **Le régulateur** (KHDA, ADEK, MoE) pousse l'inspection sur les *student outcomes* mais manque d'outils de mesure granulaire et souveraine.

**Résolu aujourd'hui comment :** tests ponctuels et hétérogènes (CAT4, MAP), bulletins maison non standardisés, ou rien de continu. Aucun outil ne relie mesure granulaire continue → projection de trajectoire supérieur → langage curriculaire de l'école.

**Pourquoi maintenant :** marché du privé GCC en expansion massive (>16 000 nouvelles places à Dubaï en 2024-25, >387 000 élèves dans le privé) ; pression réglementaire croissante sur les outcomes ; stratégies étatiques (Education 33, Vision 2030) qui financent l'outillage de mesure. Espace blanc : PIX ne peut pas s'internationaliser (mandat gouvernemental français).

---

## Objectifs

### Objectifs produit / business
- **North Star MVP** : 3 à 5 écoles privées pilotes signées sur 1 matière (maths primaire), avec usage réel et données de calibration qui s'accumulent.
- **Secondaires** : déclencher ≥1 conversation B2G (KHDA/ADEK/MoE) pour subvention/pilote souverain ; atteindre une banque d'items dont la difficulté se stabilise (signal que le moteur Elo converge).

### Non-objectifs (MVP)
- Pas de production de contenu pédagogique (cours, vidéos).
- Pas de couche multi-curriculum à l'achat (vient en phase 2).
- Pas de certification opposable (phase 3, hook B2G).
- Pas de B2C parents en acquisition directe (le parent est *bénéficiaire* via l'école, pas client payant au MVP).
- Pas d'IRT au démarrage.

---

## Solution proposée

### Vue d'ensemble

Atlas mesure la maîtrise via un **moteur Elo par compétence atomique**. Chaque élève répond à des items ; difficulté de l'item et niveau de l'élève s'ajustent mutuellement à chaque réponse. Le système route l'élève vers des items qui maximisent l'information (difficulté ≈ niveau estimé). Les résultats remontent dans un **dashboard** par élève / classe / établissement, restitués sur une **échelle ancrée trajectoire-supérieur** (percentile + équivalent niveau + projection). Quand une lacune est détectée sur une compétence, une **boucle de remédiation** sert un exercice ciblé (généré par Claude *après* mesure — jamais pour la mesure elle-même).

### Les trois couches (séparation stricte)

1. **Moteur de mesure (cœur, défendable)** — Elo par compétence. S'auto-calibre sur le trafic réel. Migration cible IRT en phase 2 *si* la rigueur devient un argument B2G.
2. **Référentiel de compétences neutre (actif unique)** — graphe de compétences atomisées avec prérequis, indépendant de tout curriculum. C'est l'ADN PIX. Le curriculum n'est qu'une **étiquette** projetée par-dessus (phase 2, via mapping RAG sur documents curriculaires officiels).
3. **Couche de restitution / trajectoire (où vit le marketing)** — traduit le niveau Elo interne en langage client : percentile, équivalent niveau scolaire, bande type « SAT-ready », projection de trajectoire. La crédibilité « université d'élite » vient d'ICI, pas du moteur.

### Modèle de rôles (RBAC — V1)

Distinct des personas. Cette matrice est la base du modèle d'autorisation et de la config SSO. Super admin et admin IT sont des **rôles d'infrastructure** : indispensables (gate d'achat B2B GCC — un SaaS école ne se vend pas sans contrôle IT), mais ils ne pilotent pas la construction de valeur pédagogique. À livrer « suffisant pour passer le gate », pas comme chantier de différenciation.

| Rôle | Périmètre |
|---|---|
| **Super admin** | Accès illimité (Atlas / éditeur). |
| **Admin IT** | SSO, autorisations, sécurité globale. Gate d'achat. |
| **Admin pédagogique** | Gestion des licences dans les classes, curriculums, assignations pédagogiques, analytics établissement. |
| **Enseignant** | Assignations pédagogiques, corrections, analytics de ses classes. |
| **Parent** | Lecture seule : analytics et activités de son enfant (ne réalise aucune activité). |
| **Élève** | Activités pédagogiques. |

### Personas (pilotent la roadmap features)

4 personas-cœur portent les besoins qui décident des features. Les rôles super admin / admin IT existent dans la matrice mais ne sont pas des personas-roadmap (plomberie).

- **Admin pédagogique** — décideur d'usage. Veut piloter licences/classes, voir les analytics agrégés établissement, prouver les outcomes (familles + régulateur). Persona d'**acquisition**.
- **Enseignant** — fait vivre ou mourir l'usage quotidien. Veut voir les lacunes de SA classe sans effort, savoir où concentrer son cours, ne pas crouler sous la correction. Persona de **rétention** — central vu le North Star (usage hebdo réel).
- **Parent** — bénéficiaire en lecture seule. Veut voir la trajectoire de son enfant et les lacunes en cours de comblement. Persona de **preuve / rétention**.
- **Élève** — utilisateur des activités adaptatives.

**Stakeholder (non persona-produit en V1) : le Régulateur** (KHDA / ADEK / MoE). Pas servi par une feature V1 ; ciblé en **phase 2-3** via le reporting outcomes et la certification souveraine. Nommé ici pour ne pas le laisser flotter, mais on ne construit pas pour lui au MVP.

### User journeys

**Admin pédagogique (décideur)**
1. Souscrit Atlas pour une matière (maths primaire), provisionne classes et licences.
2. Lance le diagnostic initial adaptatif sur ses classes.
3. Consulte les analytics établissement : maîtrise par compétence, par classe, lacunes agrégées.
4. Présente aux familles la trajectoire individuelle ; prépare le reporting outcomes.
5. Constate la rétention des familles via preuve continue → renouvelle.

**Enseignant (rétention)**
1. Ouvre sa vue classe : lacunes prioritaires par compétence, sans correction manuelle.
2. Décide où concentrer son heure de cours ; assigne / déclenche la remédiation ciblée.
3. Suit la progression de ses élèves compétence par compétence.

**Parent (lecture seule)**
1. Accède aux analytics de son enfant (résultats + activités réalisées).
2. Voit où l'enfant se situe vs attentes du supérieur et les lacunes en cours de comblement.

**Élève (utilisateur)**
1. Passe une session adaptative ; difficulté ajustée en temps réel.
2. Reçoit un retour immédiat ; en cas de lacune, exercice de remédiation ciblé.
3. Progresse compétence par compétence ; le profil de maîtrise se densifie.

### Fonctionnalités (scope MVP, par priorité)

- **F1 — Référentiel de compétences atomisé (maths primaire)** : graphe compétences + prérequis. Socle de tout.
- **F2 — Moteur Elo par compétence** : mise à jour mutuelle élève/item à chaque réponse ; sélection d'item adaptative.
- **F3 — Banque d'items initiale** : items à difficulté estimée a priori (puis auto-corrigée). Génération Claude + validation humaine + linguiste native AR.
- **F4 — Session de diagnostic / d'entraînement adaptative** : interface élève AR/EN.
- **F5 — Couche de restitution** : percentile + équivalent niveau + projection trajectoire.
- **F6a — Vue analytics établissement (admin pédagogique)** : agrégé école / classe ; lacunes agrégées ; outcomes.
- **F6b — Vue classe actionnable (enseignant)** : lacunes prioritaires de sa classe, zéro correction manuelle, pilotage de la remédiation.
- **F7 — Boucle de remédiation** : exercice ciblé généré post-mesure sur la compétence en lacune ; déclenchable/visible par l'enseignant (pas seulement automatique).
- **F8 — RBAC + SSO + provisioning** : 6 rôles (super admin, admin IT, admin pédagogique, enseignant, parent, élève). Gate d'achat — livré « suffisant pour signer », non sur-investi.

### Out of scope (V1 → renvois)
- Mapping multi-curriculum à l'achat (Common Core / National Curriculum / MoE) → **Phase 2**.
- Migration moteur IRT 1PL/2PL → **Phase 2** (conditionnel B2G).
- Certification opposable → **Phase 3** (hook B2G souverain).
- Matières au-delà des maths primaire → **Phase 2+**.
- Acquisition B2C directe → ultérieur.

---

## Sécurité & Conformité

Marché K-12 GCC = données de mineurs + lois de souveraineté (UAE fédéral, PDPL saoudienne) + achat passant par une DSI/IT qui exige un contrôle auditable. La sécurité est ici un **gate d'achat**, pas un raffinement. Principe de tri : un *deal-breaker* bloque la signature ; un *must-have V1* doit être présent (suffisant, pas parfait) ; un *roadmap* se promet de façon crédible et suffit à signer un pilote.

**Note de reclassement** : SOC 2 type 2 / ISO 27001 sont volontairement classés en **roadmap**, pas en must-have V1. Une certification type 2 demande 6-12 mois ; en faire un prérequis V1 empêche tout lancement. Ce qui signe un pilote = contrôles techniques réels en place + feuille de route crédible + périmètre explicite.

| Catégorie | Item | Pourquoi ce niveau |
|---|---|---|
| 🔴 Deal-breaker | **Résidence des données dans le GCC** (région locale / hébergement souverain) | Données de mineurs + souveraineté UAE/PDPL. Sans résidence locale, certaines écoles/régulateurs ne peuvent légalement pas signer. À trancher dès l'archi. |
| 🔴 Deal-breaker | **Isolation stricte des données par tenant** (école/classe/région) | Limite le blast radius. Une fuite inter-écoles est fatale sur un marché de référence. Design data, pas patch. |
| 🔴 Deal-breaker | **Chiffrement at rest + in transit + gestion des clés/secrets** | Baseline non négociable, éliminatoire en due diligence IT. |
| 🟠 Must-have V1 | **SSO / fédération d'identité + MFA** (admins & enseignants min.) | Gate d'achat. MFA obligatoire comptes admin/enseignant. SSO suffisant pour passer, pas tous les IdP au lancement. |
| 🟠 Must-have V1 | **RBAC granulaire** (6 rôles × classe × établissement) | Déjà F8. À la fois feature et contrôle sécu. |
| 🟠 Must-have V1 | **Journalisation accès & actions** (audit log) | Contrôle auditable exigé. Logs dès V1 ; export SIEM différable. |
| 🟠 Must-have V1 | **Rétention/suppression configurable + DPA prêt** | Données mineurs = rétention stricte. DPA réclamé par la DSI. |
| 🟠 Must-have V1 | **Garde-fous IA** (sorties structurées, permissions minimales, anti-fuite données élèves dans les prompts) | Spécifique produit Claude-based. Aucune donnée perso élève identifiable ne transite dans un prompt LLM. Cadré dès F3 et F7. |
| 🟢 Roadmap | **SOC 2 type 2 / ISO 27001** | Feuille de route + périmètre explicite suffisent au pilote. Certif après traction. |
| 🟢 Roadmap | **Export SIEM, pentests, DevSecOps formalisé** | Réels mais différables. Premier pentest avant scale, pas avant premier pilote. |
| 🟢 Roadmap | **Plan de réponse à incident formalisé + contacts sécu** | Version légère au MVP, formalisation complète au scale. |

**Conséquences d'architecture immédiates :**
- *Résidence* : héberger dans une région cloud du Golfe (AWS Bahreïn/UAE, Azure UAE North, ou cloud souverain local selon l'émirat). Décision **avant** la première ligne d'infra.
- *Garde-fou IA* : règle de conception — la génération d'items (F3) et la remédiation (F7) travaillent sur compétences/réponses **anonymisées**, jamais sur un élève identifiable.
- *Isolation tenant* : intégrée directement dans le schéma data (knowledge graph + données élève), pas ajoutée après coup.

---

## Contraintes & dépendances

### Contraintes
- **Techniques** : stack from-scratch, optimisée GCC dès le départ (aucune dette d'infra). **Hébergement : Oracle Cloud (OCI), région UAE** — choisi pour (a) Always Free tier sans limite de durée → dev en phase 0 sans coût, (b) prix uniforme inter-régions → pas de surprime sur la région GCC, (c) résidence des données UAE pour le pilote école privée. Service moteur en FastAPI, front Next.js, base Postgres.
- **Principe de portabilité (anti-lock-in)** : s'en tenir à des briques standard et portables (Postgres, conteneurs, stockage objet S3-compatible) plutôt qu'à des services propriétaires Oracle exotiques. Objectif : pouvoir migrer vers un cloud souverain national (type Core42) **si et quand** un deal B2G l'exige et le finance, sans réécriture. Core42 = surdimensionné et sans free tier aujourd'hui ; tenu en réserve pour le B2G phase 2-3.
- **Compliance** : résidence des données dans le GCC (deal-breaker, cf. section Sécurité) ; alignement MoE/ADEK/KHDA même pour curricula internationaux ; données mineurs (rétention stricte, DPA) ; garde-fous IA anti-fuite.
- **Ressources** : production « human piloting Claude » ; linguiste native AR disponible pour validation des items.

### Dépendances externes
- Documents curriculaires officiels (pour la couche de mapping, phase 2).
- Linguiste AR (validation items + qualité linguistique).
- Données de cohorte externes (AP/SAT/IGCSE) pour ancrer l'échelle de restitution à terme.

---

## Risques & mitigations

| Risque | Prob. | Impact | Mitigation |
|---|---|---|---|
| Items non calibrés → mesure bruitée | H | H | Elo s'auto-corrige sur trafic ; seuil min de réponses avant de « faire confiance » à un item ; quarantaine des items aberrants |
| Cold start (peu de trafic au lancement) | H | M | Difficulté a priori soignée à la génération ; pilotes concentrés pour densifier vite la donnée |
| Crédibilité « trajectoire » contestée | M | H | Échelle de restitution ancrée sur repères externes ; transparence sur ce qui est mesuré vs projeté |
| Mur réglementaire / souveraineté data | M | H | Clarifier hébergement GCC tôt ; angle B2G comme alliance plutôt qu'obstacle |
| Dispersion (multi-curriculum / multi-matière trop tôt) | M | H | Discipline de scope : 1 matière, 1 référentiel, jusqu'à preuve du moteur |

---

## Métriques de succès

- **Convergence moteur** : la difficulté estimée des items se stabilise après N réponses (signal que l'Elo « tient »).
- **Adoption pilote** : 3-5 écoles avec usage hebdomadaire réel.
- **Valeur perçue école** : l'école présente spontanément les rapports Atlas aux familles / au régulateur.
- **Signal B2G** : ≥1 conversation institutionnelle ouverte.
- **Qualitatif** : un directeur d'école dit « ça m'aide à retenir les parents ».

---

## Open questions

- [ ] Curriculum d'ancrage du socle de calibration : **American / Common Core** (reco) vs British. À confirmer.
- [x] ~~Région d'hébergement Golfe~~ → **Tranché : Oracle Cloud (OCI) région UAE**, briques portables pour garder la porte B2G ouverte (cf. Contraintes).
- [ ] Profondeur du diagnostic initial (nb de compétences couvertes au lancement maths primaire).
- [ ] Forme exacte de la « projection de trajectoire » dans la restitution (percentile seul vs projection modélisée).
