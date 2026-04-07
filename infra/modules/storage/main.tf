terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.50"
    }
  }
}

data "azurerm_client_config" "current" {}

# Storage Account
resource "azurerm_storage_account" "main" {
  name                     = "${replace(var.project_name, "-", "")}sa${var.environment}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = var.storage_account_tier
  account_replication_type = var.storage_account_replication_type

  https_traffic_only_enabled       = var.https_traffic_only_enabled
  min_tls_version                  = var.min_tls_version
  shared_access_key_enabled        = true
  infrastructure_encryption_enabled = true

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "HEAD", "PUT"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }

    delete_retention_policy {
      days = 7
    }

    versioning_enabled = true
  }

  tags = var.tags
}

# Blob Service
resource "azurerm_storage_blob_service_properties" "main" {
  storage_account_id = azurerm_storage_account.main.id

  cors_rule {
    allowed_headers    = ["*"]
    allowed_methods    = ["GET", "HEAD", "PUT"]
    allowed_origins    = ["*"]
    exposed_headers    = ["*"]
    max_age_in_seconds = 3600
  }

  delete_retention_policy {
    days = 7
  }

  versioning_enabled = true
}

# Storage Containers
resource "azurerm_storage_container" "containers" {
  for_each = var.containers

  name                  = each.key
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = each.value.access_type

  metadata = each.value.metadata
}

# Lifecycle Management Policy
resource "azurerm_storage_management_policy" "main" {
  count = length(var.lifecycle_rules) > 0 ? 1 : 0

  storage_account_id = azurerm_storage_account.main.id

  dynamic "rule" {
    for_each = var.lifecycle_rules

    content {
      name    = rule.key
      enabled = rule.value.enabled

      filter {
        prefix_match = rule.value.filters.prefix_match
      }

      actions {
        base_blob {
          tier_to_cool_after_days_since_last_access_time    = rule.value.actions.tier_to_cool_after_days
          tier_to_archive_after_days_since_last_access_time  = rule.value.actions.tier_to_archive_after_days
          delete_after_days_since_last_access_time           = rule.value.actions.delete_after_days
        }
      }
    }
  }
}

# Network Rules (default allow, can be restricted)
resource "azurerm_storage_account_network_rules" "main" {
  count = var.restrict_network_access ? 1 : 0

  storage_account_id = azurerm_storage_account.main.id

  default_action             = "Deny"
  bypass                     = ["AzureServices"]
  virtual_network_subnet_ids = var.allowed_subnet_ids
  ip_rules                   = var.allowed_ip_addresses
}

output "storage_account_id" {
  value = azurerm_storage_account.main.id
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "storage_primary_blob_endpoint" {
  value = azurerm_storage_account.main.primary_blob_endpoint
}

output "storage_connection_string" {
  value     = azurerm_storage_account.main.primary_connection_string
  sensitive = true
}

output "storage_account_key" {
  value     = azurerm_storage_account.main.primary_access_key
  sensitive = true
}

output "container_ids" {
  value = {
    for key, container in azurerm_storage_container.containers :
    key => container.id
  }
}
