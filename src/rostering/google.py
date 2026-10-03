"""Adapter Google Admin SDK Directory (Phase B) — implémente le `Protocol` Directory.

Conception en deux couches pour rester testable et léger :
- **Mapping** (JSON Directory → DirectorySnapshot) : pur, testé via un transport factice,
  sans réseau ni credentials. C'est ici que vit la logique.
- **Transport** : un callable `(path, params) -> json` authentifié. La fabrique réelle
  (`service_account_transport`) utilise `google-auth` pour la délégation domain-wide
  (signature JWT RS256, impossible en stdlib) — importé **paresseusement** pour que ce
  module s'importe et se teste même sans la lib installée.

Scopes (lecture seule, least-privilege — simplifie la revue OAuth Google) :
  admin.directory.{user,orgunit,group,group.member}.readonly
"""
from __future__ import annotations

import json
import os
from typing import Callable, Dict, List, Optional, Protocol

from src.models.base import Role
from src.rostering.directory import (
    DirectorySnapshot, DirGroup, DirGuardian, DirMembership, DirOrgUnit, DirUser,
)
from src.rostering.mapping import classify_role

_BASE = "https://admin.googleapis.com/admin/directory/v1"
_CLASSROOM_BASE = "https://classroom.googleapis.com"

DIRECTORY_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/admin.directory.orgunit.readonly",
    "https://www.googleapis.com/auth/admin.directory.group.readonly",
    "https://www.googleapis.com/auth/admin.directory.group.member.readonly",
]

GUARDIAN_SCOPES = ["https://www.googleapis.com/auth/classroom.guardianlinks.students.readonly"]

# Transport authentifié : (path relatif, params) -> dict JSON.
Transport = Callable[[str, Dict], Dict]


class GoogleDirectoryAdapter:
    """Lit l'annuaire Workspace et le normalise en `DirectorySnapshot` pour le moteur."""

    def __init__(self, transport: Transport, *, customer: str = "my_customer"):
        self._get = transport
        self._customer = customer

    # --- pagination Directory (nextPageToken) ---
    def _paged(self, path: str, params: Dict, key: str) -> List[dict]:
        items: List[dict] = []
        token: Optional[str] = None
        while True:
            p = dict(params)
            if token:
                p["pageToken"] = token
            data = self._get(path, p)
            items.extend(data.get(key, []))
            token = data.get("nextPageToken")
            if not token:
                return items

    def snapshot(self) -> DirectorySnapshot:
        c = self._customer

        # OrgUnits (clé = orgUnitPath : c'est ce que les users référencent via orgUnitPath)
        org_units = [
            DirOrgUnit(
                external_id=o["orgUnitPath"],
                name=o.get("name", ""),
                parent_external_id=o.get("parentOrgUnitPath"),
            )
            for o in self._paged(f"/customer/{c}/orgunits", {"type": "all"}, "organizationUnits")
        ]

        users = [
            DirUser(
                external_id=u["id"],
                email=u["primaryEmail"],
                full_name=(u.get("name") or {}).get("fullName", ""),
                org_unit_external_id=u.get("orgUnitPath"),
                is_admin=bool(u.get("isAdmin")),
                suspended=bool(u.get("suspended")),
            )
            for u in self._paged(
                "/users", {"customer": c, "maxResults": 500, "projection": "basic"}, "users"
            )
        ]

        groups = [
            DirGroup(external_id=g["id"], name=g.get("name") or g.get("email", ""))
            for g in self._paged("/groups", {"customer": c, "maxResults": 200}, "groups")
        ]

        memberships: List[DirMembership] = []
        for g in groups:
            for m in self._paged(f"/groups/{g.external_id}/members", {"maxResults": 200}, "members"):
                # On ignore les groupes imbriqués : seules les personnes sont inscrites.
                if m.get("type", "USER") == "USER" and m.get("id"):
                    memberships.append(DirMembership(g.external_id, m["id"]))

        return DirectorySnapshot(org_units, users, groups, memberships)


class GoogleClassroomGuardians:
    """Source de tuteurs via l'API Google Classroom (`userProfiles.guardians`).

    Lien tuteur↔élève = établi par invitation école + acceptation parent → vérifié par
    Google. C'est l'autorité de confiance `source="roster"`. Un appel par élève (l'API
    n'a pas de listing domaine) ; les non-élèves ne sont jamais interrogés (cf. Composite).
    """

    def __init__(self, transport: Transport):
        self._get = transport

    def _paged(self, path: str, key: str) -> List[dict]:
        items, token = [], None
        while True:
            params = {"pageToken": token} if token else {}
            data = self._get(path, params)
            items.extend(data.get(key, []))
            token = data.get("nextPageToken")
            if not token:
                return items

    def guardians_for(self, student_external_ids: List[str]) -> List[DirGuardian]:
        out: List[DirGuardian] = []
        for sid in student_external_ids:
            for g in self._paged(f"/v1/userProfiles/{sid}/guardians", "guardians"):
                prof = g.get("guardianProfile") or {}
                email = prof.get("emailAddress")
                if email:
                    out.append(DirGuardian(
                        student_external_id=sid,
                        email=email,
                        full_name=(prof.get("name") or {}).get("fullName", ""),
                        external_id=g.get("guardianId"),
                    ))
        return out


class GuardianSource(Protocol):
    def guardians_for(self, student_external_ids: List[str]) -> List[DirGuardian]: ...


class CompositeDirectory:
    """Annuaire de base (Admin SDK) ENRICHI des tuteurs (Classroom), derrière le même Protocol.

    N'interroge les tuteurs QUE pour les utilisateurs classés élèves (économie d'appels).
    Résilient : si la source tuteurs échoue, on renvoie `guardians=None` (la sync ne touche
    alors PAS aux liens parents) plutôt que de casser tout le rostering.
    """

    def __init__(self, base, guardian_source: GuardianSource, *, classifier=classify_role):
        self._base = base
        self._guardians = guardian_source
        self._classifier = classifier

    def snapshot(self) -> DirectorySnapshot:
        snap = self._base.snapshot()
        ou_by_id = {o.external_id: o for o in snap.org_units}
        student_ids = [u.external_id for u in snap.users
                       if self._classifier(u, ou_by_id) == Role.STUDENT]
        try:
            guardians = self._guardians.guardians_for(student_ids)
        except Exception:
            guardians = None  # source indisponible → on ne réconcilie pas les parents
        return DirectorySnapshot(snap.org_units, snap.users, snap.groups, snap.memberships,
                                 guardians=guardians)


def get_user_self(access_token: str, *, timeout: float = 30.0) -> dict:
    """Lit la fiche de l'utilisateur courant (Directory `users/me`) avec SON token OAuth.

    Sert à vérifier le statut admin Workspace à l'onboarding, sans délégation domain-wide
    (l'app Marketplace n'est pas encore installée). Pas de google-auth : le token vient
    déjà du flux OIDC de l'admin. Nécessite le scope admin.directory.user.readonly.
    """
    import httpx
    r = httpx.get(f"{_BASE}/users/me", params={"projection": "basic"},
                  headers={"Authorization": f"Bearer {access_token}"}, timeout=timeout)
    r.raise_for_status()
    return r.json()


# --- Fabriques (voie réelle : google-auth en import paresseux) -----------------------------

def service_account_transport(key_info: dict, admin_email: str, *,
                              scopes: Optional[List[str]] = None,
                              base_url: str = _BASE,
                              timeout: float = 30.0) -> Transport:
    """Transport authentifié par délégation domain-wide (service account → admin impersonné).

    `base_url` permet de viser une autre API Google (Admin SDK par défaut, Classroom sinon).
    `google-auth` n'est importé qu'ici : le reste du module reste utilisable sans la lib.
    """
    import httpx
    from google.oauth2 import service_account  # lazy : dépendance optionnelle
    from google.auth.transport.requests import Request  # lazy

    creds = service_account.Credentials.from_service_account_info(
        key_info, scopes=scopes or DIRECTORY_SCOPES, subject=admin_email,
    )
    _auth_request = Request()

    def _get(path: str, params: Dict) -> Dict:
        if not creds.valid:
            creds.refresh(_auth_request)
        r = httpx.get(base_url + path, params=params,
                      headers={"Authorization": f"Bearer {creds.token}"}, timeout=timeout)
        r.raise_for_status()
        return r.json()

    return _get


def _load_sa_key() -> dict:
    raw = os.environ.get("GOOGLE_SA_KEY_JSON")
    path = os.environ.get("GOOGLE_SA_KEY_FILE")
    if raw:
        return json.loads(raw)
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise RuntimeError("Clé service account absente (GOOGLE_SA_KEY_JSON ou GOOGLE_SA_KEY_FILE)")


def build_from_env(admin_email: str, customer_id: Optional[str] = None, *,
                   with_guardians: Optional[bool] = None):
    """Construit l'adapter depuis la clé service account GLOBALE du vendeur (env).

    GOOGLE_SA_KEY_JSON (JSON inline) ou GOOGLE_SA_KEY_FILE (chemin). L'admin à impersonner
    et le customer viennent de l'intégration du tenant. Tuteurs (Classroom) : opt-in via
    `with_guardians` ou l'env `ROSTER_GUARDIANS=1` (scope OAuth dédié requis).
    """
    key_info = _load_sa_key()
    base = GoogleDirectoryAdapter(
        service_account_transport(key_info, admin_email), customer=customer_id or "my_customer")
    enabled = (with_guardians if with_guardians is not None
               else os.environ.get("ROSTER_GUARDIANS") == "1")
    if not enabled:
        return base
    g_transport = service_account_transport(
        key_info, admin_email, scopes=GUARDIAN_SCOPES, base_url=_CLASSROOM_BASE)
    return CompositeDirectory(base, GoogleClassroomGuardians(g_transport))
