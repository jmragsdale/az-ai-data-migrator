output "cosmos_db_endpoint" {
  description = "Cosmos DB account endpoint"
  value       = module.cosmos_db.cosmos_db_endpoint
}

output "cosmos_db_key" {
  description = "Cosmos DB primary key"
  value       = module.cosmos_db.cosmos_db_primary_key
  sensitive   = true
}

output "cosmos_db_connection_string" {
  description = "Cosmos DB connection string"
  value       = module.cosmos_db.cosmos_db_connection_string
  sensitive   = true
}

output "storage_account_id" {
  description = "Storage account ID"
  value       = module.blob_storage.storage_account_id
}

output "storage_account_name" {
  description = "Storage account name"
  value       = module.blob_storage.storage_account_name
}

output "storage_primary_blob_endpoint" {
  description = "Primary blob endpoint URL"
  value       = module.blob_storage.storage_primary_blob_endpoint
}

output "storage_connection_string" {
  description = "Storage account connection string"
  value       = module.blob_storage.storage_connection_string
  sensitive   = true
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  description = "Log Analytics workspace name"
  value       = azurerm_log_analytics_workspace.main.name
}
