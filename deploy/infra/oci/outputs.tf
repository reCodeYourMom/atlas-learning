# Les deux marches à suivre sont construites en `locals` : un heredoc ne peut pas servir
# directement de branche à un ternaire (HCL attend une expression, pas un bloc littéral).
locals {
  _ip       = oci_core_instance.atlas.public_ip
  _sous_nom = var.demo_domain != "" ? split(".", var.demo_domain)[0] : "demo"

  _etapes_demo = <<-EOT
    1. DNS — UN SEUL enregistrement à ajouter chez le registrar du domaine :
         Type A · Nom "${local._sous_nom}" · Valeur ${local._ip} · TTL 3600
       Ne touche à aucune autre ligne : le domaine racine et son www restent où ils sont.

    2. Attendre la propagation AVANT de déployer. Caddy demande son certificat dès le
       boot, et un échec Let's Encrypt consomme le quota (5 essais par heure et par
       domaine) :
         dig +short ${var.demo_domain}     # doit renvoyer ${local._ip}

    3. Si repo_url était vide, déployer à la main :
         ssh ubuntu@${local._ip}
         cd repo/demo/deploy && DEMO_DOMAIN=${var.demo_domain} ./deploy.sh
       (avec repo_url renseigné, cloud-init l'a déjà fait : voir ~/ATLAS-READY.txt)

    4. Le semis initial tourne au premier boot, ~40 s :
         cd repo/demo/deploy && docker compose logs -f backend

    5. https://${var.demo_domain} — deploy.sh affiche le mot de passe des 5 comptes.
       Remise à zéro entre deux rendez-vous : ./reset.sh
  EOT

  _etapes_prod = <<-EOT
    1. DNS : deux enregistrements A → ${local._ip}
         ${var.app_domain}
         ${var.auth_domain}
    2. Si repo_url était vide : scp le dépôt (atlas-learning/) sur la VM, puis :
         cd atlas-learning/deploy/prod && APP_DOMAIN=${var.app_domain} AUTH_DOMAIN=${var.auth_domain} ./deploy.sh
    3. Caddy émet le TLS automatiquement au 1er accès HTTPS.
  EOT
}

output "public_ip" {
  value       = local._ip
  description = "IP publique de la VM. C'est la valeur à mettre dans l'enregistrement DNS A."
}

output "ssh" {
  value       = "ssh ubuntu@${local._ip}"
  description = "Connexion SSH (clé fournie via ssh_public_key_path)."
}

output "dns_record" {
  description = "L'enregistrement DNS à créer chez le registrar."
  value = (var.deploy_profile == "demo"
    ? "Type A · Nom \"${local._sous_nom}\" · Valeur ${local._ip} · TTL 3600"
    : "Deux A records (${var.app_domain}, ${var.auth_domain}) → ${local._ip}"
  )
}

output "next_steps" {
  description = "Marche à suivre après l'apply, selon le profil de déploiement."
  value       = var.deploy_profile == "demo" ? local._etapes_demo : local._etapes_prod
}
