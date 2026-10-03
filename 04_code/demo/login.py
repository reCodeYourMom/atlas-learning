"""Connexion DÉMO : un mot de passe partagé, hors production.

L'auth du produit est SSO uniquement (migration 0013_drop_direct_auth) : plus aucun mot
de passe en base, la MFA est portée par l'IdP. Excellent en production — impraticable
pour une démo commerciale, où il faut ouvrir cinq comptes en visio sans monter un
Keycloak et sans exposer un endpoint curl.

D'où ce mode explicite : UN secret partagé, lu dans l'environnement (jamais en base,
jamais versionné), qui ouvre une session sur un compte EXISTANT du jeu de démo. Quatre
verrous : ce module doit être présent (l'image de production ne contient pas demo/),
`DEMO_LOGIN_PASSWORD` doit être posé, `ATLAS_ENV` ne doit pas être une prod, et l'email
doit déjà exister. Comparaison à temps constant, et journalisation de chaque tentative —
un mot de passe partagé reste un mot de passe.

Branché par `src/api/app.py` via `install(app, get_db)`.
"""
from __future__ import annotations

import hmac
import os
import time
from typing import Callable, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.audit import log_action
from src.models.org import AppUser
from src.rbac.auth import make_token


def password() -> Optional[str]:
    """Le secret partagé, ou None si la connexion de démo est fermée."""
    is_prod = os.environ.get("ATLAS_ENV", "dev").lower() in ("prod", "production")
    pwd = os.environ.get("DEMO_LOGIN_PASSWORD") or ""
    return None if (is_prod or not pwd) else pwd


class DemoLoginIn(BaseModel):
    email: str
    password: str


# Anti-bruteforce du mot de passe partagé : N échecs par clé (IP, puis email) dans une
# fenêtre glissante → 429. En mémoire de processus : suffisant pour la stack de démo
# (un seul backend), volontairement sans dépendance. Un succès remet le compteur à zéro.
MAX_FAILURES = 10
WINDOW_S = 600
_failures: dict = {}


def _throttled(key: str, *, now: Optional[float] = None) -> bool:
    now = now if now is not None else time.time()
    hits = [t_ for t_ in _failures.get(key, ()) if now - t_ < WINDOW_S]
    _failures[key] = hits
    return len(hits) >= MAX_FAILURES


def _record_failure(key: str, *, now: Optional[float] = None) -> None:
    now = now if now is not None else time.time()
    _failures.setdefault(key, []).append(now)


def _clear(key: str) -> None:
    _failures.pop(key, None)


def install(app: FastAPI, get_db: Callable) -> None:
    """Enregistre POST /demo/login sur l'app (get_db = la dépendance de session de l'API)."""

    @app.post("/demo/login")
    def demo_login(body: DemoLoginIn, request: Request, s: Session = Depends(get_db)):
        """Connexion de démonstration : email d'un compte de démo + mot de passe partagé."""
        expected = password()
        if expected is None:
            raise HTTPException(status_code=404, detail="indisponible")
        email = body.email.strip().lower()
        client_ip = request.client.host if request.client else "?"
        keys = (f"ip:{client_ip}", f"email:{email}")
        if any(_throttled(k) for k in keys):
            log_action(s, action="auth.demo_login_throttled", details={"email": email, "ip": client_ip})
            s.commit()
            raise HTTPException(status_code=429, detail="trop de tentatives, réessayer plus tard")
        user = s.execute(
            select(AppUser).where(AppUser.email == email, AppUser.deleted_at.is_(None))
        ).scalar_one_or_none()
        # compare_digest : le temps de réponse ne doit pas dépendre du préfixe correct.
        ok = hmac.compare_digest(body.password or "", expected)
        if user is None or not user.is_active or not ok:
            # Message unique : ne dit jamais si c'est l'email ou le mot de passe qui est faux.
            for k in keys:
                _record_failure(k)
            log_action(s, action="auth.demo_login_failed", details={"email": email, "ip": client_ip})
            s.commit()
            raise HTTPException(status_code=401, detail="identifiants invalides")
        for k in keys:
            _clear(k)
        log_action(s, action="auth.demo_login", user_id=user.id)
        s.commit()
        return {"token": make_token(str(user.id)), "user_id": str(user.id)}
