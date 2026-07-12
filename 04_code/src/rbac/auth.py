"""Jetons de session signés (Epic 6, T6.3) — SSO uniquement, plus de comptes directs.

Depuis la revue sécurité DSI, l'authentification passe EXCLUSIVEMENT par l'IdP (OIDC,
`src/rbac/oidc.py`) : plus de mot de passe, plus de MFA TOTP applicatif (la MFA est
portée par l'IdP). Ce module ne garde que les jetons signés HMAC qui matérialisent une
session applicative (et les liens magiques parent / super-admin, voir l'API).

Le `purpose` cloisonne les jetons : un lien magique parent ne peut pas servir d'accès admin.

Deux familles de jetons :
  - jetons de SESSION (`make_token`) : réutilisables par nature (Bearer à chaque requête) ;
  - jetons de LIEN MAGIQUE (`make_single_use_token`) : portent un `jti` aléatoire, consommé
    UNE seule fois côté serveur (table `consumed_token`, cf. `src/rbac/single_use.py`) —
    un lien intercepté n'est plus rejouable après le premier usage.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Optional, Tuple

_DEV_SECRET = "dev-insecure-secret"


def _secret() -> bytes:
    val = os.environ.get("AUTH_SECRET")
    if not val:
        # Fail-fast en prod : un secret par défaut rend les jetons forgeables.
        if os.environ.get("ATLAS_ENV", "dev").lower() in ("prod", "production"):
            raise RuntimeError("AUTH_SECRET doit être défini en production")
        val = _DEV_SECRET
    return val.encode()


def _sign(payload: bytes) -> str:
    body = urlsafe_b64encode(payload).decode()
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def make_token(user_id: str, *, purpose: str = "session", ttl_s: int = 3600,
               now: float = None) -> str:
    now = int(now if now is not None else time.time())
    return _sign(f"{user_id}:{purpose}:{now + ttl_s}".encode())


def make_single_use_token(user_id: str, *, purpose: str, ttl_s: int,
                          now: float = None) -> str:
    """Jeton de LIEN MAGIQUE : comme `make_token`, plus un `jti` aléatoire (anti-rejeu).

    Le `jti` est consommé atomiquement à l'usage (cf. `src/rbac/single_use.py`) : le lien
    devient réellement « single-use », même intercepté avant son expiration.
    """
    now = int(now if now is not None else time.time())
    jti = secrets.token_urlsafe(16)
    return _sign(f"{user_id}:{purpose}:{now + ttl_s}:{jti}".encode())


def _parse(token: str, *, purpose: str, now: float = None) -> Tuple[str, Optional[str], int]:
    """(user_id, jti | None, exp) si signature/purpose/expiration valides ; sinon ValueError."""
    try:
        body, sig = token.split(".", 1)
    except (ValueError, AttributeError):
        raise ValueError("jeton malformé")
    expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected, sig):
        raise ValueError("signature invalide")
    payload = urlsafe_b64decode(body).decode()
    # 4 champs (le 3e est l'exp numérique) = jeton single-use ; sinon jeton de session.
    parts = payload.rsplit(":", 3)
    if len(parts) == 4 and parts[2].isdigit():
        user_id, tok_purpose, exp, jti = parts
    else:
        user_id, tok_purpose, exp = payload.rsplit(":", 2)
        jti = None
    if not hmac.compare_digest(tok_purpose, purpose):
        raise ValueError("usage de jeton invalide")
    if int(exp) < int(now if now is not None else time.time()):
        raise ValueError("jeton expiré")
    return user_id, jti, int(exp)


def parse_token(token: str, *, purpose: str = "session", now: float = None) -> str:
    """Retourne user_id si le jeton est valide, du bon `purpose` et non expiré ; sinon ValueError.

    Le `purpose` cloisonne les jetons : un lien magique parent ne peut pas servir à accéder
    aux endpoints de session, et inversement. NE consomme PAS le `jti` : les liens magiques
    doivent passer par `single_use.consume_single_use_token` (anti-rejeu).
    """
    user_id, _jti, _exp = _parse(token, purpose=purpose, now=now)
    return user_id


def parse_single_use_token(token: str, *, purpose: str,
                           now: float = None) -> Tuple[str, str, int]:
    """(user_id, jti, exp) d'un jeton single-use valide ; ValueError sinon.

    Refuse un jeton SANS `jti` : un jeton de session ne peut pas se faire passer
    pour un lien magique.
    """
    user_id, jti, exp = _parse(token, purpose=purpose, now=now)
    if jti is None:
        raise ValueError("jeton sans jti (pas un lien magique)")
    return user_id, jti, exp
