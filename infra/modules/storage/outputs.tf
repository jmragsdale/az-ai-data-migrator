"""Azure Storage module outputs."""

output "storage_account_id" {
  description = "The ID of the created Storage Account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "The name of the created Storage Account"
  value       = azurerm_storage_account.main.name
}

output "primary_blob_endpoint" {
  description = "The primary Blob endpoint URL for the Storage Account"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "primary_connection_string" {
  description = "The primary connection string for the Storage Account"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "primary_access_key" {
  description = "The primary access key for the Storage Account"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "secondary_access_key" {
  description = "The secondary access key for the Storage Account"
  value       = azurerm_storage_account.main.secondary_access_key
  sensitive   = true
}

output "container_ids" {
  description = "Map of container names to their IDs"
  value = {
    for key, container in azurerm_storage_container.containers :
    key => container.id
  }
}

output "container_names" {
  description = "List of created container names"
  value = [
    for container in azurerm_storage_container.containers :
    container.name
  ]
}

output "https_traffic_only_enabled" {
  description = "Whether HTTPS traffic is enforced"
  value       = azurerm_storage_account.main.https_traffic_only_enabled
}

output "minimum_tls_version" {
  description = "The minimum TLS version required"
  value       = azurerm_storage_account.main.min_tls_version
}
