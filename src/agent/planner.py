"""Migration planning using Claude API for intelligent Azure resource configuration."""

import json
from typing import Any, Dict, Optional

from anthropic import Anthropic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MigrationPlanner:
    """Generate intelligent migration plans using Claude API."""

    def __init__(self, anthropic_client: Optional[Anthropic] = None):
        """Initialize migration planner.

        Args:
            anthropic_client: Anthropic client for API calls
        """
        self.client = anthropic_client
        self.migration_plan: Dict[str, Any] = {}

    def generate_plan(
        self,
        analysis_results: Dict[str, Any],
        estimated_document_count: int,
        estimated_data_volume_gb: float,
        anthropic_api_key: str,
    ) -> Dict[str, Any]:
        """Generate migration plan from schema analysis results.

        Args:
            analysis_results: Output from SchemaAnalyzer
            estimated_document_count: Estimated number of documents
            estimated_data_volume_gb: Estimated data volume in GB
            anthropic_api_key: Anthropic API key

        Returns:
            Migration plan with Cosmos DB and Blob Storage configuration
        """
        if not self.client:
            self.client = Anthropic(api_key=anthropic_api_key)

        # Prepare input
        analysis_json = json.dumps(analysis_results, indent=2)[:2000]

        system_prompt = """You are an Azure database migration architect with deep expertise in Cosmos DB and Blob Storage.
        Based on the provided schema analysis, generate a comprehensive migration plan.

        Your plan should specify:
        1. Cosmos DB configuration:
           - Database name
           - Container names with recommended partition keys
           - Throughput (RU/s) based on expected load
           - Indexing policies for optimal query performance
           - Consistency level
           - Time-to-live (TTL) settings if appropriate
        2. Blob Storage configuration:
           - Container names and organization strategy
           - Recommended access tier (Hot, Cool, Archive)
           - Lifecycle policies
           - Metadata tagging strategy
        3. Data migration approach:
           - Batch sizes for optimal throughput
           - Suggested order of migration
           - Rollback strategy

        Provide structured plan in JSON format."""

        user_message = f"""Generate a migration plan based on this schema analysis:

        {analysis_json}

        Additional context:
        - Estimated documents: {estimated_document_count:,}
        - Estimated data volume: {estimated_data_volume_gb:.2f} GB

        Provide a detailed JSON plan with:
        - cosmos_db_config: Database and container configuration
        - blob_storage_config: Storage container and tier configuration
        - batch_strategy: Recommended batch sizes and processing order
        - rollback_strategy: Steps to safely rollback if needed"""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = message.content[0].text

            # Parse response
            try:
                plan = json.loads(response_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    plan = json.loads(json_match.group())
                else:
                    plan = {"raw_response": response_text}

            # Validate and enhance plan
            self.migration_plan = self._validate_and_enhance_plan(plan)
            self.migration_plan["tokens_used"] = (
                message.usage.input_tokens + message.usage.output_tokens
            )

            logger.info("Migration plan generated successfully")
            return self.migration_plan

        except Exception as e:
            logger.error(f"Migration planning failed: {e}")
            raise

    def _validate_and_enhance_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance generated plan with defaults.

        Args:
            plan: Generated plan from Claude

        Returns:
            Validated and enhanced plan
        """
        # Ensure Cosmos DB config has required fields
        if "cosmos_db_config" not in plan:
            plan["cosmos_db_config"] = {}

        cosmos_config = plan["cosmos_db_config"]
        cosmos_config.setdefault("database_name", "migrated_data")
        cosmos_config.setdefault("consistency_level", "Strong")
        cosmos_config.setdefault("throughput_rus", 400)
        cosmos_config.setdefault("autoscale_max_rus", 4000)

        # Ensure Blob Storage config has required fields
        if "blob_storage_config" not in plan:
            plan["blob_storage_config"] = {}

        blob_config = plan["blob_storage_config"]
        blob_config.setdefault("access_tier", "Hot")
        blob_config.setdefault("container_name", "migrated_data")

        # Add default batch strategy
        if "batch_strategy" not in plan:
            plan["batch_strategy"] = {
                "batch_size": 1000,
                "parallel_batches": 5,
                "retry_attempts": 3,
            }

        return plan

    def get_cosmos_db_config(self) -> Dict[str, Any]:
        """Get Cosmos DB configuration from migration plan.

        Returns:
            Cosmos DB configuration
        """
        return self.migration_plan.get("cosmos_db_config", {})

    def get_blob_storage_config(self) -> Dict[str, Any]:
        """Get Blob Storage configuration from migration plan.

        Returns:
            Blob Storage configuration
        """
        return self.migration_plan.get("blob_storage_config", {})

    def get_batch_strategy(self) -> Dict[str, Any]:
        """Get batch processing strategy from migration plan.

        Returns:
            Batch processing strategy
        """
        return self.migration_plan.get("batch_strategy", {})

    def estimate_migration_time(
        self, total_documents: int, throughput_limit: int = 100
    ) -> Dict[str, Any]:
        """Estimate migration time based on plan.

        Args:
            total_documents: Total documents to migrate
            throughput_limit: Documents per second throughput limit

        Returns:
            Time estimation with breakdown
        """
        batch_size = self.migration_plan.get("batch_strategy", {}).get(
            "batch_size", 1000
        )
        batches = (total_documents + batch_size - 1) // batch_size

        # Estimate time per batch (including network latency)
        estimated_seconds_per_batch = batch_size / throughput_limit

        total_seconds = batches * estimated_seconds_per_batch
        hours = total_seconds / 3600
        minutes = (total_seconds % 3600) / 60

        return {
            "total_batches": batches,
            "batch_size": batch_size,
            "seconds_per_batch": estimated_seconds_per_batch,
            "total_seconds": int(total_seconds),
            "estimated_hours": round(hours, 1),
            "estimated_minutes": round(minutes, 0),
        }
