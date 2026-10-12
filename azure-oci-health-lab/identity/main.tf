terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    azuread = { source = "hashicorp/azuread", version = "= 3.3.0" }
    oci     = { source = "oracle/oci", version = "= 7.21.0" }
  }
}
provider "azuread" { tenant_id = var.azure_tenant_id }
provider "oci" {
  region              = var.oci_home_region
  config_file_profile = var.oci_admin_profile
}
variable "azure_tenant_id" { type = string }
variable "azure_admin_member_object_ids" { type = set(string) }
variable "github_repository" {
  type    = string
  default = "ApolloJize/Projects"
}
variable "oci_tenancy_ocid" { type = string }
variable "oci_compartment_ocid" { type = string }
variable "oci_home_region" { type = string }
variable "oci_admin_profile" {
  type    = string
  default = "DEFAULT"
}
variable "oci_operator_email" { type = string }
variable "oci_operator_public_key_path" {
  type        = string
  description = "An existing API signing PUBLIC key PEM. Private key is never given to Terraform."
}

data "azuread_client_config" "admin" {}
resource "azuread_group" "db_admins" {
  display_name     = "healthlab-db-admins"
  security_enabled = true
  owners           = [data.azuread_client_config.admin.object_id]
  members          = var.azure_admin_member_object_ids
}
resource "azuread_application" "terraform" {
  display_name = "healthlab-terraform"
  owners       = [data.azuread_client_config.admin.object_id]
}
resource "azuread_service_principal" "terraform" {
  client_id = azuread_application.terraform.client_id
  owners    = [data.azuread_client_config.admin.object_id]
}
resource "azuread_application_federated_identity_credential" "github" {
  application_id = azuread_application.terraform.id
  display_name   = "github-main"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:ref:refs/heads/main"
}
# OCI legacy IAM resources create users/groups in the Default identity domain.
# In a separate identity domain, create the equivalent account there instead.
resource "oci_identity_user" "operator" {
  compartment_id = var.oci_tenancy_ocid
  name           = "healthlab-operator"
  description    = "API operator for the synthetic lab"
  email          = var.oci_operator_email
}
resource "oci_identity_group" "operators" {
  compartment_id = var.oci_tenancy_ocid
  name           = "healthlab-operators"
  description    = "Lab resource operators"
}
resource "oci_identity_user_group_membership" "operator" {
  user_id  = oci_identity_user.operator.id
  group_id = oci_identity_group.operators.id
}
resource "oci_identity_api_key" "operator" {
  user_id   = oci_identity_user.operator.id
  key_value = file(var.oci_operator_public_key_path)
}
resource "oci_identity_policy" "operators" {
  compartment_id = var.oci_tenancy_ocid
  name           = "healthlab-operators"
  description    = "Cloud services and policies confined to the dedicated lab compartment"
  statements = concat(
    [for family in ["virtual-network-family", "instance-family", "volume-family", "autonomous-database-family", "goldengate-family", "integration-instance", "vaults", "keys", "secret-family", "dns", "bastion-family", "policies"] :
    "Allow group ${oci_identity_group.operators.name} to manage ${family} in compartment id ${var.oci_compartment_ocid}"],
    ["Allow group ${oci_identity_group.operators.name} to read instance-images in tenancy",
    "Allow group ${oci_identity_group.operators.name} to inspect availability-domains in tenancy"]
  )
}
output "accounts" {
  value = {
    azure_client_id             = azuread_application.terraform.client_id
    azure_service_principal_id  = azuread_service_principal.terraform.object_id
    azure_entra_admin_object_id = azuread_group.db_admins.object_id
    azure_entra_admin_name      = azuread_group.db_admins.display_name
    oci_user_ocid               = oci_identity_user.operator.id
    oci_api_fingerprint         = oci_identity_api_key.operator.fingerprint
  }
}
