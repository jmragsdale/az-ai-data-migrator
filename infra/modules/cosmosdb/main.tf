terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.50"
    }
  }
}

data "azurerm_client_config" "current" {}

# Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.project_name}-cosmos-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level       = var.consistency_level
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  enable_automatic_failover    = var.enable_automatic_failover
  enable_partition_key_version = var.enable_partition_key_version
  multiple_write_locations_enabled = var.enable_multiple_write_regions

  capabilities {
    name = "EnableServerless"
  }

  backup {
    type                = "Continuous"
    tier                = "Continuous7Days"
    interval_in_minutes = 60
    retention_in_hours  = 8
  }

  tags = var.tags
}

# Cosmos DB Database
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name

  autoscale_settings {
    max_throughput = var.max_throughput_rus
  }
}

# Default Container
resource "azurerm_cosmosdb_sql_container" "default" {
  name                = "documents"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name

  partition_key_path      = "/id"
  partition_key_version   = 2
  default_ttl             = -1
  analytical_storage_ttl  = -1

  indexing_policy {
    indexing_mode = "Consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }

    spatial_index {
      path = "/*"
    }

    composite_index {
      index {
        path   = "/timestamp"
        order  = "Ascending"
      }
      index {
        path   = "/status"
        order  = "Descending"
      }
    }
  }

  unique_key {
    paths = ["/id"]
  }

  autoscale_settings {
    max_throughput = var.max_throughput_rus
  }
}

output "cosmos_db_account_id" {
  value = azurerm_cosmosdb_account.main.id
}

output "cosmos_db_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "cosmos_db_primary_key" {
  value     = azurerm_cosmosdb_account.main.primary_key
  sensitive = true
}

output "cosmos_db_connection_string" {
  value     = "AccountEndpoint=${azurerm_cosmosdb_account.main.endpoint};AccountKey=${azurerm_cosmosdb_account.main.primary_key};"
  sensitive = true
}

output "database_name" {
  value = azurerm_cosmosdb_sql_database.main.name
}

output "default_container_name" {
  value = azurerm_cosmosdb_sql_container.default.name
}
