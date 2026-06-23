"""Inspecte le schéma de la DB DATABASE_URL : tables + types enum natifs (PG).

Usage : python scripts/inspect_schema.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

from src.db import make_engine


def main() -> None:
    engine = make_engine()
    insp = inspect(engine)
    print("tables:", sorted(insp.get_table_names()))
    if engine.dialect.name == "postgresql":
        with engine.connect() as c:
            enums = c.execute(text(
                "SELECT typname FROM pg_type WHERE typtype='e' ORDER BY typname"
            )).scalars().all()
        print("enums natifs PG:", enums)


if __name__ == "__main__":
    main()
