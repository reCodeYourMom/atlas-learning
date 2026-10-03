"""Onboarding self-service d'un tenant (Phase C) — logique pure, testable sans HTTP.

Pré-condition CRITIQUE : l'appelant a DÉJÀ vérifié que l'utilisateur est admin Workspace
(via Directory `users/me`). Ce module ne fait que matérialiser le tenant ; il ne décide
PAS qui a le droit (sinon : escalade de privilège — `hd` ne prouve que l'appartenance).

Crée/retrouve l'Organisation par domaine, garantit le compte IT_ADMIN « bootstrap »
(sans external_ref → jamais désactivé par le rostering) et l'intégration Google (pending).
Idempotent : ré-onboarder le même domaine ne duplique rien ; un 2ᵉ admin réel s'ajoute.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.base import Role
from src.models.measurement import School
from src.models.org import AppUser, Membership, Organization, TenantIntegration


@dataclass
class OnboardResult:
    organization: Organization
    user: AppUser
    created: bool          # True si le tenant vient d'être créé


def onboard_tenant(s: Session, *, email: str, domain: str,
                   customer_id: Optional[str] = None,
                   org_name: Optional[str] = None,
                   seats: Optional[int] = None,
                   default_school: bool = True) -> OnboardResult:
    email = email.lower()
    org = s.execute(
        select(Organization).where(Organization.domain == domain,
                                   Organization.deleted_at.is_(None))
    ).scalar_one_or_none()

    created = org is None
    if org is None:
        org = Organization(name=org_name or domain, domain=domain, external_ref=customer_id,
                           seats=seats)
        s.add(org); s.flush()
        s.add(TenantIntegration(organization_id=org.id, provider="google",
                                status="pending", admin_email=email,
                                customer_id=customer_id))
        if default_school:
            # École par défaut (domaine mono-école) ; le rostering ajoutera les autres via OU.
            s.add(School(name=org_name or domain, organization_id=org.id,
                         external_ref="__default__"))
    elif customer_id and not org.external_ref:
        org.external_ref = customer_id

    # Compte bootstrap : pas d'external_ref → protégé du déprovisioning rostering.
    user = s.execute(select(AppUser).where(AppUser.email == email)).scalar_one_or_none()
    if user is None:
        user = AppUser(email=email); s.add(user); s.flush()

    m = s.execute(
        select(Membership).where(Membership.user_id == user.id,
                                 Membership.role == Role.IT_ADMIN,
                                 Membership.organization_id == org.id)
    ).scalar_one_or_none()
    if m is None:
        s.add(Membership(user_id=user.id, role=Role.IT_ADMIN, organization_id=org.id))

    return OnboardResult(org, user, created)
