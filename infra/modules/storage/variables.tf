variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "project_name" {
  description = "Project name for naming resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "storage_account_tier" {
  description = "Storage account tier (Standard or Premium)"
  type        = string
  default     = "Standard"

  validation {
    condition     = contains(["Standard", "Premium"], var.storage_account_tier)
    error_message = "Storage account tier must be Standard or Premium"
  }
}

variable "storage_account_replication_type" {
  description = "Storage account replication type (LRS, GRS, RAGRS, ZRS)"
  type        = string
  default     = "LRS"

  validation {
    condition     = contains(["LRS", "GRS", "RAGRS", "ZRS", "GZRS", "RAGZRS"], var.storage_account_replication_type)
    error_message = "Invalid replication type"
  }
}

variable "https_traffic_only_enabled" {
  description = "Enable HTTPS only access"
  type        = bool
  default     = true
}

variable "min_tls_version" {
  description = "Minimum TLS version"
  type        = string
  default     = "TLS1_2"
}

variable "containers" {
  description = "Map of containers to create"
  type = map(object({
    access_type = optional(string, "private")
    metadata    = optional(map(string), {})
  }))
  default = {}
}

variable "lifecycle_rules" {
  description = "Map of lifecycle rules"
  type = map(object({
    enabled = bool
    filters = object({
      prefix_match = optional(list(string), [])
    })
    actions = object({
      tier_to_cool_after_days   = optional(number)
      tier_to_archive_after_days = optional(number)
      delete_after_days          = optional(number)
    })
  }))
  default = {}
}

variable "restrict_network_access" {
  description = "Enable network restrictions"
  type        = bool
  default     = false
}

variable "allowed_subnet_ids" {
  description = "List of allowed subnet IDs"
  type        = list(string)
  default     = []
}

variable "allowed_ip_addresses" {
  description = "List of allowed IP addresses"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
