data "azurerm_client_config" "current" {}
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}
resource "azurerm_resource_group" "lab" {
  name     = "${var.prefix}-rg"
  location = var.azure_location
  tags     = local.tags
}
resource "azurerm_virtual_network" "lab" {
  name                = "${var.prefix}-vnet"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  address_space       = [var.azure_cidr]
}
resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = [local.azure_gw]
}
resource "azurerm_subnet" "mi" {
  name                 = "sqlmi"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = [local.azure_mi]
  delegation {
    name = "sql-managed-instance"
    service_delegation {
      name    = "Microsoft.Sql/managedInstances"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action", "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action", "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"]
    }
  }
}
resource "azurerm_subnet" "pe" {
  name                 = "private-endpoints"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = [local.azure_pe]
}
resource "azurerm_subnet" "dns" {
  name                 = "dns-inbound"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = [local.azure_dns]
  delegation {
    name = "dns-resolver"
    service_delegation {
      name    = "Microsoft.Network/dnsResolvers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}
resource "azurerm_private_dns_resolver" "lab" {
  name                = "${var.prefix}-dns"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  virtual_network_id  = azurerm_virtual_network.lab.id
}
resource "azurerm_private_dns_resolver_inbound_endpoint" "lab" {
  name                    = "inbound"
  private_dns_resolver_id = azurerm_private_dns_resolver.lab.id
  location                = var.azure_location
  ip_configurations {
    private_ip_allocation_method = "Dynamic"
    subnet_id                    = azurerm_subnet.dns.id
  }
}
resource "azurerm_network_security_group" "mi" {
  name                = "${var.prefix}-sqlmi-nsg"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  security_rule {
    name                       = "sql-from-oci"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "1433"
    source_address_prefix      = local.oci_private
    destination_address_prefix = local.azure_mi
  }
  # SQL MI adds and owns its mandatory network intent rules. Keep them intact.
}
resource "azurerm_subnet_network_security_group_association" "mi" {
  subnet_id                 = azurerm_subnet.mi.id
  network_security_group_id = azurerm_network_security_group.mi.id
}
resource "azurerm_route_table" "mi" {
  name                = "${var.prefix}-sqlmi-routes"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  route {
    name           = "oci"
    address_prefix = var.oci_cidr
    next_hop_type  = "VirtualNetworkGateway"
  }
}
resource "azurerm_subnet_route_table_association" "mi" {
  subnet_id      = azurerm_subnet.mi.id
  route_table_id = azurerm_route_table.mi.id
}
resource "azurerm_mssql_managed_instance" "source" {
  name                         = "${var.prefix}-mi"
  resource_group_name          = azurerm_resource_group.lab.name
  location                     = var.azure_location
  subnet_id                    = azurerm_subnet.mi.id
  administrator_login          = "labadmin"
  administrator_login_password = random_password.credentials["azure-sql-admin"].result
  license_type                 = "LicenseIncluded"
  sku_name                     = "GP_Gen5"
  vcores                       = 4
  storage_size_in_gb           = 128
  public_data_endpoint_enabled = false
  minimum_tls_version          = "1.2"
  proxy_override               = "Proxy"
  identity { type = "SystemAssigned" }
  depends_on = [azurerm_subnet_network_security_group_association.mi, azurerm_subnet_route_table_association.mi]
}
resource "azurerm_mssql_managed_database" "source" {
  name                = "healthsource"
  managed_instance_id = azurerm_mssql_managed_instance.source.id
}
resource "azurerm_mssql_managed_instance_active_directory_administrator" "admin" {
  managed_instance_id = azurerm_mssql_managed_instance.source.id
  login_username      = var.azure_entra_admin_name
  object_id           = var.azure_entra_admin_object_id
  tenant_id           = var.azure_tenant_id
}
resource "azurerm_storage_account" "lake" {
  name                            = "${var.prefix}${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.lab.name
  location                        = var.azure_location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  # No records are stored here by the demo; this is Synapse's required default lake.
  # Data-plane auth is still required. See docs/setup.md before hardening network ACLs.
}
resource "azurerm_storage_data_lake_gen2_filesystem" "lake" {
  name               = "synapse"
  storage_account_id = azurerm_storage_account.lake.id
}
resource "azurerm_synapse_workspace" "warehouse" {
  name                                 = "${var.prefix}-${random_string.suffix.result}"
  resource_group_name                  = azurerm_resource_group.lab.name
  location                             = var.azure_location
  storage_data_lake_gen2_filesystem_id = azurerm_storage_data_lake_gen2_filesystem.lake.id
  sql_administrator_login              = "labadmin"
  sql_administrator_login_password     = random_password.credentials["synapse-admin"].result
  managed_virtual_network_enabled      = true
  public_network_access_enabled        = false
  identity { type = "SystemAssigned" }
}
resource "azurerm_synapse_workspace_aad_admin" "admin" {
  synapse_workspace_id = azurerm_synapse_workspace.warehouse.id
  login                = var.azure_entra_admin_name
  object_id            = var.azure_entra_admin_object_id
  tenant_id            = var.azure_tenant_id
}
resource "azurerm_role_assignment" "synapse_lake" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_synapse_workspace.warehouse.identity[0].principal_id
}
resource "azurerm_synapse_sql_pool" "warehouse" {
  name                 = "healthdw"
  synapse_workspace_id = azurerm_synapse_workspace.warehouse.id
  sku_name             = "DW100c"
  create_mode          = "Default"
  storage_account_type = "LRS"
}
resource "azurerm_private_dns_zone" "synapse" {
  name                = "privatelink.sql.azuresynapse.net"
  resource_group_name = azurerm_resource_group.lab.name
}
resource "azurerm_private_dns_zone_virtual_network_link" "synapse" {
  name                  = "lab"
  resource_group_name   = azurerm_resource_group.lab.name
  private_dns_zone_name = azurerm_private_dns_zone.synapse.name
  virtual_network_id    = azurerm_virtual_network.lab.id
}
resource "azurerm_private_endpoint" "synapse" {
  name                = "${var.prefix}-synapse-sql"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  subnet_id           = azurerm_subnet.pe.id
  private_service_connection {
    name                           = "sql"
    private_connection_resource_id = azurerm_synapse_workspace.warehouse.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "sql"
    private_dns_zone_ids = [azurerm_private_dns_zone.synapse.id]
  }
}
