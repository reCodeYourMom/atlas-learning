"""Chargement des variables d'environnement depuis .env (dev).

Importer ce module suffit : `import src.config` charge le .env une fois.
En prod, les variables viennent de l'environnement réel — le .env est optionnel
(load_dotenv n'écrase jamais une variable déjà définie).
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_PATH)  # override=False par défaut : l'env réel prime
