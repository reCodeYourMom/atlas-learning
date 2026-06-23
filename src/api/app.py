"""API de session adaptative (Epic 4, T4.3).

Endpoints : POST /sessions, GET /sessions/{id}/next-item, POST /sessions/{id}/responses.
Sert aussi l'UI élève bilingue (statique) sous /ui.
Aucune donnée élève envoyée à un service externe.
"""
from __future__ import annotations

import os
import secrets
import uuid
from pathlib import Path
from typing import Callable, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.session_service import (
    AlreadyAnswered,
    grade_answer,
    next_item,
    start_session,
    submit_response,
)
from src.api.views_service import (
    class_digest,
    class_gaps,
    list_students,
    referentiel_graph,
    remediation_preview,
    school_overview,
    student_profile,
    student_trajectory,
    tutor_explanation,
)
from src.audit import log_action
from src.db import make_engine
from src.items import review
from src.items.arabic import (
    ALLAM_MODEL,
    TranslationError,
    ar_coverage,
    ar_math_preserved,
    translate_to_arabic,
)
from src.models.base import Role
from src.models.item import Item
from src.models.measurement import School, Student
from src.models.audit import AuditLog
from src.models.org import (
    AppUser, Classroom, Membership, Organization, ParentStudent, RosterRun, StudentClassroom,
    TenantIntegration,
)
from src.models.session import AssessmentSession
from src.rbac.auth import make_token, parse_token
from src.compliance import service as compliance
from src.licensing import service as licensing
from src.notify.email import build_email_sender
from src.notify.templates import admin_login_email, parent_login_email
from src.onboarding.service import onboard_tenant
from src.restitution.proof import proof_surfaces
from src.rbac import oidc
from src.rostering import google as gdir
from src.rostering import oneroster, oneroster_csv, wonde
from src.rostering.sync import sync_directory
from src.rbac.authz import (
    UserContext,
    build_user_context,
    can_access_classroom,
    can_access_school,
    can_access_student,
)

_engine = make_engine()


def get_db():
    s = Session(bind=_engine)
    try:
        yield s
    finally:
        s.close()


app = FastAPI(title="Atlas Learning — Session API")

# CORS — autorise le front Next.js (dev) à appeler l'API. Origines restreintes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- auth ----------

def get_context(authorization: str = Header(None), s: Session = Depends(get_db)) -> UserContext:
    """Résout le UserContext depuis le jeton Bearer (RBAC vérifié côté serveur)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="jeton manquant")
    try:
        user_id = parse_token(authorization[len("Bearer "):])
    except ValueError:
        raise HTTPException(status_code=401, detail="jeton invalide")
    return build_user_context(s, uuid.UUID(user_id))


# ---------- authentification = SSO uniquement ----------
#
# Plus de `/login` mot de passe ni de MFA TOTP applicative : l'identité passe par l'IdP
# (OIDC, plus bas). Deux exceptions SANS mot de passe, par liens magiques signés HMAC :
#   - parents (hors Workspace scolaire) ;
#   - super-admin Atlas (équipe éditeur), qui ne peut pas dépendre de l'IdP d'un client.
#
# Pour le DEV / la démo / les tests e2e (sans IdP externe), un simulateur SSO permet
# d'ouvrir une session pour un utilisateur EXISTANT. Il est FERMÉ par défaut et en prod.

def _dev_login_enabled() -> bool:
    is_prod = os.environ.get("ATLAS_ENV", "dev").lower() in ("prod", "production")
    return (not is_prod) and os.environ.get("OIDC_DEV_LOGIN") == "1"


class DevLoginIn(BaseModel):
    email: str


@app.post("/dev/login")
def dev_login(body: DevLoginIn, s: Session = Depends(get_db)):
    """Simulateur SSO (DEV uniquement) : ouvre une session pour un utilisateur existant.

    Remplace l'ancien login mot de passe dans la démo / les tests e2e. Refusé en prod
    et désactivé tant que `OIDC_DEV_LOGIN=1` n'est pas posé (défense en profondeur).
    """
    if not _dev_login_enabled():
        raise HTTPException(status_code=404, detail="indisponible")
    user = s.execute(
        select(AppUser).where(AppUser.email == body.email.strip().lower(),
                              AppUser.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="utilisateur inconnu")
    log_action(s, action="auth.dev_login", user_id=user.id)
    s.commit()
    return {"token": make_token(str(user.id)), "user_id": str(user.id)}


# ---------- SSO / OIDC (fallback compte direct conservé) ----------

def _web_base() -> str:
    return os.environ.get("WEB_BASE_URL", "http://localhost:3000").rstrip("/")


def _oidc_redirect_uri(provider_key: str) -> str:
    # Tout transite par l'origine du front (proxy /api → FastAPI) : same-origin, un seul host.
    base = os.environ.get("OIDC_REDIRECT_BASE", _web_base()).rstrip("/")
    return f"{base}/api/oauth/{provider_key}/callback"


@app.get("/auth/providers")
def auth_providers():
    """Providers SSO activés — pilote l'affichage des boutons côté front."""
    return {"providers": oidc.enabled_providers()}


@app.get("/oauth/{provider_key}/start")
def oauth_start(provider_key: str):
    """Démarre le flux OIDC : redirige vers l'IdP avec un `state` signé (anti-CSRF)."""
    p = oidc.get_provider(provider_key)
    if p is None:
        raise HTTPException(status_code=404, detail="fournisseur SSO non configuré")
    # state = jeton signé HMAC (purpose cloisonné) ; pas de stockage serveur nécessaire.
    # Il PORTE le nonce (anti-rejeu du ID token) : signé par nous, donc non forgeable et
    # revérifiable au callback sans état serveur.
    nonce = secrets.token_urlsafe(16)
    state = make_token(f"{provider_key}|{nonce}", purpose="oidc_state", ttl_s=600)
    url = oidc.authorize_url(p, _oidc_redirect_uri(provider_key), state, nonce=nonce)
    return RedirectResponse(url, status_code=302)


@app.get("/oauth/{provider_key}/callback")
def oauth_callback(provider_key: str, code: Optional[str] = None, state: Optional[str] = None,
                   error: Optional[str] = None, s: Session = Depends(get_db)):
    """Retour de l'IdP : valide le state, échange le code, résout l'utilisateur, ouvre la session."""
    web = _web_base()
    if error:
        return RedirectResponse(f"{web}/login?sso_error={error}", status_code=302)

    p = oidc.get_provider(provider_key)
    if p is None:
        raise HTTPException(status_code=404, detail="fournisseur SSO non configuré")

    # 1) state : signé par nous, du bon purpose, lié au bon provider → anti-CSRF/forge.
    #    Le state porte le nonce attendu dans le ID token.
    try:
        marker = parse_token(state or "", purpose="oidc_state")
    except ValueError:
        raise HTTPException(status_code=400, detail="state invalide")
    if not marker.startswith(f"{provider_key}|"):
        raise HTTPException(status_code=400, detail="state/provider incohérent")
    nonce = marker.split("|", 1)[1]
    if not code:
        raise HTTPException(status_code=400, detail="code manquant")

    # 2) échange code → tokens, puis résolution d'identité selon le provider :
    #    - id_token (Entra/Google/IdP conformes) : validation crypto stricte (JWKS + nonce) ;
    #    - userinfo (UAE PASS) : identité via userinfo over TLS (pas de id_token signé).
    try:
        tokens = oidc.exchange_code(p, code, _oidc_redirect_uri(provider_key))
        claims = oidc.resolve_identity(p, tokens, nonce=nonce)
    except oidc.IdTokenError:
        return RedirectResponse(f"{web}/login?sso_error=token", status_code=302)
    except Exception:
        return RedirectResponse(f"{web}/login?sso_error=exchange", status_code=302)
    email = oidc.extract_email(claims)
    if not email:
        return RedirectResponse(f"{web}/login?sso_error=email", status_code=302)

    # 3) l'utilisateur doit déjà exister (pas d'auto-provisioning d'un email inconnu).
    user = s.execute(
        select(AppUser).where(AppUser.email == email, AppUser.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return RedirectResponse(f"{web}/login?sso_error=unknown", status_code=302)

    # MFA porté par l'IdP côté SSO : on ouvre directement la session applicative.
    log_action(s, action="auth.sso_login", user_id=user.id)
    s.commit()
    session_token = make_token(str(user.id))
    # token dans le fragment (#) : jamais envoyé au serveur ni journalisé.
    return RedirectResponse(f"{web}/oauth/callback#token={session_token}", status_code=302)


# ---------- onboarding self-service (création de tenant par l'IT admin) ----------

# Scopes onboarding = OIDC + lecture annuaire (pour vérifier le statut admin Workspace).
_ONBOARDING_SCOPES = ("openid email profile "
                      "https://www.googleapis.com/auth/admin.directory.user.readonly")


def _onboarding_redirect_uri() -> str:
    base = os.environ.get("OIDC_REDIRECT_BASE", _web_base()).rstrip("/")
    return f"{base}/api/onboarding/google/callback"


@app.get("/onboarding/google/start")
def onboarding_start():
    """L'IT admin lance la création de son établissement via Sign-in Google (scopes admin)."""
    p = oidc.get_provider("google")
    if p is None:
        raise HTTPException(status_code=404, detail="SSO Google non configuré")
    nonce = secrets.token_urlsafe(16)
    state = make_token(f"google|{nonce}", purpose="onboarding", ttl_s=600)
    url = oidc.authorize_url(p, _onboarding_redirect_uri(), state,
                             scopes=_ONBOARDING_SCOPES, nonce=nonce)
    return RedirectResponse(url, status_code=302)


@app.get("/onboarding/google/callback")
def onboarding_callback(code: Optional[str] = None, state: Optional[str] = None,
                        error: Optional[str] = None, s: Session = Depends(get_db)):
    """Retour Google : exige un compte Workspace ADMIN, puis crée/retrouve le tenant."""
    web = _web_base()
    if error:
        return RedirectResponse(f"{web}/login?onboarding_error={error}", status_code=302)
    p = oidc.get_provider("google")
    if p is None:
        raise HTTPException(status_code=404, detail="SSO Google non configuré")
    try:
        marker = parse_token(state or "", purpose="onboarding")
    except ValueError:
        raise HTTPException(status_code=400, detail="state invalide")
    nonce = marker.split("|", 1)[1] if "|" in marker else None
    if not code:
        raise HTTPException(status_code=400, detail="code manquant")

    try:
        tokens = oidc.exchange_code(p, code, _onboarding_redirect_uri())
        claims = oidc.validate_id_token(p, tokens["id_token"], nonce=nonce)
        me = gdir.get_user_self(tokens["access_token"])  # statut admin réel (Directory API)
    except oidc.IdTokenError:
        return RedirectResponse(f"{web}/login?onboarding_error=token", status_code=302)
    except Exception:
        return RedirectResponse(f"{web}/login?onboarding_error=exchange", status_code=302)

    email = oidc.extract_email(claims)
    hd = claims.get("hd")  # domaine Workspace (claim signé ; absent pour un compte perso)
    if not email or not hd:
        return RedirectResponse(f"{web}/login?onboarding_error=workspace", status_code=302)
    if not me.get("isAdmin"):
        # hd prouve l'appartenance, PAS l'admin → on refuse tout non-admin (anti-escalade).
        return RedirectResponse(f"{web}/login?onboarding_error=not_admin", status_code=302)

    default_seats = os.environ.get("DEFAULT_SEATS")
    res = onboard_tenant(s, email=email, domain=hd, customer_id=me.get("customerId"),
                         seats=int(default_seats) if default_seats else None)
    log_action(s, action="onboarding.tenant_created" if res.created else "onboarding.admin_login",
               user_id=res.user.id)
    s.commit()
    token = make_token(str(res.user.id))
    return RedirectResponse(f"{web}/oauth/callback#token={token}", status_code=302)


# ---------- console IT admin : rostering (statut, sync, historique) ----------

# Connecteurs de rostering STANDARDS : chacun produit le même `DirectorySnapshot`, le
# moteur de sync ne connaît aucune source. `TenantIntegration.provider` choisit l'adapter.
_DIRECTORY_BUILDERS = {
    "google": lambda integ: gdir.build_from_env(integ.admin_email, integ.customer_id),
    "oneroster": lambda integ: oneroster.build_from_env(integ),
    "oneroster_csv": lambda integ: oneroster_csv.build_from_env(integ),
    "wonde": lambda integ: wonde.build_from_env(integ),
}


def directory_for(integ: TenantIntegration):
    """Construit l'adapter d'annuaire correspondant au provider du tenant."""
    builder = _DIRECTORY_BUILDERS.get(integ.provider)
    if builder is None:
        raise RuntimeError(f"provider de rostering inconnu : {integ.provider!r}")
    return builder(integ)


def get_directory_factory() -> Callable:
    """Injectable (tests : FakeDirectory ; prod : Google / OneRoster / Wonde selon le tenant)."""
    return directory_for


def _require_it_admin_org(ctx: UserContext, s: Session) -> Organization:
    if not ctx.has(Role.IT_ADMIN, Role.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="rôle IT admin requis")
    if len(ctx.org_ids) != 1:
        raise HTTPException(status_code=400, detail="organisation non résolue")
    org = s.get(Organization, next(iter(ctx.org_ids)))
    if org is None or org.deleted_at is not None:
        raise HTTPException(status_code=404, detail="organisation introuvable")
    return org


def _integration_of(s: Session, org: Organization) -> Optional[TenantIntegration]:
    return s.execute(
        select(TenantIntegration).where(TenantIntegration.organization_id == org.id)
    ).scalar_one_or_none()


def _run_payload(run: RosterRun) -> dict:
    return {
        "id": str(run.id), "status": run.status, "summary": run.summary,
        "created": run.created_count, "updated": run.updated_count,
        "deactivated": run.deactivated_count, "errors": run.error_count,
        "pending_deactivations": run.pending_deactivations,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@app.get("/admin/integration")
def admin_integration(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Statut de l'intégration d'annuaire + occupation des sièges (console IT)."""
    org = _require_it_admin_org(ctx, s)
    integ = _integration_of(s, org)
    usage = licensing.seat_usage(s, org)
    return {
        "organization": {"id": str(org.id), "name": org.name, "domain": org.domain,
                         "seats": usage["seats"], "seats_used": usage["used"],
                         "over_capacity": usage["over"]},
        "integration": None if integ is None else {
            "provider": integ.provider, "status": integ.status,
            "admin_email": integ.admin_email,
            "last_sync_at": integ.last_sync_at.isoformat() if integ.last_sync_at else None,
            "last_error": integ.last_error,
        },
    }


class IntegrationIn(BaseModel):
    provider: str                       # google | oneroster | oneroster_csv | wonde
    admin_email: Optional[str] = None   # google : admin à impersonner
    customer_id: Optional[str] = None   # google customer / id école Wonde


@app.post("/admin/integration")
def admin_set_integration(body: IntegrationIn,
                          ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Configure le connecteur de rostering du tenant (IT admin) parmi les standards supportés."""
    org = _require_it_admin_org(ctx, s)
    if body.provider not in _DIRECTORY_BUILDERS:
        raise HTTPException(status_code=400,
                            detail=f"provider non supporté (attendu : {sorted(_DIRECTORY_BUILDERS)})")
    integ = _integration_of(s, org)
    if integ is None:
        integ = TenantIntegration(organization_id=org.id)
        s.add(integ)
    integ.provider = body.provider
    integ.admin_email = body.admin_email
    integ.customer_id = body.customer_id
    integ.status = "pending"      # (re)connexion : la 1re sync repassera en connected
    integ.last_error = None
    log_action(s, action="rostering.configure", user_id=ctx.user_id,
               resource_type="organization", resource_id=org.id)
    s.commit()
    return {"provider": integ.provider, "status": integ.status}


@app.post("/admin/rostering/sync")
def admin_rostering_sync(force: bool = False, ctx: UserContext = Depends(get_context),
                         s: Session = Depends(get_db),
                         factory: Callable = Depends(get_directory_factory)):
    """Déclenche une sync (IT admin). `force=true` = approuver des désactivations massives bloquées."""
    org = _require_it_admin_org(ctx, s)
    integ = _integration_of(s, org)
    if integ is None:
        raise HTTPException(status_code=400, detail="intégration non configurée")
    try:
        directory = factory(integ)
        run = sync_directory(s, org, directory.snapshot(), force=force)
        if run.status != "blocked":
            licensing.flag_overage(s, org)  # dépassement de licence → statut/alerte visible
        log_action(s, action="rostering.sync_forced" if force else "rostering.sync",
                   user_id=ctx.user_id)
        s.commit()
    except Exception as exc:  # adapter indisponible / erreur Google → on trace et on remonte
        integ.status, integ.last_error = "error", str(exc)[:500]
        s.commit()
        raise HTTPException(status_code=502, detail="échec de la synchronisation")
    return _run_payload(run)


@app.get("/admin/rostering/runs")
def admin_rostering_runs(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Historique des synchronisations (audit, console IT)."""
    org = _require_it_admin_org(ctx, s)
    runs = s.execute(
        select(RosterRun).where(RosterRun.organization_id == org.id)
        .order_by(RosterRun.started_at.desc()).limit(20)
    ).scalars().all()
    return {"runs": [_run_payload(r) for r in runs]}


class SeatsIn(BaseModel):
    seats: Optional[int] = None  # None = illimité (essai)


@app.post("/admin/organizations/{org_id}/seats")
def admin_set_seats(org_id: uuid.UUID, body: SeatsIn,
                    ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Pose le quota de sièges contractuel — RÉSERVÉ au vendeur (SUPER_ADMIN)."""
    if Role.SUPER_ADMIN not in ctx.roles:
        raise HTTPException(status_code=403, detail="réservé au vendeur")
    org = s.get(Organization, org_id)
    if org is None or org.deleted_at is not None:
        raise HTTPException(status_code=404, detail="organisation introuvable")
    try:
        licensing.set_seats(s, org, body.seats)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    licensing.flag_overage(s, org)  # recalcule l'état si le nouveau quota change la donne
    log_action(s, action="licensing.set_seats", resource_type="organization", resource_id=org_id)
    s.commit()
    return licensing.seat_usage(s, org)


# ---------- conformité PDPL : audit, export, droit à l'oubli (IT admin) ----------

@app.get("/admin/audit")
def admin_audit(limit: int = 100, action: Optional[str] = None,
                ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Vue du journal d'audit du tenant (la DSI veut voir les accès/actions)."""
    org = _require_it_admin_org(ctx, s)
    return {"entries": compliance.audit_entries(s, org, limit=min(max(limit, 1), 500),
                                                action=action)}


@app.get("/admin/export")
def admin_export(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Export structuré des données du tenant (portabilité PDPL)."""
    org = _require_it_admin_org(ctx, s)
    log_action(s, action="compliance.export", user_id=ctx.user_id)
    s.commit()
    return compliance.export_tenant(s, org)


@app.post("/admin/students/{student_id}/erase")
def admin_erase_student(student_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                        s: Session = Depends(get_db)):
    """Droit à l'oubli d'un élève (suppression DURE, isolation tenant vérifiée)."""
    org = _require_it_admin_org(ctx, s)
    st = compliance.student_in_org(s, org, student_id)
    if st is None:
        raise HTTPException(status_code=404, detail="élève introuvable dans ce tenant")
    res = compliance.erase_student(s, st)
    s.commit()
    return res


class TenantEraseIn(BaseModel):
    confirm_domain: str  # garde-fou : doit égaler le domaine du tenant


@app.post("/admin/tenant/erase")
def admin_erase_tenant(body: TenantEraseIn, ctx: UserContext = Depends(get_context),
                       s: Session = Depends(get_db)):
    """Purge complète du tenant (fin de contrat) — IRRÉVERSIBLE. Confirmé par le domaine."""
    org = _require_it_admin_org(ctx, s)
    if not org.domain or body.confirm_domain.strip().lower() != org.domain.lower():
        raise HTTPException(status_code=400, detail="confirmation du domaine invalide")
    res = compliance.erase_tenant(s, org)
    s.commit()
    return res


# ---------- accès parent : lien magique (sans mot de passe, hors Workspace) ----------

def get_email_sender():
    """Injectable (tests : FakeEmailSender ; prod : provider via env)."""
    return build_email_sender()


def get_llm_client():
    """Client LLM arabe injectable (tests : FakeLLMClient ; prod : Groq/ALLaM via env).

    Défaut = modèle arabe natif ALLaM, servi via Groq (cf. items/arabic.py).
    """
    from src.llm.client import GroqClient
    return GroqClient(model=ALLAM_MODEL)


_PARENT_LINK_TTL = 14 * 24 * 3600  # 14 jours : le parent reclique / redemande quand il veut


def _send_parent_link(sender, user: AppUser) -> None:
    token = make_token(str(user.id), purpose="parent_login", ttl_s=_PARENT_LINK_TTL)
    link = f"{_web_base()}/api/parent/login?token={token}"
    subject, html, text = parent_login_email(link)
    sender.send(to=user.email, subject=subject, html=html, text=text)


class ParentRequestIn(BaseModel):
    email: str


@app.post("/parent/request-link")
def parent_request_link(body: ParentRequestIn, s: Session = Depends(get_db),
                        sender=Depends(get_email_sender)):
    """Auto-demande d'un lien magique. Réponse constante → pas d'énumération de comptes."""
    user = s.execute(
        select(AppUser).where(AppUser.email == body.email.strip().lower(),
                              AppUser.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is not None and user.is_active:
        ctx = build_user_context(s, user.id)
        if Role.PARENT in ctx.roles:
            _send_parent_link(sender, user)
            log_action(s, action="parent.request_link", user_id=user.id)
            s.commit()
    return {"ok": True}


@app.get("/parent/login")
def parent_login(token: str, s: Session = Depends(get_db)):
    """Valide le lien magique → ouvre une session → redirige vers l'espace enfant."""
    web = _web_base()
    try:
        uid = parse_token(token, purpose="parent_login")
    except ValueError:
        return RedirectResponse(f"{web}/parent?error=invalid", status_code=302)
    user = s.get(AppUser, uuid.UUID(uid))
    if user is None or not user.is_active or user.deleted_at is not None:
        return RedirectResponse(f"{web}/parent?error=invalid", status_code=302)
    log_action(s, action="parent.login", user_id=user.id)
    s.commit()
    session_token = make_token(str(user.id))   # la racine route le parent → /parent/{enfant}
    return RedirectResponse(f"{web}/oauth/callback#token={session_token}", status_code=302)


# ---------- accès super-admin Atlas (équipe éditeur) : lien magique interne ----------
#
# Les SUPER_ADMIN ne peuvent pas dépendre de l'IdP d'un CLIENT. Plutôt qu'un mot de passe
# (interdit par la revue DSI), ils se connectent par un lien magique signé envoyé à leur
# email d'éditeur — court-vécu, à usage unique, cloisonné (purpose=admin_login).

_ADMIN_LINK_TTL = 30 * 60  # 30 min : accès éditeur, fenêtre courte


@app.post("/admin/request-link")
def admin_request_link(body: ParentRequestIn, s: Session = Depends(get_db),
                       sender=Depends(get_email_sender)):
    """Auto-demande d'un lien magique d'accès éditeur. Réservé aux SUPER_ADMIN.

    Réponse constante (anti-énumération) : on ne révèle jamais si l'email est super-admin.
    """
    user = s.execute(
        select(AppUser).where(AppUser.email == body.email.strip().lower(),
                              AppUser.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is not None and user.is_active:
        ctx = build_user_context(s, user.id)
        if Role.SUPER_ADMIN in ctx.roles:
            token = make_token(str(user.id), purpose="admin_login", ttl_s=_ADMIN_LINK_TTL)
            link = f"{_web_base()}/api/admin/login?token={token}"
            subject, html, text = admin_login_email(link)
            sender.send(to=user.email, subject=subject, html=html, text=text)
            log_action(s, action="admin.request_link", user_id=user.id)
            s.commit()
    return {"ok": True}


@app.get("/admin/login")
def admin_login(token: str, s: Session = Depends(get_db)):
    """Valide le lien magique éditeur → ouvre une session SUPER_ADMIN."""
    web = _web_base()
    try:
        uid = parse_token(token, purpose="admin_login")
    except ValueError:
        return RedirectResponse(f"{web}/login?admin_error=invalid", status_code=302)
    user = s.get(AppUser, uuid.UUID(uid))
    if user is None or not user.is_active or user.deleted_at is not None:
        return RedirectResponse(f"{web}/login?admin_error=invalid", status_code=302)
    # Re-vérifie le rôle au moment de la connexion (révocation possible entre-temps).
    if Role.SUPER_ADMIN not in build_user_context(s, user.id).roles:
        return RedirectResponse(f"{web}/login?admin_error=forbidden", status_code=302)
    log_action(s, action="admin.login", user_id=user.id)
    s.commit()
    session_token = make_token(str(user.id))
    return RedirectResponse(f"{web}/oauth/callback#token={session_token}", status_code=302)


@app.post("/admin/parents/invite")
def admin_parents_invite(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db),
                         sender=Depends(get_email_sender)):
    """Envoie un lien magique à tous les parents actifs du tenant (IT admin)."""
    org = _require_it_admin_org(ctx, s)
    parents = s.execute(
        select(AppUser).join(Membership, Membership.user_id == AppUser.id)
        .where(Membership.organization_id == org.id, Membership.role == Role.PARENT,
               AppUser.deleted_at.is_(None), AppUser.is_active.is_(True))
    ).scalars().unique().all()
    for p in parents:
        _send_parent_link(sender, p)
    log_action(s, action="parents.invite", user_id=ctx.user_id, details={"count": len(parents)})
    s.commit()
    return {"invited": len(parents)}


@app.get("/parent/children")
def parent_children(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Enfants du parent connecté (étiquette = email scolaire ; on ne stocke pas de nom)."""
    if Role.PARENT not in ctx.roles:
        raise HTTPException(status_code=403, detail="réservé aux parents")
    out = []
    for sid in ctx.child_student_ids:
        st = s.get(Student, sid)
        if st is None or st.deleted_at is not None:
            continue
        label = st.external_ref or "—"
        if st.user_id:
            child = s.get(AppUser, st.user_id)
            if child is not None:
                label = child.email
        out.append({"student_id": str(sid), "label": label})
    return {"children": out}


# ---------- liaison parent↔enfant par le staff (autorité de confiance, audité) ----------

class GuardianIn(BaseModel):
    email: str
    send_invite: bool = True


@app.get("/students/{student_id}/guardians")
def list_guardians(student_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                   s: Session = Depends(get_db)):
    """Tuteurs d'un élève (prof/admin de l'élève)."""
    _authorize_student(ctx, s, student_id)
    rows = s.execute(
        select(AppUser, ParentStudent.source)
        .join(ParentStudent, ParentStudent.user_id == AppUser.id)
        .where(ParentStudent.student_id == student_id)
    ).all()
    return {"guardians": [{"user_id": str(u.id), "email": u.email, "source": src}
                          for (u, src) in rows]}


@app.post("/students/{student_id}/guardians")
def add_guardian(student_id: uuid.UUID, body: GuardianIn,
                 ctx: UserContext = Depends(get_context), s: Session = Depends(get_db),
                 sender=Depends(get_email_sender)):
    """Rattache un email parent à l'élève — c'est le STAFF qui établit la confiance. Audité."""
    st = _authorize_student(ctx, s, student_id)   # 403/404 si pas le droit sur cet élève
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email requis")
    pu = s.execute(select(AppUser).where(AppUser.email == email)).scalar_one_or_none()
    if pu is None:
        pu = AppUser(email=email); s.add(pu); s.flush()  # staff-managed → pas d'external_ref
    elif pu.deleted_at is not None:
        pu.deleted_at, pu.is_active = None, True
    school = s.get(School, st.school_id)
    org_id = school.organization_id if school is not None else None
    if s.execute(select(Membership).where(Membership.user_id == pu.id,
                                          Membership.role == Role.PARENT)).scalar_one_or_none() is None:
        s.add(Membership(user_id=pu.id, role=Role.PARENT, organization_id=org_id))
    if s.get(ParentStudent, (pu.id, st.id)) is None:
        s.add(ParentStudent(user_id=pu.id, student_id=st.id, source="staff"))
    log_action(s, action="guardian.link", user_id=ctx.user_id, school_id=st.school_id,
               resource_type="student", resource_id=st.id, details={"parent": email})
    if body.send_invite:
        _send_parent_link(sender, pu)
    s.commit()
    return {"student_id": str(st.id), "parent_user_id": str(pu.id), "email": email}


@app.delete("/students/{student_id}/guardians/{user_id}")
def remove_guardian(student_id: uuid.UUID, user_id: uuid.UUID,
                    ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Retire un lien tuteur (prof/admin de l'élève). Audité."""
    st = _authorize_student(ctx, s, student_id)
    ps = s.get(ParentStudent, (user_id, st.id))
    if ps is None:
        raise HTTPException(status_code=404, detail="lien introuvable")
    s.delete(ps)
    log_action(s, action="guardian.unlink", user_id=ctx.user_id, school_id=st.school_id,
               resource_type="student", resource_id=st.id, details={"parent_user_id": str(user_id)})
    s.commit()
    return {"ok": True}


# ---------- onboarding IT : checklist guidée (état dérivé) ----------

@app.get("/admin/setup")
def admin_setup(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Étapes de mise en route, cochées automatiquement depuis l'état réel du tenant."""
    org = _require_it_admin_org(ctx, s)
    integ = _integration_of(s, org)
    usage = licensing.seat_usage(s, org)
    synced = integ is not None and integ.last_sync_at is not None
    invited = s.execute(
        select(AuditLog.id).where(
            AuditLog.action == "parents.invite",
            AuditLog.user_id.in_(
                select(Membership.user_id).where(Membership.organization_id == org.id)),
        ).limit(1)
    ).first() is not None
    steps = [
        {"key": "connect", "done": integ is not None},
        {"key": "sync", "done": synced},
        {"key": "verify", "done": usage["used"] > 0},
        {"key": "parents", "done": invited},
    ]
    return {"steps": steps, "done": sum(1 for x in steps if x["done"]), "total": len(steps)}


@app.get("/me")
def me(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Identité + périmètre de l'utilisateur courant — pilote la navigation du front."""
    from src.models.measurement import School

    classrooms = []
    for cid in ctx.classroom_ids:
        cls = s.get(Classroom, cid)
        if cls is not None:
            classrooms.append({"id": str(cls.id), "name": cls.name, "school_id": str(cls.school_id)})

    schools = []
    seen = set(ctx.school_ids)
    # admin : écoles de son périmètre ; enseignant : écoles de ses classes
    for cid in ctx.classroom_ids:
        cls = s.get(Classroom, cid)
        if cls is not None:
            seen.add(cls.school_id)
    for sid in seen:
        sch = s.get(School, sid)
        if sch is not None:
            schools.append({"id": str(sch.id), "name": sch.name})
            for cls in s.execute(select(Classroom).where(Classroom.school_id == sch.id)).scalars():
                if not any(c["id"] == str(cls.id) for c in classrooms) \
                        and ctx.has(Role.PED_ADMIN, Role.IT_ADMIN, Role.SUPER_ADMIN):
                    classrooms.append({"id": str(cls.id), "name": cls.name,
                                       "school_id": str(cls.school_id)})

    return {
        "user_id": str(ctx.user_id),
        "roles": sorted(r.value for r in ctx.roles),
        "schools": schools,
        "classrooms": classrooms,
        "child_student_ids": [str(x) for x in ctx.child_student_ids],
        "own_student_id": str(ctx.own_student_id) if ctx.own_student_id else None,
    }


def _authorize_student(ctx: UserContext, s: Session, student_id: uuid.UUID) -> Student:
    st = s.get(Student, student_id)
    if st is None:
        raise HTTPException(status_code=404, detail="élève introuvable")
    # Ensemble des classes de l'élève (principale + spécialités) pour le contrôle enseignant.
    class_ids = set(s.execute(
        select(StudentClassroom.classroom_id).where(StudentClassroom.student_id == st.id)
    ).scalars())
    if st.classroom_id:
        class_ids.add(st.classroom_id)
    if not can_access_student(ctx, st.id, st.school_id, class_ids):
        raise HTTPException(status_code=403, detail="accès refusé à cet élève")
    return st


# ---------- session (protégée RBAC) ----------

class StartSessionIn(BaseModel):
    student_id: uuid.UUID                # school_id dérivé de l'élève (pas de confiance au client)
    target_competency_ids: Optional[List[uuid.UUID]] = None


class ResponseIn(BaseModel):
    item_id: uuid.UUID
    selected: str                       # option choisie ; correction côté serveur
    lang: str = "en"                    # "en" | "ar"
    response_time_ms: Optional[int] = None


def _get_session(s: Session, session_id: uuid.UUID) -> AssessmentSession:
    sess = s.get(AssessmentSession, session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="session introuvable")
    return sess


@app.post("/sessions")
def create_session(body: StartSessionIn, ctx: UserContext = Depends(get_context),
                   s: Session = Depends(get_db)):
    st = _authorize_student(ctx, s, body.student_id)
    sess = start_session(s, student_id=st.id, school_id=st.school_id,
                         target_competency_ids=body.target_competency_ids)
    return {"session_id": str(sess.id), "status": sess.status}


@app.get("/sessions/{session_id}/next-item")
def get_next_item(session_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                  s: Session = Depends(get_db)):
    sess = _get_session(s, session_id)
    _authorize_student(ctx, s, sess.student_id)
    return next_item(s, sess)


@app.post("/sessions/{session_id}/responses")
def post_response(session_id: uuid.UUID, body: ResponseIn,
                  ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    sess = _get_session(s, session_id)
    _authorize_student(ctx, s, sess.student_id)
    item = s.get(Item, body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item introuvable")
    is_correct = grade_answer(item, body.selected, body.lang)   # correction serveur
    try:
        result = submit_response(s, sess, item_id=body.item_id, is_correct=is_correct,
                                 response_time_ms=body.response_time_ms)
        # `was_correct` = correction de la réponse qu'on vient de soumettre (feedback élève) ;
        # le reste du payload décrit l'item SUIVANT.
        return {**result, "was_correct": is_correct}
    except AlreadyAnswered:
        raise HTTPException(status_code=409, detail="item déjà répondu dans cette session")


@app.get("/classrooms/{classroom_id}/gaps")
def classroom_gaps(classroom_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                   s: Session = Depends(get_db)):
    """T5.4 — vue enseignant : lacunes de SA classe (RBAC)."""
    cls = s.get(Classroom, classroom_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="classe introuvable")
    if not can_access_classroom(ctx, classroom_id, cls.school_id):
        raise HTTPException(status_code=403, detail="accès refusé à cette classe")
    log_action(s, action="classroom.view_gaps", school_id=cls.school_id, user_id=ctx.user_id,
               resource_type="classroom", resource_id=classroom_id)
    s.commit()
    return {"classroom_id": str(classroom_id), "gaps": class_gaps(s, classroom_id)}


@app.get("/classrooms/{classroom_id}/digest")
def classroom_digest(classroom_id: uuid.UUID, days: int = 7,
                     ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Digest hebdomadaire enseignant (Mouvement 01) : activité, lacunes émergentes, priorité #1."""
    cls = s.get(Classroom, classroom_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="classe introuvable")
    if not can_access_classroom(ctx, classroom_id, cls.school_id):
        raise HTTPException(status_code=403, detail="accès refusé à cette classe")
    log_action(s, action="classroom.view_digest", school_id=cls.school_id, user_id=ctx.user_id,
               resource_type="classroom", resource_id=classroom_id)
    s.commit()
    return class_digest(s, classroom_id, days=min(max(days, 1), 90))


@app.get("/classrooms/{classroom_id}/students")
def classroom_students(classroom_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                       s: Session = Depends(get_db)):
    """Liste des élèves d'une classe (enseignant/admin)."""
    cls = s.get(Classroom, classroom_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="classe introuvable")
    if not can_access_classroom(ctx, classroom_id, cls.school_id):
        raise HTTPException(status_code=403, detail="accès refusé à cette classe")
    return {"classroom_id": str(classroom_id), "name": cls.name,
            "students": list_students(s, classroom_id)}


@app.get("/students/{student_id}/profile")
def get_student_profile(student_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                        s: Session = Depends(get_db)):
    """Fiche élève — profil de maîtrise + diagnostic causal (écran héros). RBAC."""
    st = _authorize_student(ctx, s, student_id)
    log_action(s, action="student.view_profile", school_id=st.school_id, user_id=ctx.user_id,
               resource_type="student", resource_id=st.id)
    s.commit()
    return student_profile(s, student_id)


@app.get("/students/{student_id}/trajectory")
def get_student_trajectory(student_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                           s: Session = Depends(get_db)):
    """Trajectoire (vue parent, lecture seule). RBAC."""
    st = _authorize_student(ctx, s, student_id)
    log_action(s, action="student.view_trajectory", school_id=st.school_id, user_id=ctx.user_id,
               resource_type="student", resource_id=st.id)
    s.commit()
    return student_trajectory(s, student_id)


@app.get("/students/{student_id}/tutor")
def student_tutor(student_id: uuid.UUID, competency_code: str,
                  ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Tuteur causal (Mouvement 04) : explique « pourquoi cet exercice » pour une lacune.

    Déterministe, sans PII (sortie = libellés de compétences). Accessible à qui peut déjà
    voir l'élève (élève lui-même, enseignant, parent) — l'autorisation est vérifiée.
    """
    _authorize_student(ctx, s, student_id)
    return tutor_explanation(s, student_id, competency_code)


class RemediationIn(BaseModel):
    competency_code: str
    lang: str = "en"


@app.post("/remediation/preview")
def post_remediation(body: RemediationIn, ctx: UserContext = Depends(get_context),
                     s: Session = Depends(get_db)):
    """Aperçu d'un exercice de remédiation pour la compétence ciblée (cause racine)."""
    if not ctx.has(Role.TEACHER, Role.PED_ADMIN, Role.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="rôle non autorisé")
    return remediation_preview(s, body.competency_code, body.lang)


@app.get("/competencies")
def get_competencies(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Graphe du référentiel (nœuds + arêtes) — support de la viz diagnostic."""
    return referentiel_graph(s)


# ---------- console linguiste : descente de l'arabe dans le contenu (Mouvement 02) ----------
#
# Le pipeline AR existe (items/arabic.py + review.py) mais n'était exposé nulle part : un
# linguiste ne pouvait pas travailler. Ici on l'ouvre, sous garde-fou pédagogique. La machine
# PROPOSE (Groq/ALLaM), le linguiste VALIDE — le gate ar_validated reste la seule porte d'entrée
# au pool servi (cf. review.promote_to_active).

def _require_linguist(ctx: UserContext) -> None:
    if not ctx.has(Role.PED_ADMIN, Role.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="rôle pédagogique requis (validation linguistique)")


def _ar_item_payload(it: Item) -> dict:
    return {
        "item_id": str(it.id),
        "competency_id": str(it.competency_id),
        "status": it.status.value,
        "answer_format": it.answer_format.value,
        "content_en": it.content_en,
        "content_ar": it.content_ar,
        "ar_validated": it.ar_validated,
        # Fidélité math déterministe EN↔AR : priorise la revue (un nombre altéré = à corriger).
        "math_preserved": ar_math_preserved(it.content_en, it.content_ar) if it.content_ar else False,
    }


@app.get("/admin/arabic/coverage")
def admin_arabic_coverage(ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Couverture arabe de la banque (preuve de la « descente » AR — prérequis KSA)."""
    _require_linguist(ctx)
    return ar_coverage(s)


@app.get("/admin/arabic/pending")
def admin_arabic_pending(limit: int = 50, ctx: UserContext = Depends(get_context),
                         s: Session = Depends(get_db)):
    """Worklist du linguiste : items revus EN en attente de traduction/validation AR."""
    _require_linguist(ctx)
    items = review.list_pending_arabic(s)[: min(max(limit, 1), 200)]
    return {"items": [_ar_item_payload(it) for it in items], "coverage": ar_coverage(s)}


@app.post("/admin/arabic/{item_id}/propose")
def admin_arabic_propose(item_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                         s: Session = Depends(get_db), client=Depends(get_llm_client)):
    """Propose un content_ar via Groq/ALLaM (machine PROPOSE). Repose ar_validated à False."""
    _require_linguist(ctx)
    it = s.get(Item, item_id)
    if it is None or it.deleted_at is not None:
        raise HTTPException(status_code=404, detail="item introuvable")
    try:
        content_ar = translate_to_arabic(it.content_en, client, answer_format=it.answer_format)
    except TranslationError as exc:
        raise HTTPException(status_code=502, detail=f"traduction inexploitable : {exc}")
    review.set_arabic(s, it, content_ar, by=str(ctx.user_id))
    log_action(s, action="arabic.propose", user_id=ctx.user_id,
               resource_type="item", resource_id=it.id)
    s.commit()
    return _ar_item_payload(it)


@app.post("/admin/arabic/{item_id}/validate")
def admin_arabic_validate(item_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                          s: Session = Depends(get_db)):
    """Le linguiste VALIDE l'AR : ar_validated=True, human_reviewed → linguist_validated."""
    _require_linguist(ctx)
    it = s.get(Item, item_id)
    if it is None or it.deleted_at is not None:
        raise HTTPException(status_code=404, detail="item introuvable")
    try:
        review.validate_arabic(s, it, linguist=str(ctx.user_id))
    except review.InvalidTransition as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    log_action(s, action="arabic.validate", user_id=ctx.user_id,
               resource_type="item", resource_id=it.id)
    s.commit()
    return _ar_item_payload(it)


@app.get("/schools/{school_id}/overview")
def school_overview_ep(school_id: uuid.UUID, ctx: UserContext = Depends(get_context),
                       s: Session = Depends(get_db)):
    """T5.5 — vue admin pédagogique : agrégat établissement (RBAC + tenant)."""
    if not can_access_school(ctx, school_id):
        raise HTTPException(status_code=403, detail="accès refusé à cet établissement")
    log_action(s, action="school.view_overview", school_id=school_id, user_id=ctx.user_id,
               resource_type="school", resource_id=school_id)
    s.commit()
    return school_overview(s, school_id)


@app.get("/schools/{school_id}/proof")
def school_proof_ep(school_id: uuid.UUID, window_days: int = 30,
                    ctx: UserContext = Depends(get_context), s: Session = Depends(get_db)):
    """Surfaces de preuve (Mouvement 03) : avant/après cohorte + gains + projection trajectoire."""
    if not can_access_school(ctx, school_id):
        raise HTTPException(status_code=403, detail="accès refusé à cet établissement")
    log_action(s, action="school.view_proof", school_id=school_id, user_id=ctx.user_id,
               resource_type="school", resource_id=school_id)
    s.commit()
    return proof_surfaces(s, school_id, window_days=min(max(window_days, 1), 365))


_static = Path(__file__).resolve().parent / "static"
if _static.exists():
    app.mount("/ui", StaticFiles(directory=str(_static), html=True), name="ui")
