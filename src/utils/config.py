"""Configuration management for the migration tool."""

import os
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Singleton configuration manager for environment variables."""

    _instance: Optional["Config"] = None

    def __init__(self):
        """Initialize configuration from environment variables."""
        load_dotenv()

        # Anthropic API
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

        # Azure Authentication
        self.azure_subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", "")
        self.azure_resource_group = os.getenv("AZURE_RESOURCE_GROUP", "")
        self.azure_location = os.getenv("AZURE_LOCATION", "eastus")

        # Cosmos DB
        self.azure_cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT", "")
        self.azure_cosmos_key = os.getenv("AZURE_COSMOS_KEY", "")

        # Blob Storage
        self.azure_storage_connection_string = os.getenv(
            "AZURE_STORAGE_CONNECTION_STRING", ""
        )

        # Source Data
        self.source_mongodb_uri = os.getenv("SOURCE_MONGODB_URI", "")
        self.source_path = os.getenv("SOURCE_PATH", "./data")

        # Migration Settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.sample_size = int(os.getenv("SAMPLE_SIZE", "100"))
        self.migration_batch_size = int(os.getenv("MIGRATION_BATCH_SIZE", "1000"))

        # Cost Estimation
        self.estimated_docs_per_month = int(
            os.getenv("ESTIMATED_DOCS_PER_MONTH", "1000000")
        )
        self.estimated_query_rate_per_day = int(
            os.getenv("ESTIMATED_QUERY_RATE_PER_DAY", "10000")
        )
        self.estimated_storage_gb = int(os.getenv("ESTIMATED_STORAGE_GB", "500"))

        # Feature Flags
        self.enable_pii_scan = os.getenv("ENABLE_PII_SCAN", "true").lower() == "true"
        self.enable_encryption = (
            os.getenv("ENABLE_ENCRYPTION", "true").lower() == "true"
        )
        self.enable_cost_estimation = (
            os.getenv("ENABLE_COST_ESTIMATION", "true").lower() == "true"
        )

    @classmethod
    def get_instance(cls) -> "Config":
        """Get the singleton configuration instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def validate_required(self) -> None:
        """Validate that all required configuration is present."""
        required_fields = [
            ("anthropic_api_key", self.anthropic_api_key),
            ("azure_subscription_id", self.azure_subscription_id),
            ("azure_resource_group", self.azure_resource_group),
            ("azure_cosmos_endpoint", self.azure_cosmos_endpoint),
            ("azure_cosmos_key", self.azure_cosmos_key),
        ]

        missing = [name for name, value in required_fields if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    def to_dict(self, mask_sensitive: bool = True) -> dict:
        """Convert configuration to dictionary, optionally masking sensitive values."""
        config_dict = {
            "anthropic_api_key": (
                self.anthropic_api_key[:10] + "***" if mask_sensitive else self.anthropic_api_key
            ),
            "azure_subscription_id": self.azure_subscription_id,
            "azure_resource_group": self.azure_resource_group,
            "azure_location": self.azure_location,
            "azure_cosmos_endpoint": self.azure_cosmos_endpoint,
            "azure_cosmos_key": (
                "***" if mask_sensitive else self.azure_cosmos_key
            ),
            "azure_storage_connection_string": (
                "***" if mask_sensitive else self.azure_storage_connection_string
            ),
            "source_mongodb_uri": (
                "mongodb://***/***" if mask_sensitive else self.source_mongodb_uri
            ),
            "source_path": self.source_path,
            "log_level": self.log_level,
            "dry_run": self.dry_run,
            "sample_size": self.sample_size,
            "migration_batch_size": self.migration_batch_size,
            "estimated_docs_per_month": self.estimated_docs_per_month,
            "estimated_query_rate_per_day": self.estimated_query_rate_per_day,
            "estimated_storage_gb": self.estimated_storage_gb,
            "enable_pii_scan": self.enable_pii_scan,
            "enable_encryption": self.enable_encryption,
            "enable_cost_estimation": self.enable_cost_estimation,
        }
        return config_dict
