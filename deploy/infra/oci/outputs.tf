output "public_ip" {
  value       = oci_core_instance.atlas.public_ip
  description = "IP publique de la VM. Pointe app_domain et auth_domain dessus (DNS A), ou utilise <IP>.nip.io."
}

output "ssh" {
  value       = "ssh ubuntu@${oci_core_instance.atlas.public_ip}"
  description = "Connexion SSH (clé fournie via ssh_public_key_path)."
}

output "next_steps" {
  value = <<-EOT
    1. DNS : crée 2 enregistrements A → ${oci_core_instance.atlas.public_ip}
         ${var.app_domain}
         ${var.auth_domain}
       (ou démarre en ${oci_core_instance.atlas.public_ip}.nip.io sans acheter de domaine)
    2. Si repo_url était vide : scp le dossier 04_code/ sur la VM, puis :
         cd 04_code/deploy/prod && APP_DOMAIN=${var.app_domain} AUTH_DOMAIN=${var.auth_domain} ./deploy.sh
    3. Caddy émet le TLS automatiquement au 1er accès HTTPS.
  EOT
}
