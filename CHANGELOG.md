# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-06

### Added

- Initial project scaffolding with complete module structure
- Schema analysis with Claude API for automatic schema inference and pattern detection
- LLM-powered migration planning with intelligent Cosmos DB partitioning recommendations
- Conflict resolution for inconsistent document schemas
- Azure cost estimation with RU/s calculations and storage tier recommendations
- Multi-source connectors: MongoDB, filesystem, JSON, CSV
- Full-featured Cosmos DB migrator with bulk upsert, retry logic, and rollback support
- Azure Blob Storage migrator with chunked uploads, access tier management, and metadata tagging
- Post-migration integrity validation with record count verification and spot-checking
- PII detection using regex patterns and Claude API for deeper analysis
- Azure Managed Identity support with DefaultAzureCredential fallback
- Rich CLI interface with progress bars and formatted output
- Comprehensive test suite with pytest and mocked Azure clients
- Terraform infrastructure modules for Cosmos DB and Storage Account
- Migration manifest logging for audit trails and rollback operations
- Resource tagging with standardized metadata

### Features

- **CLI Commands**:
  - `az-migrate analyze`: Discover and analyze source data schemas
  - `az-migrate plan`: Generate LLM-powered migration strategy
  - `az-migrate migrate`: Execute migration with dry-run preview
  - `az-migrate rollback`: Undo migration by deleting resources per manifest
  - `az-migrate validate`: Verify post-migration data integrity

- **Security**:
  - Managed Identity support for Azure authentication
  - PII detection and reporting with remediation recommendations
  - Encryption validation for both Cosmos DB and Blob Storage
  - Credential masking in logs and output

- **Infrastructure as Code**:
  - Cosmos DB account with SQL API and autoscale throughput
  - Configurable container partitioning and indexing policies
  - Azure Storage Account with HTTPS enforcement and TLS 1.2 minimum
  - Network rules and access tier management

[0.1.0]: https://github.com/your-org/az-ai-data-migrator/releases/tag/v0.1.0
