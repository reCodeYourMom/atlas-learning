"""SSO OIDC (Epic 6) — seul mode d'authentification (plus de comptes directs).

Flux Authorization Code. La preuve d'identité repose sur la **validation cryptographique
du ID token** (`validate_id_token`) : signature RS256/ES256 vérifiée contre les clés
publiques de l'IdP (JWKS), plus `iss` / `aud` / `exp` / `nonce` (anti-rejeu). C'est ce
qu'attend une revue sécurité d'un « OIDC réel » ; l'appel `userinfo` ne sert plus que de
complément optionnel (ex. nom d'affichage), jamais de preuve d'identité.

Providers activés par variables d'environnement (rien en dur, rien de secret versionné) :
  OIDC_<PROVIDER>_CLIENT_ID, OIDC_<PROVIDER>_CLIENT_SECRET
  OIDC_<PROVIDER>_ISSUER (override ; presets google/microsoft sinon)
Un provider sans client_id/secret est simplement « non configuré » → 404 côté API.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx

_HTTP_TIMEOUT = 10.0
# Algorithmes de signature acceptés pour le ID token. RS256 = Google/Microsoft ;
# ES256 toléré pour les IdP génériques modernes. Jamais "none" ni HS* (clé symétrique).
_ID_TOKEN_ALGS = ["RS256", "ES256"]
_CLOCK_LEEWAY_S = 60  # tolérance de dérive d'horloge pour exp/iat


@dataclass(frozen=True)
class Provider:
    key: str
    issuer: str
    client_id: str
    client_secret: str
    scopes: str = "openid email profile"
    # Source d'identité : "id_token" = preuve cryptographique (signature JWKS), défaut sûr
    # pour Entra/Google/IdP conformes. "userinfo" = identité via l'endpoint userinfo over
    # TLS, UNIQUEMENT pour les IdP qui n'émettent pas de id_token signé standard (UAE PASS).
    identity_source: str = "id_token"
    acr_values: Optional[str] = None          # niveau d'assurance (UAE PASS : SOP)
    static_discovery: Optional[dict] = None    # endpoints fixes (IdP sans .well-known)


# UAE PASS : SSO national (public + privé EAU). N'expose pas de .well-known/JWKS standard →
# endpoints fixes + identité via userinfo. Environnement stg/prod, override possible.
_UAEPASS_HOSTS = {
    "production": "https://id.uaepass.ae/idshub",
    "staging": "https://stg-id.uaepass.ae/idshub",
}
# acr web par défaut (SOP1, niveau « low ») ; scope profil général documenté par UAE PASS.
_UAEPASS_ACR = "urn:safelayer:tws:policies:authentication:level:low"
_UAEPASS_SCOPE = "urn:uae:digitalid:profile:general"


def _uaepass_issuer() -> str:
    override = os.environ.get("OIDC_UAEPASS_ISSUER")
    if override:
        return override.rstrip("/")
    env = os.environ.get("OIDC_UAEPASS_ENV", "production").lower()
    return _UAEPASS_HOSTS.get(env, _UAEPASS_HOSTS["production"])


def _uaepass_discovery(issuer: str) -> dict:
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "userinfo_endpoint": f"{issuer}/userinfo",
        "end_session_endpoint": f"{issuer}/logout",
    }


def _issuer_for(key: str) -> Optional[str]:
    """Issuer preset pour les providers connus (override possible par env)."""
    override = os.environ.get(f"OIDC_{key.upper()}_ISSUER")
    if override:
        return override.rstrip("/")
    if key == "google":
        return "https://accounts.google.com"
    if key == "microsoft":
        tenant = os.environ.get("OIDC_MICROSOFT_TENANT", "common")
        return f"https://login.microsoftonline.com/{tenant}/v2.0"
    if key == "uaepass":
        return _uaepass_issuer()
    return None


def get_provider(key: str) -> Optional[Provider]:
    """Provider configuré, ou None si client_id/secret absents (= non activé)."""
    key = key.lower()
    cid = os.environ.get(f"OIDC_{key.upper()}_CLIENT_ID")
    csec = os.environ.get(f"OIDC_{key.upper()}_CLIENT_SECRET")
    issuer = _issuer_for(key)
    if not cid or not csec or not issuer:
        return None
    if key == "uaepass":
        # UAE PASS : identité via userinfo (pas de id_token signé), endpoints fixes, acr SOP.
        return Provider(key, issuer, cid, csec, scopes=_UAEPASS_SCOPE,
                        identity_source="userinfo", acr_values=_UAEPASS_ACR,
                        static_discovery=_uaepass_discovery(issuer))
    return Provider(key, issuer, cid, csec)


def enabled_providers() -> list[str]:
    """Clés des providers activés (pour piloter les boutons SSO du front)."""
    return [k for k in ("google", "microsoft", "uaepass", "generic")
            if get_provider(k) is not None]


# --- Discovery (cache process : les endpoints d'un IdP ne bougent pas) ---

_disco_cache: dict[str, dict] = {}


def discovery(provider: Provider) -> dict:
    # IdP sans .well-known (UAE PASS) : endpoints fixes fournis par le provider.
    if provider.static_discovery is not None:
        return provider.static_discovery
    if provider.issuer not in _disco_cache:
        url = f"{provider.issuer}/.well-known/openid-configuration"
        r = httpx.get(url, timeout=_HTTP_TIMEOUT)
        r.raise_for_status()
        _disco_cache[provider.issuer] = r.json()
    return _disco_cache[provider.issuer]


def authorize_url(provider: Provider, redirect_uri: str, state: str,
                  *, scopes: Optional[str] = None, nonce: Optional[str] = None) -> str:
    d = discovery(provider)
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes or provider.scopes,
        "state": state,
    }
    # nonce : lie la requête d'autorisation au ID token renvoyé (anti-rejeu). Revérifié
    # dans validate_id_token. On le passe systématiquement quand on en a un.
    if nonce:
        params["nonce"] = nonce
    # acr_values : niveau d'assurance exigé (UAE PASS : SOP). Posé par le provider.
    if provider.acr_values:
        params["acr_values"] = provider.acr_values
    # access_type=offline + prompt=consent : nécessaire pour obtenir le consentement complet
    # (et un refresh token) sur les scopes admin demandés à l'onboarding.
    if scopes:
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    return f"{d['authorization_endpoint']}?{urlencode(params)}"


def exchange_code(provider: Provider, code: str, redirect_uri: str) -> dict:
    d = discovery(provider)
    r = httpx.post(
        d["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
        },
        headers={"Accept": "application/json"},
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def fetch_userinfo(provider: Provider, access_token: str) -> dict:
    d = discovery(provider)
    r = httpx.get(
        d["userinfo_endpoint"],
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


# --- Validation cryptographique du ID token (preuve d'identité) -----------------------------
#
# PyJWT + cryptography (RS256/ES256, impossible en stdlib pur) sont importés PARESSEUSEMENT,
# comme google-auth dans le rostering : le module s'importe sans la lib, et les chemins de
# test qui ne valident pas de token n'en dépendent pas.

_jwk_clients: dict = {}  # cache par jwks_uri (les clés d'un IdP changent rarement)


def _jwks_uri(provider: Provider) -> str:
    uri = discovery(provider).get("jwks_uri")
    if not uri:
        raise ValueError("IdP sans jwks_uri : impossible de valider le ID token")
    return uri


def _signing_key(provider: Provider, id_token: str):
    """Clé publique de signature de l'IdP pour ce token (résolue via le `kid` de l'entête).

    Isolée pour être monkeypatchable en test (clé RSA locale, aucun réseau).
    """
    from jwt import PyJWKClient

    uri = _jwks_uri(provider)
    client = _jwk_clients.get(uri)
    if client is None:
        client = _jwk_clients.setdefault(uri, PyJWKClient(uri))
    return client.get_signing_key_from_jwt(id_token).key


class IdTokenError(ValueError):
    """ID token invalide : signature, émetteur, audience, expiration ou nonce."""


def validate_id_token(provider: Provider, id_token: str, *,
                      nonce: Optional[str] = None) -> dict:
    """Valide le ID token et renvoie ses claims. Lève `IdTokenError` sinon.

    Vérifie : signature (RS256/ES256 via JWKS de l'IdP), `iss` = issuer attendu,
    `aud` = notre client_id, `exp`/`iat` (avec tolérance d'horloge), et `nonce` si fourni.
    """
    import jwt

    issuer = discovery(provider).get("issuer") or provider.issuer
    try:
        key = _signing_key(provider, id_token)
        claims = jwt.decode(
            id_token, key,
            algorithms=_ID_TOKEN_ALGS,
            audience=provider.client_id,
            issuer=issuer,
            leeway=_CLOCK_LEEWAY_S,
            options={"require": ["exp", "iat", "aud", "iss"]},
        )
    except Exception as exc:  # PyJWTError, clé introuvable, etc. → message neutre
        raise IdTokenError(f"ID token rejeté : {type(exc).__name__}")
    # nonce : PyJWT ne le valide pas → on le fait explicitement (anti-rejeu).
    if nonce is not None:
        import hmac
        if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            raise IdTokenError("nonce absent ou incohérent (rejeu)")
    return claims


def resolve_identity(provider: Provider, tokens: dict, *,
                     nonce: Optional[str] = None) -> dict:
    """Renvoie les claims d'identité selon la source du provider. Lève `IdTokenError` sinon.

    - `id_token` (défaut, Entra/Google/IdP conformes) : validation cryptographique stricte.
    - `userinfo` (UAE PASS) : pas de id_token signé standard → identité via l'endpoint
      userinfo over TLS, authentifié par l'access_token. Le `state` signé HMAC reste la
      protection anti-CSRF ; le nonce ne s'applique pas (aucun id_token à lier).
    """
    if provider.identity_source == "userinfo":
        access = tokens.get("access_token")
        if not access:
            raise IdTokenError("access_token manquant (flux userinfo)")
        try:
            return fetch_userinfo(provider, access)
        except Exception as exc:
            raise IdTokenError(f"userinfo rejeté : {type(exc).__name__}")
    return validate_id_token(provider, tokens["id_token"], nonce=nonce)


def extract_email(userinfo: dict) -> Optional[str]:
    """Email vérifié de l'utilisateur, ou None si absent / explicitement non vérifié."""
    if userinfo.get("email_verified") is False:
        return None
    email = userinfo.get("email") or userinfo.get("preferred_username")
    return email.lower() if email else None
