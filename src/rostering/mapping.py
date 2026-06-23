"""Règles de mapping annuaire → modèle Atlas (pures, testables, surchargables par tenant).

Le rôle d'un utilisateur est déduit de son OrgUnit (et du flag admin Workspace). Les noms
d'OU varient d'une école à l'autre → on isole la règle ici pour la personnaliser sans
toucher au moteur. Défaut volontairement conservateur : un utilisateur non classé est
ignoré (jamais inscrit par erreur).
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from src.models.base import Role
from src.rostering.directory import DirOrgUnit, DirUser

_STUDENT_HINTS = ("student", "eleve", "élève", "pupil", "learner", "طالب")
_TEACHER_HINTS = ("teacher", "staff", "faculty", "prof", "enseignant", "معلم")


def _ou_name(user: DirUser, ou_by_id: Dict[str, DirOrgUnit]) -> str:
    ou = ou_by_id.get(user.org_unit_external_id or "")
    return (ou.name if ou else "").lower()


def classify_role(user: DirUser, ou_by_id: Dict[str, DirOrgUnit]) -> Optional[Role]:
    """Rôle Atlas d'un utilisateur, ou None s'il n'est pas classable (→ ignoré).

    Priorité au rôle EXPLICITE fourni par la source (OneRoster/Wonde) : standards de
    rostering qui exposent directement student/teacher/administrator → pas de devinette.
    Repli heuristique sur le nom d'OrgUnit + flag admin (cas Google Workspace, sans rôle).
    """
    if user.role is not None:
        return user.role
    if user.is_admin:
        return Role.IT_ADMIN
    name = _ou_name(user, ou_by_id)
    if any(h in name for h in _STUDENT_HINTS):
        return Role.STUDENT
    if any(h in name for h in _TEACHER_HINTS):
        return Role.TEACHER
    return None


def resolve_group_school(
    member_school_ids: List[str],
    fallback_school_id: Optional[str],
) -> Optional[str]:
    """École d'une classe = école majoritaire de ses membres ; sinon repli (école unique)."""
    if member_school_ids:
        return Counter(member_school_ids).most_common(1)[0][0]
    return fallback_school_id


def pick_homeroom(class_external_refs: List[str]) -> Optional[str]:
    """Classe principale (homeroom) d'un élève parmi ses inscriptions.

    L'annuaire Google ne distingue pas la classe principale des spécialités → défaut
    **déterministe** (ref la plus petite) pour rester idempotent. Surchargable par tenant
    qui connaît la vraie règle (ex. le groupe dont l'email encode le niveau).
    """
    return sorted(class_external_refs)[0] if class_external_refs else None
