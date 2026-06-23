"""Adapter Wonde — implémente le `Protocol` Directory.

Wonde agrège des centaines de MIS scolaires (forte présence MENA/UK) derrière une API REST
unique. Conception en deux couches comme les autres adapters :
- **Mapping** (JSON Wonde → DirectorySnapshot) : pur, testé via transport factice.
- **Transport** : callable `(path_ou_url, params) -> json` authentifié par Bearer token.

Modèle Wonde → Atlas (une école Wonde = une School Atlas) :
  school → School,  class → Classroom,  student/employee → AppUser (+ Student/Teacher),
  appartenance à une classe (relations `students`/`employees` incluses) → inscription.

Pagination Wonde : `meta.pagination.next` (URL curseur), suivie jusqu'à épuisement.
"""
from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from src.models.base import Role
from src.rostering.directory import (
    DirectorySnapshot, DirGroup, DirMembership, DirOrgUnit, DirUser,
)

# Transport authentifié : (path relatif OU url curseur next, params) -> dict JSON.
Transport = Callable[[str, Dict], Dict]


class WondeAdapter:
    """Lit une école Wonde et la normalise en `DirectorySnapshot`."""

    def __init__(self, transport: Transport, school_id: str, *,
                 school_name: str = "School", fallback_email_domain: str = "wonde.local"):
        self._get = transport
        self._school = school_id
        self._school_name = school_name
        # Beaucoup d'élèves K-12 n'ont pas d'email MIS. On synthétise une adresse STABLE
        # (ancrée sur l'id Wonde immuable) pour que le provisioning fonctionne ; l'identité
        # SSO réelle reste portée par l'IdP. Domaine configurable par tenant.
        self._fallback_domain = fallback_email_domain

    def _paged(self, path: str, params: Optional[Dict] = None) -> List[dict]:
        out: List[dict] = []
        data = self._get(path, params or {})
        out.extend(data.get("data", []))
        nxt = ((data.get("meta") or {}).get("pagination") or {}).get("next")
        while nxt:
            data = self._get(nxt, {})
            out.extend(data.get("data", []))
            nxt = ((data.get("meta") or {}).get("pagination") or {}).get("next")
        return out

    def _email(self, person: dict) -> str:
        email = person.get("email")
        if not email:
            cd = (person.get("contact_details") or {}).get("data") or {}
            email = cd.get("email") or cd.get("primary_email")
        if email:
            return email.lower()
        return f"{person['id']}@{self._fallback_domain}"   # repli stable (id Wonde)

    @staticmethod
    def _name(person: dict) -> str:
        return f"{person.get('forename', '')} {person.get('surname', '')}".strip()

    def _user(self, person: dict, role: Role) -> DirUser:
        return DirUser(
            external_id=person["id"],
            email=self._email(person),
            full_name=self._name(person),
            org_unit_external_id=self._school,
            role=role,
        )

    def snapshot(self) -> DirectorySnapshot:
        sid = self._school
        org_units = [DirOrgUnit(external_id=sid, name=self._school_name)]

        students = self._paged(f"/schools/{sid}/students", {"include": "contact_details"})
        employees = self._paged(f"/schools/{sid}/employees", {"include": "contact_details"})
        users = ([self._user(p, Role.STUDENT) for p in students]
                 + [self._user(p, Role.TEACHER) for p in employees])
        user_refs = {u.external_id for u in users}

        groups: List[DirGroup] = []
        memberships: List[DirMembership] = []
        for c in self._paged(f"/schools/{sid}/classes", {"include": "students,employees"}):
            cid = c["id"]
            groups.append(DirGroup(external_id=cid, name=c.get("name") or c.get("description", "")))
            members = ((c.get("students") or {}).get("data", [])
                       + (c.get("employees") or {}).get("data", []))
            for m in members:
                if m.get("id") in user_refs:
                    memberships.append(DirMembership(cid, m["id"]))

        # guardians=None : les contacts Wonde sont gérés à part (autorité de confiance),
        # jamais auto-inscrits ici → le moteur ne touche pas aux liens parents.
        return DirectorySnapshot(org_units, users, groups, memberships)


# --- Fabrique (voie réelle : Bearer token over httpx) ---------------------------------------

_BASE = "https://api.wonde.com/v1.0"


def bearer_transport(token: str, *, base_url: str = _BASE, timeout: float = 30.0) -> Transport:
    """Transport Wonde authentifié par Bearer token (jeton applicatif du vendeur)."""
    import httpx

    base = base_url.rstrip("/")

    def _get(path: str, params: Dict) -> Dict:
        # `path` peut être une URL absolue (curseur `next`) ou un chemin relatif.
        url = path if path.startswith("http") else f"{base}{path}"
        r = httpx.get(url, params=params,
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                      timeout=timeout)
        r.raise_for_status()
        return r.json()

    return _get


def build_from_env(integration=None) -> WondeAdapter:
    """Construit l'adapter Wonde depuis l'environnement + l'intégration du tenant.

    WONDE_TOKEN (jeton vendeur), WONDE_BASE_URL (optionnel). L'id de l'école Wonde vient de
    l'intégration du tenant (`customer_id`), son nom d'`admin_email`/`name` si dispo.
    """
    token = os.environ.get("WONDE_TOKEN")
    if not token:
        raise RuntimeError("Wonde non configuré (WONDE_TOKEN)")
    school_id = getattr(integration, "customer_id", None) or os.environ.get("WONDE_SCHOOL_ID")
    if not school_id:
        raise RuntimeError("École Wonde non résolue (integration.customer_id / WONDE_SCHOOL_ID)")
    transport = bearer_transport(token, base_url=os.environ.get("WONDE_BASE_URL", _BASE))
    return WondeAdapter(transport, school_id)
