# Backend FastAPI — image prod. Contexte de build = 04_code/ (racine du backend).
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances système minimales (psycopg[binary] embarque libpq, donc rien de lourd).
RUN apt-get update && apt-get install -y --no-install-recommends curl tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Code applicatif (src + migrations + scripts de provision).
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts
# Le référentiel de compétences, lu par seed_referentiel.py (data/referentiel_fractions.json).
# Sans lui, le seed échoue dans le conteneur : la base démarre vide et rien n'est servable.
COPY data ./data
COPY deploy/prod/entrypoint-backend.sh /usr/local/bin/entrypoint-backend.sh
RUN chmod +x /usr/local/bin/entrypoint-backend.sh

# Utilisateur non-root (durcissement prod).
RUN useradd -m -u 10001 atlas && chown -R atlas:atlas /app
USER atlas

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/auth/providers >/dev/null || exit 1

# tini = init PID 1 (reaping correct des process). Entrypoint = migrations + uvicorn.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint-backend.sh"]

# Cible `demo` (demo/deploy/docker-compose.yml) : la même image + le dossier demo/ — semis de
# l'école de démo et connexion par mot de passe partagé (/demo/login).
FROM base AS demo
COPY --chown=atlas:atlas demo ./demo

# Cible par défaut (dernière étape) : l'image de production NE CONTIENT PAS demo/. La route
# /demo/login n'y existe donc pas — elle n'est pas seulement désactivée.
FROM base AS prod
