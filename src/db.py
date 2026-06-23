"""Connexion DB centralisée.

Prod : Postgres (Oracle UAE) via DATABASE_URL.
Dev / CI : SQLite fichier par défaut (aucune dépendance serveur).

Une seule source de vérité pour l'URL : Alembic et le seed la lisent ici.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import Select

# SQLite fichier local par défaut (dans 04_code/), surchargé en prod par DATABASE_URL.
_DEFAULT_SQLITE = f"sqlite:///{Path(__file__).resolve().parents[1] / 'atlas_dev.db'}"


def get_database_url() -> str:
    import src.config  # noqa: F401  charge le .env (DATABASE_URL optionnel)

    return os.environ.get("DATABASE_URL", _DEFAULT_SQLITE)


def make_engine(url: str | None = None) -> Engine:
    engine = create_engine(url or get_database_url(), future=True)
    if engine.dialect.name == "sqlite":
        # SQLite désactive les FK par défaut : on les active pour que
        # ON DELETE CASCADE/RESTRICT s'appliquent comme en Postgres.
        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_conn, _rec):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


SessionLocal = sessionmaker(class_=Session, expire_on_commit=False)


def active(model) -> Select:  # noqa: ANN001
    """`select(model)` filtré sur les lignes vivantes (soft delete).

    Requête « par défaut » : ne retourne jamais les lignes `deleted_at IS NOT NULL`.
    Les modèles sans colonne `deleted_at` sont renvoyés sans filtre.
    """
    stmt = select(model)
    deleted_at = getattr(model, "deleted_at", None)
    if deleted_at is not None:
        stmt = stmt.where(deleted_at.is_(None))
    return stmt
