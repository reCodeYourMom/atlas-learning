# =====================================================================
# Atlas — provisioning OCI Always Free (région UAE).
# VM.Standard.A1.Flex (Ampere) + VCN/subnet + security list 22/80/443
# + cloud-init (Docker + bundle + deploy.sh). Tout en free tier.
#
#   terraform init && terraform apply
# Pré-requis : compte OCI (home region UAE), clé API, voir terraform.tfvars.example.
# =====================================================================

terraform {
  required_version = ">= 1.3"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region # ex: me-dubai-1 (UAE East) ou me-abudhabi-1 (UAE Central)
}

# --- Réseau ----------------------------------------------------------
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

resource "oci_core_vcn" "atlas" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "atlas-vcn"
  dns_label      = "atlas"
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.atlas.id
  display_name   = "atlas-igw"
}

resource "oci_core_route_table" "rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.atlas.id
  display_name   = "atlas-rt"
  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

resource "oci_core_security_list" "sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.atlas.id
  display_name   = "atlas-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  # SSH — restreins var.ssh_ingress_cidr à ton IP pour durcir.
  ingress_security_rules {
    protocol = "6" # TCP
    source   = var.ssh_ingress_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }
  # HTTP (ACME/redirection) + HTTPS
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_subnet" "subnet" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.atlas.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "atlas-subnet"
  route_table_id    = oci_core_route_table.rt.id
  security_list_ids = [oci_core_security_list.sl.id]
  dns_label         = "atlas"
}

# --- Image Ubuntu 22.04 pour A1 (ARM) --------------------------------
data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# --- Instance Always Free -------------------------------------------
resource "oci_core_instance" "atlas" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "atlas-prod"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = var.instance_ocpus       # 2 = plafond Always Free (depuis ~15/06/2026)
    memory_in_gbs = var.instance_memory_gbs  # 12 = plafond Always Free (depuis ~15/06/2026)
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.subnet.id
    assign_public_ip = true
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
    # CMK OCI Vault pour le chiffrement at-rest du boot volume (données mineurs).
    # Vide → null → chiffrement par clé gérée Oracle (défaut). Cf. RUNBOOK-BETA §1.
    kms_key_id = var.boot_kms_key_ocid != "" ? var.boot_kms_key_ocid : null
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      app_domain  = var.app_domain
      auth_domain = var.auth_domain
      repo_url    = var.repo_url
    }))
  }
}
