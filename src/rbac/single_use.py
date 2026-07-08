"""Consommation ATOMIQUE des liens magiques (anti-rejeu, revue sécurité 2026-07-07).

Le code et la doc promettaient des liens « single-use » ; sans état serveur, un lien
intercepté restait rejouable jusqu'à expiration (14 j côté parent !). Ici, le `jti`
du jeton est INSÉRÉ dans `consumed_token` : la contrainte d'unicité (clé primaire)
arbitre la course — le second usage (rejeu, ou deux requêtes concurrentes) lève
IntegrityError et est refusé. Les jetons de SESSION (Bearer) ne passent PAS par ici :
ils sont réutilisables par nature.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.token import ConsumedToken
from src.rbac.auth import parse_single_use_token


class TokenAlreadyUsedError(Exception):
    """Lien magique déjà consommé (rejeu détecté). Volontairement ≠ ValueError :

    l'appelant distingue « jeton invalide » (ValueError → lien cassé/expiré) de
    « jeton rejoué » (401 franc, le lien a déjà servi)."""


def peek_single_use_token(s: Session, token: str, *, purpose: str,
                          now: float = None) -> str:
    """Valide un lien magique SANS le consommer ; retourne user_id.

    LECTURE SEULE (aucune écriture, idempotent) : sert au GET ouvert depuis l'email.
    Les scanners d'emails (Outlook SafeLinks, préchargement) suivent les liens en
    GET — si le GET consommait le jti, 100 % des liens seraient brûlés AVANT le clic
    humain (revue adversariale 2026-07-07). La consommation atomique reste l'affaire
    exclusive de `consume_single_use_token` (POST déclenché par une action humaine).

    NB : deux `peek` concurrents peuvent réussir tous les deux — sans danger : seul
    l'INSERT du jti (contrainte unique) arbitre la course à la consommation.

    - ValueError            : jeton malformé / signature / purpose / expiration ;
    - TokenAlreadyUsedError : jti déjà consommé (rejeu d'un lien déjà servi).
    """
    user_id, jti, _exp = parse_single_use_token(token, purpose=purpose, now=now)
    if s.get(ConsumedToken, jti) is not None:
        raise TokenAlreadyUsedError("lien magique déjà utilisé")
    return user_id


def consume_single_use_token(s: Session, token: str, *, purpose: str,
                             now: float = None) -> str:
    """Valide ET consomme un lien magique ; retourne user_id.

    - ValueError            : jeton malformé / signature / purpose / expiration ;
    - TokenAlreadyUsedError : jti déjà consommé (rejeu).

    La consommation est COMMITÉE immédiatement : le jeton est brûlé même si la suite
    de la connexion échoue — un rejeu ne doit jamais pouvoir réussir.
    """
    user_id, jti, exp = parse_single_use_token(token, purpose=purpose, now=now)
    # tz=utc : fromtimestamp sans tz donnerait l'heure LOCALE naïve — la purge des jti
    # (purge_retention) comparerait alors des époques décalées (convention projet : UTC aware).
    s.add(ConsumedToken(jti=jti, purpose=purpose, user_id=uuid.UUID(user_id),
                        expires_at=datetime.fromtimestamp(exp, tz=timezone.utc)))
    try:
        s.commit()   # INSERT + commit : la contrainte unique arbitre la concurrence
    except IntegrityError:
        s.rollback()
        raise TokenAlreadyUsedError("lien magique déjà utilisé")
    return user_id
