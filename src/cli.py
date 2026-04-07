"""Command-line interface for Azure data migration tool."""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table
from anthropic import Anthropic

from src.agent.analyzer import SchemaAnalyzer
from src.agent.cost_estimator import AzureCostEstimator
from src.agent.planner import MigrationPlanner
from src.connectors.json_csv import JsonCsvConnector
from src.connectors.mongodb import MongoDBConnector
from src.migrators.blob_storage import BlobStorageMigrator
from src.migrators.cosmosdb import CosmosDBMigrator
from src.security.credential_manager import CredentialManager
from src.security.encryption import EncryptionConfig
from src.security.pii_scanner import PIIScanner
from src.utils.config import Config
from src.utils.logger import get_logger, setup_logging
from src.utils.manifest import MigrationManifest
from src.utils.tagger import ResourceTagger
from src.validators.integrity import IntegrityValidator

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), default="INFO")
@click.option("--dry-run", is_flag=True, help="Preview changes without executing")
def main(log_level: str, dry_run: bool):
    """Azure AI Data Migrator - LLM-powered migration to Azure Blob Storage and Cosmos DB."""
    setup_logging(level=log_level)

    # Store dry-run flag in context
    ctx = click.get_current_context()
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run

    console.print(
        Panel.fit("[bold blue]Azure AI Data Migrator[/bold blue]", border_style="blue"),
        justify="center",
    )


@main.command()
@click.option("--source", required=True, help="Source data location (MongoDB URI or file path)")
@click.option("--source-type", type=click.Choice(["mongodb", "json", "csv", "filesystem"]),
              help="Auto-detect if not specified")
@click.option("--sample-size", default=100, help="Number of records to sample")
@click.pass_context
def analyze(ctx: click.Context, source: str, source_type: Optional[str], sample_size: int):
    """Analyze source data schema and generate insights."""

    console.print("\n[cyan]Starting schema analysis...[/cyan]")

    try:
        config = Config.get_instance()
        config.validate_required()

        # Detect source type if not specified
        if not source_type:
            if "mongodb" in source.lower() or source.startswith("mongodb"):
                source_type = "mongodb"
            elif source.endswith(".json"):
                source_type = "json"
            elif source.endswith(".csv"):
                source_type = "csv"
            else:
                source_type = "filesystem"

        samples = []
        source_stats = {}

        # Load samples based on source type
        if source_type == "mongodb":
            with console.status("[bold]Connecting to MongoDB..."):
                connector = MongoDBConnector(source)
                dbs = connector.list_databases()

                # Use first database
                if dbs:
                    collections = connector.list_collections(dbs[0])
                    if collections:
                        samples = connector.sample_documents(dbs[0], collections[0], sample_size)
                        source_stats = connector.get_collection_stats(dbs[0], collections[0])

                connector.close()

        elif source_type == "json":
            with console.status("[bold]Loading JSON file..."):
                data = JsonCsvConnector.load_json_file(source)
                samples = JsonCsvConnector.normalize_json_to_records(data)[:sample_size]

        elif source_type == "csv":
            with console.status("[bold]Loading CSV file..."):
                samples = JsonCsvConnector.load_csv_file(source)[:sample_size]

        if not samples:
            console.print("[red]No samples found in source[/red]")
            return

        # Run schema analysis
        analyzer = SchemaAnalyzer(Anthropic(api_key=config.anthropic_api_key))

        with console.status("[bold]Analyzing schema with Claude..."):
            analysis = analyzer.analyze_samples(samples, config.anthropic_api_key)

        # Display analysis results
        console.print("\n[green]Schema Analysis Complete[/green]\n")

        summary = analyzer.get_analysis_summary()

        table = Table(title="Schema Analysis Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Total Fields Found", str(summary["total_fields"]))
        table.add_row("Patterns Detected", str(summary["patterns_found"]))
        table.add_row("Inconsistencies Found", str(summary["inconsistencies_found"]))
        table.add_row("Recommended Partition Key", str(summary["partition_key_recommendation"]))
        table.add_row("Fields to Index", str(summary["indexing_count"]))

        console.print(table)

        # Save analysis results
        analysis_file = "analysis_results.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)

        console.print(f"\n[green]Analysis saved to[/green] {analysis_file}")

    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")
        logger.exception("Analysis error")


@main.command()
@click.option("--analysis-file", default="analysis_results.json",
              help="Path to analysis results JSON")
@click.option("--doc-count", default=10000, help="Estimated document count")
@click.option("--data-volume-gb", default=10.0, help="Estimated data volume in GB")
@click.pass_context
def plan(ctx: click.Context, analysis_file: str, doc_count: int, data_volume_gb: float):
    """Generate LLM-powered migration plan."""

    console.print("\n[cyan]Generating migration plan...[/cyan]")

    try:
        # Load analysis results
        if not Path(analysis_file).exists():
            console.print(f"[red]Analysis file not found: {analysis_file}[/red]")
            return

        with open(analysis_file, "r") as f:
            analysis = json.load(f)

        config = Config.get_instance()
        config.validate_required()

        # Generate migration plan
        planner = MigrationPlanner(Anthropic(api_key=config.anthropic_api_key))

        with console.status("[bold]Planning migration with Claude..."):
            plan_result = planner.generate_plan(
                analysis,
                doc_count,
                data_volume_gb,
                config.anthropic_api_key,
            )

        console.print("\n[green]Migration Plan Generated[/green]\n")

        # Display plan summary
        cosmos_config = planner.get_cosmos_db_config()
        blob_config = planner.get_blob_storage_config()
        batch_strategy = planner.get_batch_strategy()

        table = Table(title="Migration Plan Summary")
        table.add_column("Component", style="cyan")
        table.add_column("Configuration", style="magenta")

        table.add_row("Cosmos DB Database", cosmos_config.get("database_name", "N/A"))
        table.add_row("Consistency Level", cosmos_config.get("consistency_level", "N/A"))
        table.add_row("Initial Throughput (RU/s)", str(cosmos_config.get("throughput_rus", "N/A")))
        table.add_row("Blob Storage Tier", blob_config.get("access_tier", "N/A"))
        table.add_row("Batch Size", str(batch_strategy.get("batch_size", "N/A")))

        console.print(table)

        # Cost estimation
        cost_estimator = AzureCostEstimator()
        cosmos_cost = cost_estimator.estimate_cosmos_db_costs(
            doc_count,
            data_volume_gb * 1024 / max(doc_count, 1),
            doc_count // 10,
        )
        blob_cost = cost_estimator.estimate_blob_storage_costs(data_volume_gb)
        total_cost = cost_estimator.estimate_total_migration_cost(cosmos_cost, blob_cost)

        console.print("\n[cyan]Estimated Monthly Costs:[/cyan]")
        cost_table = Table()
        cost_table.add_column("Service", style="cyan")
        cost_table.add_column("Monthly Cost", style="green")
        cost_table.add_row("Cosmos DB", f"${cosmos_cost['estimated_monthly_cost_usd']:.2f}")
        cost_table.add_row("Blob Storage", f"${blob_cost['total_monthly_cost_usd']:.2f}")
        cost_table.add_row("Total", f"${total_cost['total_monthly_usd']:.2f}")

        console.print(cost_table)

        # Save plan
        plan_file = "migration_plan.json"
        with open(plan_file, "w") as f:
            json.dump(plan_result, f, indent=2)

        console.print(f"\n[green]Plan saved to[/green] {plan_file}")

    except Exception as e:
        console.print(f"[red]Planning failed: {e}[/red]")
        logger.exception("Planning error")


@main.command()
@click.option("--plan-file", default="migration_plan.json", help="Migration plan JSON")
@click.option("--manifest-file", default="migration_manifest.json", help="Manifest file path")
@click.pass_context
def migrate(ctx: click.Context, plan_file: str, manifest_file: str):
    """Execute data migration to Azure resources."""

    if ctx.obj.get("dry_run"):
        console.print("[yellow]DRY RUN MODE - No actual changes will be made[/yellow]\n")

    console.print("\n[cyan]Starting data migration...[/cyan]")

    try:
        if not Path(plan_file).exists():
            console.print(f"[red]Plan file not found: {plan_file}[/red]")
            return

        config = Config.get_instance()
        cred_manager = CredentialManager(config)
        is_valid, error_msg = cred_manager.validate_all_credentials()

        if not is_valid:
            console.print(f"[red]Credential validation failed: {error_msg}[/red]")
            return

        # Load migration plan
        with open(plan_file, "r") as f:
            plan = json.load(f)

        # Initialize manifest
        manifest = MigrationManifest(manifest_file)

        # Initialize migrators
        cosmos_migrator = CosmosDBMigrator(
            cred_manager.get_cosmos_connection_string(),
            manifest,
        )
        blob_migrator = BlobStorageMigrator(
            cred_manager.get_storage_connection_string(),
            manifest,
        )

        # Create resources
        cosmos_config = plan.get("cosmos_db_config", {})
        blob_config = plan.get("blob_storage_config", {})

        if not ctx.obj.get("dry_run"):
            console.print("[cyan]Creating Cosmos DB database...[/cyan]")
            cosmos_migrator.create_database(cosmos_config.get("database_name", "migrated_data"))

            for container in cosmos_config.get("containers", []):
                cosmos_migrator.create_container(
                    container.get("name"),
                    container.get("partition_key"),
                    throughput=container.get("throughput", 400),
                )

            console.print("[cyan]Creating Blob Storage containers...[/cyan]")
            blob_migrator.create_container(blob_config.get("container_name", "migrated-data"))

        # Save manifest
        manifest.save("completed" if not ctx.obj.get("dry_run") else "dry_run")
        console.print(f"\n[green]Migration complete - manifest saved to {manifest_file}[/green]")

    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]")
        logger.exception("Migration error")


@main.command()
@click.option("--manifest-file", required=True, help="Manifest file from migration")
@click.pass_context
def rollback(ctx: click.Context, manifest_file: str):
    """Rollback migration by deleting created resources."""

    if not Path(manifest_file).exists():
        console.print(f"[red]Manifest file not found: {manifest_file}[/red]")
        return

    if not click.confirm("This will delete all migrated resources. Continue?"):
        return

    console.print("\n[cyan]Rolling back migration...[/cyan]")

    try:
        config = Config.get_instance()
        cred_manager = CredentialManager(config)

        manifest = MigrationManifest.load(manifest_file)

        # Initialize migrators
        cosmos_migrator = CosmosDBMigrator(cred_manager.get_cosmos_connection_string())
        blob_migrator = BlobStorageMigrator(cred_manager.get_storage_connection_string())

        # Delete resources in reverse order
        summary = manifest.get_migration_summary()
        console.print(f"Rolling back migration {summary['migration_id']}")

        if not ctx.obj.get("dry_run"):
            # Delete blobs
            for container in manifest.get_all_blob_containers():
                blob_migrator.delete_container(container["name"])

            # Delete Cosmos DB
            cosmos_migrator.delete_database()

        console.print("[green]Rollback complete[/green]")

    except Exception as e:
        console.print(f"[red]Rollback failed: {e}[/red]")
        logger.exception("Rollback error")


@main.command()
@click.option("--manifest-file", required=True, help="Manifest from migration")
@click.option("--expected-doc-count", help="Expected document count for validation")
def validate(manifest_file: str, expected_doc_count: Optional[int]):
    """Validate post-migration data integrity."""

    console.print("\n[cyan]Starting validation...[/cyan]")

    try:
        if not Path(manifest_file).exists():
            console.print(f"[red]Manifest file not found: {manifest_file}[/red]")
            return

        config = Config.get_instance()
        cred_manager = CredentialManager(config)

        # Initialize validators
        cosmos_migrator = CosmosDBMigrator(cred_manager.get_cosmos_connection_string())
        blob_migrator = BlobStorageMigrator(cred_manager.get_storage_connection_string())

        validator = IntegrityValidator(cosmos_migrator, blob_migrator)

        # Run validations
        manifest = MigrationManifest.load(manifest_file)
        summary = manifest.get_migration_summary()

        with Progress() as progress:
            task = progress.add_task("[cyan]Validating...", total=100)

            # Validate Cosmos DB
            for container in manifest.get_all_cosmos_containers():
                if expected_doc_count:
                    validator.validate_cosmos_db_records(
                        container["name"],
                        int(expected_doc_count),
                    )
                validator.spot_check_cosmos_db_records(container["name"])
                progress.advance(task, 50)

            # Validate Blob Storage
            for container in manifest.get_all_blob_containers():
                validator.validate_blob_storage_blobs(container["name"], 0)
                validator.validate_blob_storage_integrity(container["name"])
                progress.advance(task, 50)

        # Generate report
        report = validator.generate_validation_report()

        console.print("\n[green]Validation Complete[/green]\n")

        # Display results
        status_color = "green" if report["status"] == "passed" else "red"
        console.print(f"[{status_color}]Status: {report['status'].upper()}[/{status_color}]")

        summary_data = report["summary"]
        validation_table = Table(title="Validation Results")
        validation_table.add_column("Metric", style="cyan")
        validation_table.add_column("Value", style="magenta")
        validation_table.add_row("Total Checks", str(summary_data["total_checks"]))
        validation_table.add_row("Passed", str(summary_data["passed"]))
        validation_table.add_row("Failed", str(summary_data["failed"]))

        console.print(validation_table)

        # Save report
        report_file = "validation_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        console.print(f"\n[green]Report saved to {report_file}[/green]")

    except Exception as e:
        console.print(f"[red]Validation failed: {e}[/red]")
        logger.exception("Validation error")


if __name__ == "__main__":
    main(obj={})
