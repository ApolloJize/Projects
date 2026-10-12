output "connections" {
  description = "Non-secret runtime configuration. Passwords remain in Vault."
  value = {
    OCI_REGION           = var.oci_region
    OCI_COMPARTMENT_OCID = var.oci_compartment_ocid
    OCI_VAULT_OCID       = oci_kms_vault.lab.id
    SECRET_PREFIX        = var.prefix
    SQLMI_HOST           = azurerm_mssql_managed_instance.source.fqdn
    SQLMI_DATABASE       = azurerm_mssql_managed_database.source.name
    SYNAPSE_HOST         = "${azurerm_synapse_workspace.warehouse.name}.sql.azuresynapse.net"
    SYNAPSE_DATABASE     = azurerm_synapse_sql_pool.warehouse.name
    ADW_DSN              = local.adw_tls_dsn
    ADW_OCID             = oci_database_autonomous_database.warehouse.id
    OIC_INSTANCE_OCID    = oci_integration_integration_instance.lab.id
    OIC_BASE_URL         = oci_integration_integration_instance.lab.instance_url
    OIC_SUBNET_OCID      = oci_core_subnet.private.id
    OIC_NSG_OCID         = oci_core_network_security_group.services.id
  }
}
output "access" {
  value = {
    runner_ip    = oci_core_instance.runner.private_ip
    bastion_ocid = oci_bastion_bastion.runner.id
    azure_vpn_ip = azurerm_public_ip.vpn.ip_address
    gg_urls      = { for name, deployment in oci_golden_gate_deployment.lab : name => deployment.deployment_url }
    key_vault    = azurerm_key_vault.lab.vault_uri
  }
}
