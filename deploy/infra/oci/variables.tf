# --- Authentification API OCI (cf. terraform.tfvars.example) ---------
variable "tenancy_ocid" { type = string }
variable "user_ocid" { type = string }
variable "fingerprint" { type = string }
variable "private_key_path" {
  type        = string
  description = "Chemin local vers la clé privée API OCI (PEM)."
}
variable "compartment_ocid" {
  type        = string
  description = "Compartment cible. Peut être égal au tenancy_ocid (racine)."
}

variable "region" {
  type        = string
  description = "Région UAE : me-abudhabi-1 (UAE Central) ou me-dubai-1 (UAE East). DOIT être ta home region pour l'Always Free."
  default     = "me-abudhabi-1" # home region choisie à l'inscription : UAE Central (Abu Dhabi)
}

# --- Instance Always Free -------------------------------------------
# ⚠ Depuis ~15 juin 2026, le plafond Always Free A1 est 2 OCPU / 12 Go TOTAL
# (avant : 4/24). On dimensionne pile au plafond pour rester à 0 €.
variable "instance_ocpus" {
  type    = number
  default = 2
}
variable "instance_memory_gbs" {
  type    = number
  default = 12
}

variable "ssh_public_key_path" {
  type        = string
  description = "Clé publique SSH déposée sur la VM (ex: ~/.ssh/id_ed25519.pub)."
}

# --- Chiffrement at-rest (données mineurs — cf. RUNBOOK-BETA §1) ------
# OCID d'une Customer-Managed Key (OCI Vault) pour chiffrer le boot volume
# À LA CRÉATION (préférable au rétrofit console qui re-chiffre). Vide = clé
# gérée par Oracle (chiffré par défaut, mais Oracle détient la clé).
variable "boot_kms_key_ocid" {
  type        = string
  description = "OCID de la CMK OCI Vault pour le boot volume. Vide = clé Oracle par défaut."
  default     = ""
}
variable "ssh_ingress_cidr" {
  type        = string
  description = "CIDR autorisé pour SSH (22). Mets ton IP/32 pour durcir."
  default     = "0.0.0.0/0"
}

# --- Application -----------------------------------------------------
# Deux profils de déploiement :
#   "demo" (défaut) → demo/deploy : UN sous-domaine, sans Keycloak, connexion par mot de
#                     passe partagé. C'est la stack des rendez-vous commerciaux.
#   "prod"          → deploy/prod : deux sous-domaines, SSO Keycloak + TOTP. Pour un pilote
#                     avec de vraies données d'élèves.
variable "deploy_profile" {
  type        = string
  description = "\"demo\" (un sous-domaine, sans Keycloak) ou \"prod\" (SSO Keycloak)."
  default     = "demo"

  validation {
    condition     = contains(["demo", "prod"], var.deploy_profile)
    error_message = "deploy_profile doit valoir \"demo\" ou \"prod\"."
  }
}

variable "demo_domain" {
  type        = string
  description = "Profil demo : LE sous-domaine de la démo (ex: demo.atlaslearning.ae)."
  default     = ""
}

variable "app_domain" {
  type        = string
  description = "Profil prod : sous-domaine front+API (ex: app.tondomaine.com)."
  default     = ""
}
variable "auth_domain" {
  type        = string
  description = "Profil prod : sous-domaine Keycloak (ex: auth.tondomaine.com)."
  default     = ""
}
variable "repo_url" {
  type        = string
  description = "URL git du repo. Vide = cloud-init prépare Docker seulement, tu copies le bundle en scp puis lances deploy.sh."
  default     = ""
}

# Garde-fou : un profil sans son (ses) domaine(s) produirait une VM qui démarre, un Caddy
# qui ne sait pas quel certificat demander, et une démo silencieusement inaccessible.
resource "terraform_data" "verifie_domaines" {
  lifecycle {
    precondition {
      condition = (
        var.deploy_profile == "demo"
        ? var.demo_domain != ""
        : var.app_domain != "" && var.auth_domain != ""
      )
      error_message = "Profil \"demo\" : renseigne demo_domain. Profil \"prod\" : renseigne app_domain ET auth_domain."
    }
  }
}
