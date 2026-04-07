# Azure AI Data Migrator - Architecture Documentation

## Overview

The Azure AI Data Migrator is a production-grade CLI tool that leverages Claude (via Anthropic SDK) to intelligently analyze, plan, and execute migrations of unstructured data to Azure cloud services. The system follows a modular architecture with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Layer (Click Commands)                    │
│   [analyze] [plan] [migrate] [validate] [rollback]              │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Layer (LLM Orchestration)               │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Analyzer     │  │ Planner      │  │ Resolver     │         │
│   │ (Claude API) │  │ (Claude API) │  │ (Claude API) │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │         Cost Estimator (Rule-based)                      │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Connector & Migrator Layer                      │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ MongoDB      │  │ Cosmos DB    │  │ Blob Storage │         │
│   │ Connector    │  │ Migrator     │  │ Migrator     │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │   JSON/CSV Connector | Filesystem Connector              │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Validation & Security Layer                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Integrity    │  │ PII Scanner  │  │ Encryption   │         │
│   │ Validator    │  │ (LLM + Regex)│  │ Config       │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │   Credential Manager | Manifest Tracker | Tagger        │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Azure Services & Infrastructure                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Cosmos DB    │  │ Blob Storage │  │ Log Analytics│         │
│   │ (SQL API)    │  │              │  │              │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │         Terraform Infrastructure as Code               │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Module Responsibilities

### 1. CLI Layer (`src/cli.py`)
- **Purpose**: User-facing command interface with Rich formatting
- **Responsibilities**:
  - Parse command-line arguments
  - Orchestrate workflow (analyze → plan → migrate → validate)
  - Display formatted output and progress bars
  - Handle dry-run mode for preview
- **Commands**:
  - `analyze`: Discover and analyze source data schemas
  - `plan`: Generate migration strategy using Claude
  - `migrate`: Execute data transfer to Azure
  - `rollback`: Undo migration via manifest
  - `validate`: Verify post-migration integrity

### 2. Agent Layer (LLM Orchestration)

#### `SchemaAnalyzer` (`src/agent/analyzer.py`)
- Calls Claude to analyze raw document samples
- Detects:
  - Field types and patterns
  - Inconsistencies across documents
  - Implicit schemas and relationships
  - Recommended partition keys for Cosmos DB
  - Indexing strategy

#### `MigrationPlanner` (`src/agent/planner.py`)
- Takes analysis results and generates migration plan
- Claude recommendations for:
  - Cosmos DB database/container design
  - Partition key selection
  - Indexing policies
  - Consistency levels
  - Throughput estimation
- Includes cost estimation and time projection

#### `ConflictResolver` (`src/agent/resolver.py`)
- Proposes solutions for schema inconsistencies
- Strategies: coerce, split, nullable, skip, custom transform
- Risk assessment for each resolution

#### `AzureCostEstimator` (`src/agent/cost_estimator.py`)
- Rule-based cost calculation (no Claude required)
- Estimates RU/s consumption from usage patterns
- Calculates Blob Storage costs by tier and access frequency
- Provides optimization recommendations

### 3. Connector Layer (Source Data Discovery)

#### `MongoDBConnector` (`src/connectors/mongodb.py`)
- Connect, list databases/collections
- Sample documents for analysis
- Stream all documents in batches
- Get collection statistics

#### `FileSystemConnector` (`src/connectors/filesystem.py`)
- Recursively scan directories
- Categorize files (documents, images, video, audio)
- Stream files in batches
- Get file metadata

#### `JsonCsvConnector` (`src/connectors/json_csv.py`)
- Load JSON (single doc or arrays)
- Load CSV with auto-delimiter detection
- Normalize records to consistent format
- Flatten/unflatten nested structures

### 4. Migrator Layer (Data Transfer)

#### `CosmosDBMigrator` (`src/migrators/cosmosdb.py`)
- Create Cosmos DB database and containers
- Bulk upsert items with retry logic
- Track progress and batch statistics
- Support rollback (delete containers/database)
- Query items for validation

#### `BlobStorageMigrator` (`src/migrators/blob_storage.py`)
- Create blob containers with access controls
- Upload files (simple or chunked)
- Set access tiers (Hot, Cool, Archive)
- Generate SAS URLs for shared access
- Support rollback (delete blobs/containers)

### 5. Validation Layer (Post-Migration Verification)

#### `IntegrityValidator` (`src/validators/integrity.py`)
- Verify record counts match between source and destination
- Spot-check random sample of records
- Verify blob existence and size
- Generate validation report with pass/fail status

### 6. Security Layer

#### `CredentialManager` (`src/security/credential_manager.py`)
- Support Azure Managed Identity via DefaultAzureCredential
- Handle connection strings and API keys
- Validate credentials at startup
- Mask sensitive values in logs

#### `PIIScanner` (`src/security/pii_scanner.py`)
- Regex-based detection: SSN, email, phone, credit card, IP, etc.
- Claude API for deeper PII analysis on sample data
- Generate PII report with severity levels
- Recommend remediation (encrypt, mask, flag)
- Azure Purview integration recommendations

#### `EncryptionConfig` (`src/security/encryption.py`)
- Validate Cosmos DB and Blob Storage encryption settings
- Support Microsoft-managed and customer-managed keys
- Generate encryption validation reports
- Provide Key Vault recommendations

### 7. Utility Layer

#### `Config` (`src/utils/config.py`)
- Singleton pattern for environment-based configuration
- Load from .env file
- Validate required fields
- Provide defaults for optional settings

#### `Logger` (`src/utils/logger.py`)
- Structured logging with timestamp and context
- Sensitive data masking (API keys, credentials, etc.)
- Optional file output
- Configurable log levels

#### `MigrationManifest` (`src/utils/manifest.py`)
- Track all resources created during migration
- Log batches and timestamps
- Enable audit trails
- Support rollback via manifest

#### `ResourceTagger` (`src/utils/tagger.py`)
- Generate standard Azure tags (migration-source, migration-date, etc.)
- Format tags for different services
- Validate tag compliance with Azure restrictions
- Add metadata tags for blobs

## Data Flow

### Analyze Phase
```
Source Data
    ↓
[Connector] → Sample Documents
    ↓
[SchemaAnalyzer] → Claude API → Schema Analysis
    ↓
Analysis Results (JSON) → User Review → analysis_results.json
```

### Plan Phase
```
analysis_results.json
    ↓
[MigrationPlanner] → Claude API → Migration Strategy
    ↓
Include: Cost Estimation, Time Estimates, Batch Strategy
    ↓
migration_plan.json → User Review
```

### Migrate Phase
```
migration_plan.json
    ↓
[CredentialManager] → Validate Credentials
    ↓
[CosmosDBMigrator] ┐
                   ├→ Create Resources → Azure Services
[BlobStorageMigrator] ┤
                      ↓
[MigrationManifest] → Track Created Resources
    ↓
migration_manifest.json → Audit Trail
```

### Validate Phase
```
migration_manifest.json
    ↓
[IntegrityValidator]
    ├→ Record Count Check
    ├→ Spot-Check Sampling
    └→ Blob Verification
    ↓
validation_report.json → Success/Failure Status
```

### Rollback Phase
```
migration_manifest.json
    ↓
[CosmosDBMigrator] ┐
                   ├→ Delete Tracked Resources
[BlobStorageMigrator] ┘
    ↓
Verify Deletion → Success
```

## Terraform Infrastructure

### Resource Structure
```
Resource Group (migrated-data-prod)
    ├── Cosmos DB Account
    │   ├── Database: migrated_data
    │   └── Container: documents (autoscale 400-4000 RU/s)
    ├── Storage Account
    │   ├── Blob Service
    │   ├── Container: migrated-data (Hot tier)
    │   └── Lifecycle Policies
    └── Log Analytics Workspace (monitoring)
```

### Modules
- **cosmosdb/**: SQL API account, database, container, autoscale throughput
- **storage/**: Storage account, blob service, containers, lifecycle management

## Security Architecture

### Authentication
- Azure Managed Identity (primary)
- Connection string fallback
- Anthropic API key from environment

### Data Protection
- TLS 1.2 minimum enforced
- Encryption at rest (Azure-managed default)
- Optional: Customer-managed keys via Key Vault

### Compliance
- PII scanning and reporting
- Audit logging via Log Analytics
- Encryption validation
- Azure Purview recommendations for governance

## Error Handling Strategy

1. **Credential Validation**: Check all credentials at startup
2. **Network Resilience**: Automatic retry with exponential backoff
3. **Data Integrity**: Checksums, spot-checking, record count verification
4. **Graceful Degradation**: Partial failures logged, continue on non-critical errors
5. **Rollback Capability**: Complete manifest enables resource cleanup

## Performance Considerations

### Throughput
- MongoDB: 1,200 items/second (network dependent)
- Blob Storage: 500 MB/second (network limited)
- Cosmos DB: 2,000-4,000 RU/s (autoscale)

### Batch Processing
- Configurable batch size (default: 1,000 items)
- Parallel batch processing (recommended: 5 concurrent)
- Exponential backoff for rate limiting

### Memory Management
- Stream-based processing for large datasets
- Generators for lazy evaluation
- Minimal in-memory buffering

## Testing Strategy

- Unit tests with mocked Azure clients
- Fixture-based sample data
- Integration tests with real Azure services (CI/CD)
- Dry-run mode for production validation

## Deployment

1. **Infrastructure**: Terraform apply for Azure resources
2. **Application**: pip install from setup.py
3. **Configuration**: Set .env variables
4. **Validation**: Run az-migrate validate to confirm setup

## Monitoring & Observability

- Structured logging with context
- Log Analytics workspace for centralized logging
- Diagnostic settings for Cosmos DB and Storage
- Migration manifest for audit trail

## Future Enhancements

- Support for additional sources (DynamoDB, Elasticsearch)
- Incremental migration with change data capture
- Automated schema evolution detection
- Machine learning for cost optimization
- Web UI for migration management
- Multi-cloud support (AWS S3, GCP)
