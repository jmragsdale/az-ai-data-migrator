# Azure AI Data Migrator

An intelligent, LLM-powered CLI tool for migrating unstructured data, documents, and NoSQL records to Microsoft Azure. Leverages Claude (Anthropic API) for schema analysis, migration planning, and conflict resolution.

## Features

- **Intelligent Schema Discovery**: Claude API analyzes raw document samples to infer schemas, detect patterns, and identify inconsistencies
- **AI-Powered Migration Planning**: Generates optimal Cosmos DB and Blob Storage configuration based on data analysis
- **PII Detection**: Multi-layer approach with regex patterns plus Claude API for deeper analysis
- **Cost Estimation**: Detailed RU/s and storage cost breakdown with monthly projections
- **Multi-Source Support**: MongoDB, JSON files, CSV files, filesystem
- **Azure-Native Security**: Managed Identity support, encryption validation, audit logging
- **Rollback Support**: Complete migration manifest enables safe resource cleanup
- **Post-Migration Validation**: Integrity checking with record count verification and spot sampling

## Quick Start

### Prerequisites

- Python 3.10+
- Azure subscription with appropriate permissions
- Anthropic API key for Claude access
- Source data (MongoDB, JSON, CSV, or filesystem)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/az-ai-data-migrator.git
cd az-ai-data-migrator

# Install dependencies
pip install -r requirements.txt

# Install as CLI tool
pip install -e .
```

### Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
export AZURE_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000
export AZURE_RESOURCE_GROUP=my-resource-group
export AZURE_COSMOS_ENDPOINT=https://my-cosmosdb.documents.azure.com:443/
export AZURE_COSMOS_KEY=your-cosmos-key
export AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### Basic Workflow

```bash
# 1. Analyze source data schema
az-migrate analyze --source mongodb://localhost:27017/mydb --source-type mongodb --sample-size 100

# 2. Generate migration plan using Claude
az-migrate plan --analysis-file analysis_results.json --doc-count 10000 --data-volume-gb 50

# 3. Preview migration (dry-run mode)
az-migrate migrate --plan-file migration_plan.json --manifest-file migration_manifest.json --dry-run

# 4. Execute migration
az-migrate migrate --plan-file migration_plan.json --manifest-file migration_manifest.json

# 5. Validate data integrity
az-migrate validate --manifest-file migration_manifest.json --expected-doc-count 10000

# 6. Rollback if needed
az-migrate rollback --manifest-file migration_manifest.json
```

## Command Reference

### analyze
Discover and analyze source data schema using Claude API.

```bash
az-migrate analyze \
  --source <mongodb-uri|file-path|directory> \
  --source-type <mongodb|json|csv|filesystem> \
  --sample-size 100
```

**Output**: `analysis_results.json` containing field maps, patterns, and inconsistencies

### plan
Generate intelligent migration plan from analysis results.

```bash
az-migrate plan \
  --analysis-file analysis_results.json \
  --doc-count 10000 \
  --data-volume-gb 50
```

**Output**: `migration_plan.json` with Cosmos DB and Blob Storage configuration

### migrate
Execute data migration to Azure resources.

```bash
az-migrate migrate \
  --plan-file migration_plan.json \
  --manifest-file migration_manifest.json \
  [--dry-run]
```

**Output**: `migration_manifest.json` tracking created resources for audit and rollback

### validate
Verify post-migration data integrity.

```bash
az-migrate validate \
  --manifest-file migration_manifest.json \
  --expected-doc-count 10000
```

**Output**: `validation_report.json` with pass/fail status and detailed metrics

### rollback
Delete all resources created during migration using manifest.

```bash
az-migrate rollback --manifest-file migration_manifest.json
```

**Output**: Confirmation of deleted resources

## Architecture

See [docs/architecture.md](docs/architecture.md) for complete system design, data flow, and module responsibilities.

### Key Components

- **Agent Layer**: SchemaAnalyzer, MigrationPlanner, ConflictResolver, AzureCostEstimator
- **Connectors**: MongoDB, Filesystem, JSON/CSV
- **Migrators**: CosmosDB, BlobStorage
- **Security**: CredentialManager, PIIScanner, EncryptionConfig
- **Validators**: IntegrityValidator
- **Infrastructure**: Terraform modules for Cosmos DB and Storage Account

## Infrastructure as Code

Provision Azure resources with Terraform:

```bash
cd infra

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="project_name=data-migrator" \
  -var="resource_group_name=my-rg" \
  -var="location=eastus"

# Apply configuration
terraform apply \
  -var="project_name=data-migrator" \
  -var="resource_group_name=my-rg" \
  -var="location=eastus"
```

### Terraform Modules

- **cosmosdb/**: SQL API account with autoscale, configurable consistency, failover
- **storage/**: Storage account with blob service, containers, lifecycle policies

## Security

### Authentication
- **Primary**: Azure Managed Identity (DefaultAzureCredential)
- **Fallback**: Connection strings and keys

### Data Protection
- **Encryption at Rest**: Azure-managed (default) or customer-managed keys
- **Encryption in Transit**: TLS 1.2 minimum enforced
- **PII Handling**: Automatic detection and remediation recommendations

### Compliance
- GDPR, CCPA, HIPAA readiness checks
- Audit logging via Log Analytics
- Azure Purview integration for data governance
- Access control via RBAC

## Cost Estimation

The tool provides detailed cost estimates:

```
Cosmos DB Monthly Cost:
  - RU/s: 2,000
  - Estimated Monthly: $280
  - Annual: $3,360

Blob Storage Monthly Cost:
  - Capacity: 5.2 TB (Hot tier)
  - Monthly: $450
  - Annual: $5,400

Total First Year: ~$13,600
```

## Troubleshooting

### Authentication Issues
```bash
# Verify Azure credentials
az login

# Check Anthropic API key
echo $ANTHROPIC_API_KEY
```

### Network Errors
- Enable verbose logging: `--log-level DEBUG`
- Check network connectivity to MongoDB/file sources
- Verify Azure service endpoints are accessible

### Data Quality Issues
- Review `analysis_results.json` for detected inconsistencies
- Check `validation_report.json` for post-migration issues
- Use `--dry-run` mode to preview changes

### Cost Overruns
- Review cost_estimator output in migration plan
- Check Cosmos DB RU consumption in Azure Portal
- Consider downgrading access tier from Hot to Cool/Archive

## Testing

Run test suite with pytest:

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
```

Test coverage includes:
- Schema analysis and type detection
- JSON/CSV parsing and normalization
- Migrator CRUD operations (mocked)
- Manifest tracking and rollback
- PII detection patterns

## Development

### Project Structure
```
az-ai-data-migrator/
├── src/
│   ├── cli.py                 # Click CLI commands
│   ├── agent/                 # LLM orchestration
│   ├── connectors/            # Source data discovery
│   ├── migrators/             # Azure resource transfer
│   ├── validators/            # Post-migration checks
│   ├── security/              # Authentication & compliance
│   └── utils/                 # Shared utilities
├── infra/                     # Terraform modules
├── tests/                     # Pytest suite
├── samples/                   # Example data
├── docs/                      # Architecture & docs
├── setup.py                   # Package configuration
└── requirements.txt           # Python dependencies
```

### Adding New Connectors

1. Create `src/connectors/your_source.py`
2. Implement connector class with standard interface
3. Update CLI to register new source type
4. Add tests in `tests/test_connectors.py`

### Adding New Migrators

1. Create `src/migrators/your_target.py`
2. Implement CRUD operations (create, read, update, delete)
3. Support manifest logging for rollback
4. Add tests in `tests/test_migrators.py`

## Performance

### Throughput
- **MongoDB**: 1,200 items/second
- **Blob Storage**: 500 MB/second
- **Cosmos DB**: 2,000-4,000 RU/s (autoscale)

### Batch Processing
- Configurable batch sizes (default: 1,000)
- Parallel batch processing (5 concurrent streams)
- Automatic retry with exponential backoff

### Memory Usage
- Stream-based processing for large datasets
- Lazy evaluation with generators
- Minimal in-memory buffering

## Monitoring

View migration progress and logs:

```bash
# Stream logs in real-time
tail -f logs/migration.log

# View Cosmos DB metrics in Azure Portal
az monitor metrics list --resource /subscriptions/.../cosmosdb/...

# Query Log Analytics
az monitor log-analytics query --workspace-id ... \
  --analytics-query "AzureDiagnostics | where OperationName == 'Upsert'"
```

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Support

- **Documentation**: See [docs/architecture.md](docs/architecture.md)
- **Issues**: Report bugs in GitHub Issues
- **Questions**: Start a discussion in GitHub Discussions
- **Email**: support@company.com

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## Roadmap

- [ ] Support for AWS DynamoDB and S3
- [ ] Real-time streaming via CDC (Change Data Capture)
- [ ] Web dashboard for migration management
- [ ] Enhanced ML-based cost optimization
- [ ] Multi-cloud deployment orchestration
- [ ] Advanced conflict resolution with user feedback loop

## Acknowledgments

- Claude API for intelligent schema analysis and planning
- Azure SDK team for robust cloud service integration
- Community contributors and testers

---

**Version**: 0.1.0
**Last Updated**: April 6, 2026
**Maintainer**: Azure Data Migration Team
