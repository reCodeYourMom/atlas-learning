# Atlas Learning — commandes de démo.
#
# `make demo-reset` remet le jeu de démo à zéro entre deux rendez-vous, en une commande.
# Aucune clé d'API n'est requise : la banque et sa version arabe sont déterministes.

PY      ?= .venv/bin/python
ALEMBIC ?= .venv/bin/alembic
DEMO_DB ?= atlas_demo.db

# SQLite par défaut. Pour la démo hébergée, exporter DATABASE_URL vers Postgres.
export DATABASE_URL ?= sqlite:///$(CURDIR)/$(DEMO_DB)

.PHONY: help demo-reset demo-accounts test

help:
	@echo "make demo-reset     — reconstruit tout le jeu de démo (< 60 s)"
	@echo "make demo-accounts  — réaffiche la fiche des comptes sans rien recréer"
	@echo "make test           — suite de tests"

## Reconstruit le jeu de démo de bout en bout.
## Ordre imposé : le référentiel avant la banque, l'arabe avant l'activation
## (promote_to_active exige ar_validated), l'activation avant le seed d'école
## (le seed refuse de tourner sur une banque non servable).
demo-reset:
	@echo "▸ base neuve"
	@rm -f $(DEMO_DB)
	@$(ALEMBIC) upgrade head >/dev/null
	@echo "▸ référentiel (32 compétences, 46 arêtes)"
	@$(PY) scripts/seed_referentiel.py >/dev/null
	@echo "▸ banque déterministe (300 items, math exacte)"
	@$(PY) scripts/generate_bank_deterministic.py >/dev/null
	@echo "▸ version arabe déterministe (aucun appel LLM)"
	@$(PY) scripts/translate_bank_ar_deterministic.py
	@echo "▸ activation de la banque"
	@$(PY) demo/provision_demo.py --bank-only
	@echo "▸ école, 3 classes, 75 élèves, 6 semaines d'historique"
	@$(PY) demo/seed_demo_school.py

demo-accounts:
	@$(PY) - <<'EOF'
	import sys; sys.path.insert(0, ".")
	from sqlalchemy import select
	from src.db import SessionLocal, make_engine
	from src.models.org import AppUser
	with SessionLocal(bind=make_engine()) as s:
	    for u in s.execute(select(AppUser).order_by(AppUser.email)).scalars():
	        print(u.email)
	EOF

test:
	@$(PY) -m pytest -q
