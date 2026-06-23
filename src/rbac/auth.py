"""Jetons de session signés (Epic 6, T6.3) — SSO uniquement, plus de comptes directs.

Depuis la revue sécurité DSI, l'authentification passe EXCLUSIVEMENT par l'IdP (OIDC,
`src/rbac/oidc.py`) : plus de mot de passe, plus de MFA TOTP applicatif (la MFA est
portée par l'IdP). Ce module ne garde que les jetons signés HMAC qui matérialisent une
session applicative (et les liens magiques parent / super-admin, voir l'API).

Le `purpose` cloisonne les jetons : un lien magique parent ne peut pas servir d'accès admin.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

_DEV_SECRET = "dev-insecure-secret"


def _secret() -> bytes:
    val = os.environ.get("AUTH_SECRET")
    if not val:
        # Fail-fast en prod : un secret par défaut rend les jetons forgeables.
        if os.environ.get("ATLAS_ENV", "dev").lower() in ("prod", "production"):
            raise RuntimeError("AUTH_SECRET doit être défini en production")
        val = _DEV_SECRET
    return val.encode()


def make_token(user_id: str, *, purpose: str = "session", ttl_s: int = 3600,
               now: float = None) -> str:
    now = int(now if now is not None else time.time())
    payload = f"{user_id}:{purpose}:{now + ttl_s}".encode()
    body = urlsafe_b64encode(payload).decode()
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def parse_token(token: str, *, purpose: str = "session", now: float = None) -> str:
    """Retourne user_id si le jeton est valide, du bon `purpose` et non expiré ; sinon ValueError.

    Le `purpose` cloisonne les jetons : un lien magique parent ne peut pas servir à accéder
    aux endpoints de session, et inversement.
    """
    try:
        body, sig = token.split(".", 1)
    except (ValueError, AttributeError):
        raise ValueError("jeton malformé")
    expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected, sig):
        raise ValueError("signature invalide")
    user_id, tok_purpose, exp = urlsafe_b64decode(body).decode().rsplit(":", 2)
    if not hmac.compare_digest(tok_purpose, purpose):
        raise ValueError("usage de jeton invalide")
    if int(exp) < int(now if now is not None else time.time()):
        raise ValueError("jeton expiré")
    return user_id
