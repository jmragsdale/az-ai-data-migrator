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

variable "database_name" {
  description = "Cosmos DB database name"
  type        = string
  default     = "migrated_data"
}

variable "throughput" {
  description = "Initial provisioned throughput (deprecated, use autoscale)"
  type        = number
  default     = 400
}

variable "max_throughput_rus" {
  description = "Maximum RU/s for autoscale"
  type        = number
  default     = 4000
}

variable "consistency_level" {
  description = "Consistency level"
  type        = string
  default     = "Strong"

  validation {
    condition     = contains(["Strong", "BoundedStaleness", "Session", "ConsistentPrefix", "Eventual"], var.consistency_level)
    error_message = "Consistency level must be one of: Strong, BoundedStaleness, Session, ConsistentPrefix, Eventual"
  }
}

variable "enable_automatic_failover" {
  description = "Enable automatic failover"
  type        = bool
  default     = true
}

variable "enable_partition_key_version" {
  description = "Enable partition key version 2"
  type        = bool
  default     = true
}

variable "enable_multiple_write_regions" {
  description = "Enable multi-region writes"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
