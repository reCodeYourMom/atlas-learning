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
variable "ssh_ingress_cidr" {
  type        = string
  description = "CIDR autorisé pour SSH (22). Mets ton IP/32 pour durcir."
  default     = "0.0.0.0/0"
}

# --- Application -----------------------------------------------------
variable "app_domain" {
  type        = string
  description = "Sous-domaine front+API (ex: app.tondomaine.com). Pour démarrer sans domaine : <IP>.nip.io après 1er apply."
}
variable "auth_domain" {
  type        = string
  description = "Sous-domaine Keycloak (ex: auth.tondomaine.com)."
}
variable "repo_url" {
  type        = string
  description = "URL git du repo (contenant 04_code/). Vide = cloud-init prépare Docker seulement, tu copies le bundle en scp puis lances deploy.sh."
  default     = ""
}
