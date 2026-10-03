"""Garde-fous du realm Keycloak PROD + docs de déploiement (revue adversariale 2026-07-07).

Findings couverts :
  - comptes démo : plus JAMAIS de mot de passe statique versionné (ChangeMe1234!) ;
    placeholder injecté par deploy.sh, credential temporary + UPDATE_PASSWORD forcé ;
  - TOTP realm-level : CONFIGURE_TOTP en required action PAR DÉFAUT (defaultAction) —
    les vrais utilisateurs du pilote créés via la console y sont soumis, pas seulement
    les 3 comptes démo ;
  - README-DEPLOY : la purge de rétention est LIVRÉE (plus de « lot séparé ») et les
    crons retention/quarantine sont documentés à côté de backup.cron ;
  - brute force (revue 2026-07-08) : sans "bruteForceProtected": true, Keycloak
    (défaut = false) accepte des essais de mot de passe ILLIMITÉS sur les usernames
    versionnés (*@demo.atlas) et les futurs comptes staff — protection exigée sur le
    realm prod ET le realm de dérisquage (cohérence).

Tests de FICHIERS (pas de Keycloak lancé) : ils verrouillent le contrat du template
et des scripts contre les régressions — même esprit que le gotcha test@demo.atlas.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "prod"
TEMPLATE = DEPLOY / "keycloak" / "atlas-realm.template.json"
DERISK = DEPLOY / "keycloak" / "derisk" / "atlas-realm.derisk.json"

DEMO_PASSWORD_PLACEHOLDER = "CHANGE_ME_demo_password"


def _realm() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def _derisk_realm() -> dict:
    return json.loads(DERISK.read_text(encoding="utf-8"))


def test_aucun_mot_de_passe_statique_dans_le_template():
    raw = TEMPLATE.read_text(encoding="utf-8")
    assert "ChangeMe" not in raw, "mot de passe statique versionné réintroduit"
    for user in _realm().get("users", []):
        for cred in user.get("credentials", []):
            # seul le placeholder (substitué par deploy.sh) est admis
            assert cred["value"] == DEMO_PASSWORD_PLACEHOLDER, (
                f"credential en clair pour {user['username']}"
            )
            # temporary:true → Keycloak FORCE le changement au 1er login
            assert cred.get("temporary") is True, (
                f"credential non temporaire pour {user['username']}"
            )


def test_comptes_demo_forcent_update_password_et_totp():
    users = _realm().get("users", [])
    assert users, "comptes démo attendus dans le realm prod"
    for user in users:
        actions = user.get("requiredActions", [])
        assert "UPDATE_PASSWORD" in actions, f"{user['username']} : pas d'UPDATE_PASSWORD"
        assert "CONFIGURE_TOTP" in actions, f"{user['username']} : pas de CONFIGURE_TOTP"


def test_totp_impose_au_niveau_realm_pas_seulement_par_user():
    # Sans defaultAction:true, le browser flow Keycloak (« Conditional OTP ») laisse
    # tout utilisateur créé APRÈS l'import se connecter au mot de passe seul.
    actions = {a["alias"]: a for a in _realm().get("requiredActions", [])}
    totp = actions.get("CONFIGURE_TOTP")
    assert totp is not None, "requiredActions realm-level sans CONFIGURE_TOTP"
    assert totp.get("enabled") is True
    assert totp.get("defaultAction") is True, (
        "CONFIGURE_TOTP doit être defaultAction:true (MFA staff sur données de mineurs)"
    )
    # UPDATE_PASSWORD doit rester disponible (requis par les credentials temporaires)
    upd = actions.get("UPDATE_PASSWORD")
    assert upd is not None and upd.get("enabled") is True


def test_pas_de_compte_smoke_ni_ropc_dans_le_realm_prod():
    # verrouille les fixes précédents (revue sécu 2026-07-07)
    realm = _realm()
    assert all(u["username"] != "test@demo.atlas" for u in realm.get("users", []))
    for client in realm.get("clients", []):
        assert client.get("directAccessGrantsEnabled") is False


def test_brute_force_protection_activee_sur_les_deux_realms():
    # Défaut Keycloak = bruteForceProtected:false → essais de mot de passe ILLIMITÉS
    # sur des usernames connus (versionnés dans ce repo). On exige la protection sur
    # le realm PROD et, par cohérence, sur le realm de dérisquage local.
    for name, realm in (("prod", _realm()), ("derisk", _derisk_realm())):
        assert realm.get("bruteForceProtected") is True, (
            f"realm {name} : bruteForceProtected absent/false (essais de mdp illimités)"
        )
        # lockout TEMPORAIRE : un lockout permanent permettrait un DoS de compte
        # (verrouiller un enseignant en spammant son username connu)
        assert realm.get("permanentLockout") is False, (
            f"realm {name} : permanentLockout doit être false (DoS de compte sinon)"
        )
        # paramètres raisonnables : seuil bas mais humain, attente croissante bornée
        assert 1 <= realm.get("failureFactor", 0) <= 10, (
            f"realm {name} : failureFactor hors [1,10]"
        )
        assert realm.get("waitIncrementSeconds", 0) >= 30, (
            f"realm {name} : waitIncrementSeconds trop court pour ralentir un brute force"
        )
        assert realm.get("maxFailureWaitSeconds", 0) >= realm["waitIncrementSeconds"], (
            f"realm {name} : maxFailureWaitSeconds < waitIncrementSeconds (incohérent)"
        )
        assert realm.get("maxDeltaTimeSeconds", 0) >= 3600, (
            f"realm {name} : fenêtre de comptage des échecs trop courte"
        )


def test_deploy_sh_genere_et_injecte_le_mdp_demo():
    sh = (DEPLOY / "deploy.sh").read_text(encoding="utf-8")
    assert "ensure_secret DEMO_ACCOUNTS_PASSWORD" in sh
    assert DEMO_PASSWORD_PLACEHOLDER in sh          # substitution sed vers le realm runtime
    assert "ChangeMe1234!" not in sh                # plus de mdp publié dans les logs


def test_readme_deploy_documente_purge_et_crons():
    md = (DEPLOY / "README-DEPLOY.md").read_text(encoding="utf-8")
    assert "lot séparé" not in md                   # la purge est livrée, pas « à venir »
    assert "purge_retention.py" in md
    assert "retention.cron" in md
    assert "quarantine.cron" in md
    assert "backup.cron" in md
    assert "ChangeMe1234!" not in md                # plus de mdp publié dans la doc
    # les fichiers cron documentés existent bien dans le bundle
    assert (DEPLOY / "retention.cron").exists()
    assert (DEPLOY / "quarantine.cron").exists()
    assert (DEPLOY / "backup.cron").exists()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests OK")
