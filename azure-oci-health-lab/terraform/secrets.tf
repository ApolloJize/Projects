resource "random_password" "credentials" {
  for_each         = toset(["azure-sql-admin", "synapse-admin", "adw-admin", "gg-admin", "gg-source", "gg-target", "raw-app", "pipeline-app", "oic-app", "report-app"])
  length           = 28
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
  override_special = "_#"
}
resource "oci_kms_vault" "lab" {
  compartment_id = var.oci_compartment_ocid
  display_name   = "${var.prefix}-vault"
  vault_type     = "DEFAULT"
}
resource "oci_kms_key" "lab" {
  compartment_id      = var.oci_compartment_ocid
  display_name        = "${var.prefix}-key"
  management_endpoint = oci_kms_vault.lab.management_endpoint
  protection_mode     = "SOFTWARE"
  key_shape {
    algorithm = "AES"
    length    = 32
  }
}
resource "oci_vault_secret" "credentials" {
  for_each       = random_password.credentials
  compartment_id = var.oci_compartment_ocid
  vault_id       = oci_kms_vault.lab.id
  key_id         = oci_kms_key.lab.id
  secret_name    = "${var.prefix}-${each.key}"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(each.value.result)
  }
}
resource "azurerm_key_vault" "lab" {
  name                       = "${var.prefix}-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.lab.name
  location                   = var.azure_location
  tenant_id                  = var.azure_tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  access_policy {
    tenant_id          = var.azure_tenant_id
    object_id          = data.azurerm_client_config.current.object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Recover", "Purge"]
  }
  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
    ip_rules       = [var.operator_cidr]
  }
}
resource "azurerm_key_vault_secret" "azure" {
  for_each     = toset(["azure-sql-admin", "synapse-admin"])
  name         = each.key
  value        = random_password.credentials[each.key].result
  key_vault_id = azurerm_key_vault.lab.id
}
