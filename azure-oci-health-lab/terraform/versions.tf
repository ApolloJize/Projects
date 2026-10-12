terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "= 4.23.0" }
    oci     = { source = "oracle/oci", version = "= 7.21.0" }
    random  = { source = "hashicorp/random", version = "= 3.7.2" }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

provider "oci" {
  region              = var.oci_region
  config_file_profile = var.oci_config_profile
}

provider "oci" {
  alias               = "home"
  region              = var.oci_home_region
  config_file_profile = var.oci_config_profile
}
