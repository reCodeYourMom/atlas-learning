# Google Cloud — config réalisée (Atlas Learning)

Configuré le 2026-06-21 via la console, compte nassimboughazi@gmail.com.

## Ressources créées

| Élément | Valeur |
|---|---|
| Projet GCP | **Atlas Learning** — ID `atlas-learning-500120` |
| API activées | Admin SDK API, Google Classroom API |
| Service account | `atlas-rostering@atlas-learning-500120.iam.gserviceaccount.com` |
| SA — clé JSON | Créée + téléchargée (dans ~/Téléchargements). État : Active |
| SA — ID client OAuth2 (délégation) | `118253211458052923043` |
| Consent screen | App « Atlas Learning », audience **Externe**, mode **test** |
| OAuth client web | « Atlas Web (login + onboarding) » |
| OIDC_GOOGLE_CLIENT_ID | `1044384395682-r6hd96bc1jo5jdt93ji1otg2si0lug9m.apps.googleusercontent.com` |
| OIDC_GOOGLE_CLIENT_SECRET | À copier depuis la console (non extrait ici) |
| Redirect URIs (TEMP) | `http://localhost:8000/api/oauth/google/callback` + `.../api/onboarding/google/callback` |

## Scopes déclarés (lecture seule)
- `admin.directory.user.readonly` (sensible)
- `admin.directory.group.readonly` (sensible)
- `admin.directory.group.member.readonly` (sensible)
- `admin.directory.orgunit.readonly` (sensible)
- `classroom.guardianlinks.students.readonly`

## À finaliser (toi / IT admin)

1. **Client secret** : Console > Google Auth Platform > Clients > « Atlas Web » →
   copier le secret → OCI Vault → `OIDC_GOOGLE_CLIENT_SECRET`.
2. **Clé SA** : déplacer le `.json` des Téléchargements vers OCI Vault → `GOOGLE_SA_KEY_FILE` ;
   supprimer la copie locale.
3. **Délégation domain-wide** (côté IT admin client, console Workspace) :
   autoriser le client `118253211458052923043` avec les 5 scopes ci-dessus.
4. **Domaine prod** : quand fixé, remplacer les redirect URIs localhost par le vrai
   domaine + mettre à jour `OIDC_REDIRECT_BASE` / `WEB_BASE_URL`.
5. **Vérification OAuth Google** (§5 runbook) : app en mode test → publier + lancer la
   revue Google des scopes sensibles (`admin.directory.*`). Délai plusieurs semaines.
   Tant que non vérifié : seuls les utilisateurs de test listés peuvent se connecter.
6. **Marketplace app** (§3.3) : listing privé à créer pour l'installation par domaine.
7. **Postmark** (§3.6) : non traité ici (hors Google Cloud).
