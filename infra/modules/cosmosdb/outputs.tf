"""Azure Cosmos DB module outputs."""

output "cosmosdb_account_id" {
  description = "The ID of the created Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.id
}

output "cosmosdb_account_name" {
  description = "The name of the created Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.name
}

output "cosmosdb_endpoint" {
  description = "The endpoint URL for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmosdb_primary_key" {
  description = "The primary master key for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.primary_key
  sensitive   = true
}

output "cosmosdb_secondary_key" {
  description = "The secondary master key for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.secondary_key
  sensitive   = true
}

output "cosmosdb_primary_readonly_key" {
  description = "The primary read-only key for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.primary_readonly_key
  sensitive   = true
}

output "cosmosdb_secondary_readonly_key" {
  description = "The secondary read-only key for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.secondary_readonly_key
  sensitive   = true
}

output "cosmosdb_connection_string" {
  description = "The connection string for the Cosmos DB account"
  value       = "AccountEndpoint=${azurerm_cosmosdb_account.main.endpoint};AccountKey=${azurerm_cosmosdb_account.main.primary_key};"
  sensitive   = true
}

output "cosmosdb_database_name" {
  description = "The name of the created Cosmos DB database"
  value       = azurerm_cosmosdb_sql_database.main.name
}

output "cosmosdb_database_id" {
  description = "The ID of the created Cosmos DB database"
  value       = azurerm_cosmosdb_sql_database.main.id
}

output "default_container_name" {
  description = "The name of the default container"
  value       = azurerm_cosmosdb_sql_container.default.name
}

output "default_container_id" {
  description = "The ID of the default container"
  value       = azurerm_cosmosdb_sql_container.default.id
}

output "cosmosdb_consistency_level" {
  description = "The consistency level configured for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.consistency_policy[0].consistency_level
}

output "cosmosdb_automatic_failover_enabled" {
  description = "Whether automatic failover is enabled"
  value       = azurerm_cosmosdb_account.main.enable_automatic_failover
}

output "cosmosdb_capabilities" {
  description = "List of capabilities enabled on the Cosmos DB account"
  value = [
    for capability in azurerm_cosmosdb_account.main.capabilities :
    capability.name
  ]
}
