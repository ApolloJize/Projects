resource "oci_database_autonomous_database" "warehouse" {
  compartment_id              = var.oci_compartment_ocid
  db_name                     = var.prefix
  display_name                = "${var.prefix}-adw"
  db_workload                 = "DW"
  compute_model               = "ECPU"
  compute_count               = 2
  data_storage_size_in_tbs    = 1
  license_model               = "LICENSE_INCLUDED"
  admin_password              = random_password.credentials["adw-admin"].result
  is_auto_scaling_enabled     = false
  is_free_tier                = false
  subnet_id                   = oci_core_subnet.private.id
  nsg_ids                     = [oci_core_network_security_group.services.id]
  private_endpoint_label      = "${var.prefix}adw"
  is_mtls_connection_required = false
}
resource "oci_identity_dynamic_group" "gg" {
  provider       = oci.home
  compartment_id = var.oci_tenancy_ocid
  name           = "${var.prefix}-gg"
  description    = "GoldenGate deployments in this lab compartment"
  matching_rule  = "ALL {resource.type = 'goldengatedeployment', resource.compartment.id = '${var.oci_compartment_ocid}'}"
}
resource "oci_identity_policy" "gg" {
  provider       = oci.home
  compartment_id = var.oci_compartment_ocid
  name           = "${var.prefix}-gg-vault"
  description    = "GoldenGate password secret access"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.gg.name} to read secret-bundles in compartment id ${var.oci_compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.gg.name} to use keys in compartment id ${var.oci_compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.gg.name} to use vaults in compartment id ${var.oci_compartment_ocid}"
  ]
}
resource "oci_golden_gate_deployment" "lab" {
  for_each                = { source = "DATABASE_MICROSOFT_SQLSERVER", target = "DATABASE_ORACLE" }
  compartment_id          = var.oci_compartment_ocid
  display_name            = "${var.prefix}-${each.key}"
  deployment_type         = each.value
  subnet_id               = oci_core_subnet.private.id
  nsg_ids                 = [oci_core_network_security_group.services.id]
  is_public               = false
  cpu_core_count          = 1
  is_auto_scaling_enabled = false
  license_model           = "LICENSE_INCLUDED"
  ogg_data {
    deployment_name    = "${var.prefix}${each.key}"
    admin_username     = "ggadmin"
    password_secret_id = oci_vault_secret.credentials["gg-admin"].id
    credential_store   = "OGG"
  }
  depends_on = [oci_identity_policy.gg]
}
resource "oci_golden_gate_connection" "source" {
  count                              = var.enable_gg_connections ? 1 : 0
  compartment_id                     = var.oci_compartment_ocid
  display_name                       = "azure-sqlmi"
  connection_type                    = "MICROSOFT_SQLSERVER"
  technology_type                    = "AZURE_SQLSERVER_MANAGED_INSTANCE"
  host                               = azurerm_mssql_managed_instance.source.fqdn
  port                               = 1433
  database_name                      = azurerm_mssql_managed_database.source.name
  username                           = "gg_reader"
  password_secret_id                 = oci_vault_secret.credentials["gg-source"].id
  security_protocol                  = "TLS"
  should_validate_server_certificate = true
  ssl_ca                             = var.sqlmi_ca_pem_path == null ? null : filebase64(var.sqlmi_ca_pem_path)
  routing_method                     = "DEDICATED_ENDPOINT"
  subnet_id                          = oci_core_subnet.private.id
  nsg_ids                            = [oci_core_network_security_group.services.id]
}
locals {
  adw_tls_dsn = one([for p in oci_database_autonomous_database.warehouse.connection_strings[0].profiles : p.value if p.tls_authentication == "SERVER" && p.consumer_group == "LOW"])
}
resource "oci_golden_gate_connection" "target" {
  count              = var.enable_gg_connections ? 1 : 0
  compartment_id     = var.oci_compartment_ocid
  display_name       = "adw-raw"
  connection_type    = "ORACLE"
  technology_type    = "OCI_AUTONOMOUS_DATABASE"
  database_id        = oci_database_autonomous_database.warehouse.id
  connection_string  = local.adw_tls_dsn
  username           = "GGADMIN"
  password_secret_id = oci_vault_secret.credentials["gg-target"].id
  routing_method     = "DEDICATED_ENDPOINT"
  subnet_id          = oci_core_subnet.private.id
  nsg_ids            = [oci_core_network_security_group.services.id]
}
resource "oci_golden_gate_connection_assignment" "source" {
  count         = var.enable_gg_connections ? 1 : 0
  connection_id = oci_golden_gate_connection.source[0].id
  deployment_id = oci_golden_gate_deployment.lab["source"].id
}
resource "oci_golden_gate_connection_assignment" "target" {
  count         = var.enable_gg_connections ? 1 : 0
  connection_id = oci_golden_gate_connection.target[0].id
  deployment_id = oci_golden_gate_deployment.lab["target"].id
}
resource "oci_integration_integration_instance" "lab" {
  compartment_id            = var.oci_compartment_ocid
  display_name              = var.prefix
  integration_instance_type = "STANDARDX"
  is_byol                   = false
  message_packs             = 1
  domain_id                 = var.oci_identity_domain_ocid
  is_file_server_enabled    = false
  is_visual_builder_enabled = false
  network_endpoint_details {
    network_endpoint_type          = "PUBLIC"
    allowlisted_http_ips           = [var.operator_cidr, "${oci_core_nat_gateway.lab.nat_ip}/32"]
    is_integration_vcn_allowlisted = true
  }
  # The provider exposes the outbound private endpoint as a read-only field.
  # scripts/configure_oic_endpoint.py creates it through the supported OCI API.
}
data "oci_identity_availability_domains" "lab" { compartment_id = var.oci_tenancy_ocid }
resource "oci_core_instance" "runner" {
  compartment_id      = var.oci_compartment_ocid
  availability_domain = data.oci_identity_availability_domains.lab.availability_domains[0].name
  display_name        = "${var.prefix}-runner"
  shape               = "VM.Standard.E4.Flex"
  shape_config {
    ocpus         = 1
    memory_in_gbs = 8
  }
  source_details {
    source_type = "image"
    source_id   = var.runner_image_ocid
  }
  create_vnic_details {
    subnet_id        = oci_core_subnet.private.id
    assign_public_ip = false
    nsg_ids          = [oci_core_network_security_group.services.id]
    hostname_label   = "runner"
  }
  metadata = { ssh_authorized_keys = var.runner_ssh_public_key }
}
resource "oci_bastion_bastion" "runner" {
  compartment_id               = var.oci_compartment_ocid
  bastion_type                 = "STANDARD"
  name                         = var.prefix
  target_subnet_id             = oci_core_subnet.private.id
  client_cidr_block_allow_list = [var.operator_cidr]
  max_session_ttl_in_seconds   = 10800
}
resource "oci_identity_dynamic_group" "runner" {
  provider       = oci.home
  compartment_id = var.oci_tenancy_ocid
  name           = "${var.prefix}-runner"
  description    = "This runner only"
  matching_rule  = "ALL {instance.id = '${oci_core_instance.runner.id}'}"
}
resource "oci_identity_policy" "runner" {
  provider       = oci.home
  compartment_id = var.oci_compartment_ocid
  name           = "${var.prefix}-runner"
  description    = "Lab bootstrap, reporting, and GenAI"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.runner.name} to read secret-bundles in compartment id ${var.oci_compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.runner.name} to use generative-ai-family in compartment id ${var.oci_compartment_ocid}"
  ]
}
