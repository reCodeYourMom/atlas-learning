"""Affiche le code TOTP courant d'un utilisateur (dépannage démo, sans authenticator).

Usage : python scripts/mfa.py <user_id_ou_email>
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.models.org import AppUser
from src.rbac.auth import totp_now

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/mfa.py <user_id_ou_email>"); sys.exit(1)
    arg = sys.argv[1]
    with SessionLocal(bind=make_engine()) as s:
        try:
            user = s.get(AppUser, uuid.UUID(arg))
        except ValueError:
            user = s.execute(select(AppUser).where(AppUser.email == arg)).scalar_one_or_none()
        if user is None:
            print(f"utilisateur introuvable : {arg}"); sys.exit(1)
        if not user.totp_secret:
            print(f"{user.email} n'a pas de secret TOTP (MFA non enrôlé)"); sys.exit(1)
        print(totp_now(user.totp_secret))
