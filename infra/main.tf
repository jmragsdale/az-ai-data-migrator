terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.50"
    }
  }

  required_version = ">= 1.3"
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# Data source for current Azure context
data "azurerm_client_config" "current" {}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}

# Cosmos DB Module
module "cosmos_db" {
  source = "./modules/cosmosdb"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project_name        = var.project_name
  environment         = var.environment

  database_name = "migrated_data"
  throughput    = 400

  consistency_level             = "Strong"
  enable_automatic_failover     = true
  enable_partition_key_version  = true
  enable_multiple_write_regions = false

  tags = var.tags
}

# Blob Storage Module
module "blob_storage" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project_name        = var.project_name
  environment         = var.environment

  storage_account_tier             = "Standard"
  storage_account_replication_type = "LRS"
  https_traffic_only_enabled       = true
  min_tls_version                  = "TLS1_2"

  containers = {
    "migrated-data" : {
      access_type = "private"
      metadata = {
        purpose = "data-migration"
        type    = "unstructured"
      }
    }
  }

  lifecycle_rules = {
    "archive-old-data" : {
      enabled = true
      filters = {
        prefix_match = ["logs/"]
      }
      actions = {
        tier_to_cool_after_days   = 30
        tier_to_archive_after_days = 90
        delete_after_days          = 365
      }
    }
  }

  tags = var.tags
}

# Log Analytics Workspace (optional, for monitoring)
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# Diagnostic Setting for Cosmos DB
resource "azurerm_monitor_diagnostic_setting" "cosmos_db" {
  name               = "${var.project_name}-cosmos-diag"
  target_resource_id = module.cosmos_db.cosmos_db_account_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "DataPlaneRequests"

    retention_policy {
      enabled = true
      days    = 30
    }
  }

  metric {
    category = "Requests"

    retention_policy {
      enabled = true
      days    = 30
    }
  }
}

# Diagnostic Setting for Storage Account
resource "azurerm_monitor_diagnostic_setting" "storage" {
  name               = "${var.project_name}-storage-diag"
  target_resource_id = module.blob_storage.storage_account_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "StorageRead"

    retention_policy {
      enabled = true
      days    = 30
    }
  }

  enabled_log {
    category = "StorageWrite"

    retention_policy {
      enabled = true
      days    = 30
    }
  }

  metric {
    category = "Transaction"

    retention_policy {
      enabled = true
      days    = 30
    }
  }
}

# Output the resource group for reference
output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the created resource group"
  value       = azurerm_resource_group.main.id
}
