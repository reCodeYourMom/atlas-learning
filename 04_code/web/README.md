# Atlas Learning — Front (Next.js)

Front bilingue **AR / EN avec RTL natif** pour les 4 personas (élève, enseignant, admin pédagogique, parent) + admin IT. Branché sur l'API FastAPI (`../src/api/app.py`).

## Stack
- **Next.js 14** (App Router) · TypeScript · Tailwind CSS
- **IBM Plex Sans + IBM Plex Sans Arabic** (paire bilingue cohérente, `line-height` distincte par script)
- **Recharts** pour la data-viz d'agrégat
- Auth par jeton Bearer (localStorage), proxy `/api/*` → FastAPI (pas de CORS en prod)

## Démarrer (dev)

Backend (depuis `04_code/`) :
```bash
export DATABASE_URL="sqlite:///$(pwd)/atlas_demo.db"   # base de démo (make demo-reset)
.venv/bin/python -m uvicorn src.api.app:app --port 8000
```

Front (depuis `04_code/web/`) :
```bash
npm install
npm run dev          # http://localhost:3000
```

### Comptes démo

Plus de mot de passe ni de MFA applicatifs (migration `0013_drop_direct_auth`, MFA déléguée à
l'IdP). En local, deux façons d'ouvrir une session sur un compte existant :

- `OIDC_DEV_LOGIN=1` côté API → `POST /dev/login {"email": …}` (simulateur SSO, dev/tests) ;
- `DEMO_LOGIN_PASSWORD=…` côté API → formulaire de la page `/login` (mode démo ; code dans `demo/login.py`, absent de l'image de production).

Les comptes du jeu de démo (`make demo-reset` dans `04_code/`) : `director@alnoor.demo`,
`teacher.{a,b,c}@alnoor.demo`, `student001..075@alnoor.demo`, `parent@alnoor.demo`,
`it.admin@alnoor.demo`, `linguist@alnoor.demo` — voir `demo/README.md` §5.

## Écrans (10, par persona)
| # | Écran | Route | Persona | Priorité |
|---|---|---|---|---|
| A | Vue classe | `/teacher/[classroomId]` | enseignant | P0 |
| B | **Fiche élève + diagnostic causal** (héros) | `/teacher/[classroomId]/s/[studentId]` | enseignant | P0 |
| C | Remédiation | (modal sur la fiche) | enseignant | P0 |
| D | Session adaptative | `/student` | élève | P1 |
| E | Fin de session | (état de `/student`) | élève | P1 |
| F | Tableau de bord établissement | `/admin/[schoolId]` | admin péda | P1 |
| G | Classes & licences | `/admin/[schoolId]/classes` | admin péda | P2 |
| H | Export rapport | `/admin/[schoolId]/report` | admin péda | P2 |
| I | Trajectoire (mobile-first) | `/parent/[studentId]` | parent | P1 |
| J | Sécurité / SSO | `/it` | admin IT | P2 |

Le **parcours de démo P0** : vue classe → on clique un élève → diagnostic causal (« bloque sur X *parce que* Y ») → remédiation ciblée. C'est lui qui produit le « aha ».

## Principes de design respectés (cf. `01_strategie/Brief-Product-Design.md`)
- **Diagnostic causal = héros** : chaîne racine → lacune, lue dans le sens de lecture (miroir RTL), doublée d'une phrase en langage naturel.
- **Honnête sur l'incertitude** : mesuré vs estimé encodé visuellement (hachure + fourchette), jamais de faux score précis.
- **Pas de rouge pour les lacunes** côté élève/parent : « prochaine étape » ambrée.
- **Bilingue par conception** : bascule AR/EN instantanée, `dir` sur `<html>`, chiffres occidentaux (`.num` reste LTR même en page RTL), maths jamais inversées.

## Architecture
```
app/                 routes (App Router) — un dossier par écran
components/           UI kit + composants domaine (Mastery, DiagnosisBlock, RestitutionCard…)
  LanguageProvider    contexte langue + RTL (garde-fou anti double-montage StrictMode)
lib/
  api.ts              client typé (proxy /api/*)
  types.ts            types alignés sur les payloads FastAPI
  i18n.ts             dictionnaire EN/AR
  mastery.ts          primitives de maîtrise (états, couleurs, ancrage Elo→niveau)
```

## Endpoints consommés
`/login` · `/me` · `/classrooms/{id}/gaps` · `/classrooms/{id}/students` ·
`/students/{id}/profile` · `/students/{id}/trajectory` · `/remediation/preview` ·
`/schools/{id}/overview` · `/sessions` (+ `next-item`, `responses`).
