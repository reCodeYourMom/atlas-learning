# Atlas Learning

Atlas Learning is a competency-based adaptive assessment platform for K-12 math. Instead of scoring a test, it measures a student's mastery of individual, fine-grained skills and explains *why* they're stuck — "blocked on X because prerequisite Y isn't mastered yet" — rather than just reporting a percentage.

The current build covers a full vertical: **fractions (grades 2–5, 32 micro-skills)**, bilingual **Arabic/English with native RTL support**.

## How it works

The system is split into three independent layers:

1. **Measurement engine** — an Elo-based adaptive engine estimates mastery per skill from student responses, and propagates confidence across a prerequisite graph (skill A depends on skill B). The engine is subject-agnostic: difficulty and content are pluggable, so the same core could drive a different subject vertical.
2. **Competency graph** — a neutral, curriculum-independent skill graph (DAG, cycle-validated) with weighted HARD/SOFT prerequisite edges. Curriculum frameworks (e.g. national standards) map onto this graph rather than defining it, so the measurement stays valid across curricula.
3. **Reporting & diagnosis** — turns raw mastery estimates into a trajectory and a causal diagnosis, surfaced through role-specific dashboards (see below).

## Features

- **Adaptive sessions** — skill selection and stopping rules driven by measurement confidence, server-side scoring.
- **Causal diagnosis & remediation** — pinpoints the actual blocking prerequisite behind a weak skill, not just "needs practice."
- **Item bank pipeline** — deterministic item generation with exact math validation, LLM-assisted difficulty calibration, an Arabic translation pipeline with automated fidelity gates, and a human review/quarantine workflow for anything that fails validation.
- **Bilingual by design** — Arabic/English content and UI, native RTL layout, not a bolt-on translation layer.
- **Role-based dashboards** — student, teacher (classroom gaps view), academic admin (school-wide report), parent, and IT admin, each scoped through server-verified RBAC (6 tenant roles plus 2 global Atlas staff roles: linguist and content reviewer) with tenant isolation.
- **Roster integrations** — Google Workspace / Classroom, OneRoster (API and CSV), and a generic directory sync, so schools don't have to hand-manage rosters.
- **Multi-tenant foundation** — org → school → classroom → student hierarchy, append-only audit logging, and lifecycle management for student data (retention, deletion, holds).
- **Auth** — OIDC SSO only (MFA is delegated to the identity provider), plus single-use magic links for parents and Atlas staff.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic. Postgres in production, SQLite for dev/CI.
- **Frontend**: Next.js 14 (`web/`), TypeScript, Tailwind, Recharts.
- **Deployment**: Docker Compose (Caddy for TLS, Keycloak for auth), with a Terraform module for cloud provisioning.
- **CI**: GitHub Actions — full test suite against a real Postgres service, including a migration round-trip check (upgrade → downgrade → upgrade).

## Repository layout

```
src/             The backend (FastAPI)
  api/             HTTP endpoints, session and dashboard services
  engine/          Elo update, confidence, propagation, adaptive selection, stopping rules
  graph/           DAG validation for the competency graph
  items/           Item generation, difficulty, Arabic pipeline, review/quarantine
  restitution/     Aggregation, scaling, causal diagnosis, remediation
  rbac/            Auth (OIDC, magic links) and role-based authorization
  rostering/       Google / OneRoster / CSV directory sync
  models/          SQLAlchemy models
  compliance/ licensing/ onboarding/ notify/ llm/
web/             The frontend (Next.js — student, teacher, admin, parent, IT admin)
data/            Competency framework and curriculum crosswalk, as JSON
alembic/         Database migrations
scripts/         Seeding, bank generation/translation/validation, ops CLIs, pilot analyses
tests/           Test suite
deploy/          Production: Docker Compose + Keycloak (prod/), Terraform (infra/)
demo/            Everything that exists only for the sales demo
```

### App vs. demo

The product and the sales demo share one codebase (`src/`, `web/`). What is demo-only lives in `demo/`: the demo school seed, bank activation, the shared-password login (`POST /demo/login`) and its own Docker stack (one subdomain, no Keycloak). The app never depends on that folder — the production image does not ship it, so the demo login route does not exist there. See `demo/README.md`.

## Running it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
make test                                      # run the test suite
make demo-reset                                # build the demo dataset (SQLite, < 60 s, no API key)
DATABASE_URL=sqlite:///$PWD/atlas_demo.db DEMO_LOGIN_PASSWORD=demo \
  .venv/bin/python -m uvicorn src.api.app:app --port 8000   # API
cd web && npm install && npm run dev           # frontend, on :3000
```

For Postgres, set `DATABASE_URL=postgresql+psycopg://…` and run `.venv/bin/alembic upgrade head`. See `deploy/prod/` for the self-hosted production stack.

## Status

The full backlog behind this vertical is implemented and covered by tests (485 passing, 1 skipped). The engine, item bank, adaptive session flow, reporting/diagnosis, RBAC, and roster integrations all run end-to-end against a demo dataset. Current work is focused on frontend polish and pilot readiness (extending the item bank to more skills, real-cohort calibration).

The architecture (pluggable subject difficulty, curriculum-agnostic competency graph) is designed to extend beyond fractions.
