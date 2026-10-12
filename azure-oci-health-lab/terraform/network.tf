resource "azurerm_public_ip" "vpn" {
  name                = "${var.prefix}-vpn-ip"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  allocation_method   = "Static"
  sku                 = "Standard"
}
resource "azurerm_virtual_network_gateway" "vpn" {
  name                = "${var.prefix}-vpn"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  type                = "Vpn"
  vpn_type            = "RouteBased"
  sku                 = "VpnGw1"
  active_active       = false
  enable_bgp          = false
  ip_configuration {
    name                          = "primary"
    public_ip_address_id          = azurerm_public_ip.vpn.id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.gateway.id
  }
}
resource "oci_core_vcn" "lab" {
  compartment_id = var.oci_compartment_ocid
  cidr_blocks    = [var.oci_cidr]
  display_name   = var.prefix
  dns_label      = var.prefix
}
resource "oci_core_drg" "lab" {
  compartment_id = var.oci_compartment_ocid
  display_name   = "${var.prefix}-drg"
}
resource "oci_core_drg_attachment" "lab" {
  drg_id = oci_core_drg.lab.id
  network_details {
    id   = oci_core_vcn.lab.id
    type = "VCN"
  }
}
resource "oci_core_cpe" "azure" {
  compartment_id = var.oci_compartment_ocid
  ip_address     = azurerm_public_ip.vpn.ip_address
  display_name   = "${var.prefix}-azure"
}
resource "oci_core_ipsec" "azure" {
  compartment_id = var.oci_compartment_ocid
  cpe_id         = oci_core_cpe.azure.id
  drg_id         = oci_core_drg.lab.id
  static_routes  = [var.azure_cidr]
  display_name   = "${var.prefix}-azure"
}
data "oci_core_ipsec_connection_tunnels" "azure" {
  ipsec_id = oci_core_ipsec.azure.id
}
resource "random_password" "vpn" {
  count   = 2
  length  = 48
  special = false
}
resource "oci_core_ipsec_connection_tunnel_management" "azure" {
  count         = 2
  ipsec_id      = oci_core_ipsec.azure.id
  tunnel_id     = data.oci_core_ipsec_connection_tunnels.azure.ip_sec_connection_tunnels[count.index].id
  routing       = "STATIC"
  ike_version   = "V2"
  shared_secret = random_password.vpn[count.index].result
}
resource "azurerm_local_network_gateway" "oci" {
  count               = 2
  name                = "${var.prefix}-oci-${count.index + 1}"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.azure_location
  gateway_address     = data.oci_core_ipsec_connection_tunnels.azure.ip_sec_connection_tunnels[count.index].vpn_ip
  address_space       = [var.oci_cidr]
}
resource "azurerm_virtual_network_gateway_connection" "oci" {
  count                      = 2
  name                       = "${var.prefix}-oci-${count.index + 1}"
  resource_group_name        = azurerm_resource_group.lab.name
  location                   = var.azure_location
  type                       = "IPsec"
  virtual_network_gateway_id = azurerm_virtual_network_gateway.vpn.id
  local_network_gateway_id   = azurerm_local_network_gateway.oci[count.index].id
  shared_key                 = random_password.vpn[count.index].result
  connection_protocol        = "IKEv2"
  enable_bgp                 = false
  depends_on                 = [oci_core_ipsec_connection_tunnel_management.azure]
}
resource "oci_core_nat_gateway" "lab" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${var.prefix}-nat"
}
data "oci_core_services" "all" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}
resource "oci_core_service_gateway" "lab" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  services { service_id = data.oci_core_services.all.services[0].id }
}
resource "oci_core_route_table" "private" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  route_rules {
    destination       = var.azure_cidr
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_drg.lab.id
  }
  route_rules {
    destination       = data.oci_core_services.all.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.lab.id
  }
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.lab.id
  }
}
resource "oci_core_security_list" "empty" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${var.prefix}-bastion-egress"
  # The Bastion private endpoint has no attached NSG and needs SSH egress.
  egress_security_rules {
    protocol         = "6"
    destination      = local.oci_private
    destination_type = "CIDR_BLOCK"
    tcp_options {
      min = 22
      max = 22
    }
  }
}
resource "oci_core_subnet" "private" {
  compartment_id             = var.oci_compartment_ocid
  vcn_id                     = oci_core_vcn.lab.id
  cidr_block                 = local.oci_private
  display_name               = "${var.prefix}-private"
  dns_label                  = "private"
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.private.id
  security_list_ids          = [oci_core_security_list.empty.id]
}
resource "oci_core_network_security_group" "services" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "${var.prefix}-services"
}
resource "oci_core_network_security_group_security_rule" "private_tcp" {
  for_each                  = toset(["22", "443", "1521", "1522"])
  network_security_group_id = oci_core_network_security_group.services.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = local.oci_private
  source_type               = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = tonumber(each.key)
      max = tonumber(each.key)
    }
  }
}
resource "oci_core_network_security_group_security_rule" "egress" {
  network_security_group_id = oci_core_network_security_group.services.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "Lab egress: Azure SQL/DNS, OCI APIs, package installation. No public ingress."
}
data "oci_core_vcn_dns_resolver_association" "lab" { vcn_id = oci_core_vcn.lab.id }
resource "oci_dns_resolver_endpoint" "azure" {
  resolver_id   = data.oci_core_vcn_dns_resolver_association.lab.dns_resolver_id
  name          = "azureforwarder"
  is_forwarding = true
  is_listening  = false
  subnet_id     = oci_core_subnet.private.id
  nsg_ids       = [oci_core_network_security_group.services.id]
  scope         = "PRIVATE"
}
resource "oci_dns_resolver" "lab" {
  resolver_id = data.oci_core_vcn_dns_resolver_association.lab.dns_resolver_id
  scope       = "PRIVATE"
  rules {
    action                 = "FORWARD"
    destination_addresses  = [azurerm_private_dns_resolver_inbound_endpoint.lab.ip_configurations[0].private_ip_address]
    source_endpoint_name   = oci_dns_resolver_endpoint.azure.name
    qname_cover_conditions = ["database.windows.net", "sql.azuresynapse.net"]
  }
}
