variable "prefix" {
  type    = string
  default = "healthlab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,11}$", var.prefix))
    error_message = "Use 3–12 lowercase letters or digits, starting with a letter."
  }
}
variable "azure_subscription_id" { type = string }
variable "azure_tenant_id" { type = string }
variable "azure_location" {
  type    = string
  default = "eastus"
}
variable "azure_entra_admin_object_id" {
  type        = string
  description = "Object ID of an existing Entra group that administers the SQL services."
}
variable "azure_entra_admin_name" { type = string }
variable "operator_cidr" {
  type        = string
  description = "Your public IPv4 address with /32, for Bastion, OIC, and Key Vault access."
  validation {
    condition     = can(cidrhost(var.operator_cidr, 0)) && endswith(var.operator_cidr, "/32")
    error_message = "Supply one operator IPv4 address as a /32."
  }
}
variable "oci_tenancy_ocid" { type = string }
variable "oci_compartment_ocid" { type = string }
variable "oci_identity_domain_ocid" { type = string }
variable "oci_region" {
  type    = string
  default = "us-ashburn-1"
}
variable "oci_home_region" {
  type    = string
  default = "us-ashburn-1"
}
variable "oci_config_profile" {
  type    = string
  default = "HEALTHLAB"
}
variable "runner_image_ocid" {
  type        = string
  description = "Ubuntu 22.04 x86_64 platform image OCID in oci_region."
}
variable "runner_ssh_public_key" {
  type        = string
  description = "Public SSH key only. The private key stays on your machine."
}
variable "azure_cidr" {
  type    = string
  default = "10.50.0.0/16"
}
variable "oci_cidr" {
  type    = string
  default = "10.60.0.0/16"
}
variable "enable_gg_connections" {
  type        = bool
  default     = false
  description = "Enable after database users, CDC and target tables have been bootstrapped."
}
variable "sqlmi_ca_pem_path" {
  type        = string
  default     = null
  description = "Optional PEM CA chain for SQL MI certificate validation. Never disable validation."
}

locals {
  tags        = { project = var.prefix, purpose = "synthetic-data-lab" }
  azure_mi    = cidrsubnet(var.azure_cidr, 8, 1)
  azure_pe    = cidrsubnet(var.azure_cidr, 8, 2)
  azure_dns   = cidrsubnet(var.azure_cidr, 12, 48)
  azure_gw    = cidrsubnet(var.azure_cidr, 11, 0)
  oci_private = cidrsubnet(var.oci_cidr, 8, 1)
}
