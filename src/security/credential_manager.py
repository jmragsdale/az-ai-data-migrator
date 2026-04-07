"""Azure credential management with Managed Identity support."""

import logging
from typing import Optional, Tuple

from azure.identity import DefaultAzureCredential
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CredentialManager:
    """Manage Azure and Anthropic credentials with Managed Identity support."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize credential manager.

        Args:
            config: Configuration instance (uses singleton if not provided)
        """
        self.config = config or Config.get_instance()
        self._azure_credential = None
        self._anthropic_key = None

    def get_azure_credential(self) -> DefaultAzureCredential:
        """Get Azure credential using DefaultAzureCredential.

        Attempts in order:
        1. Environment variables
        2. Azure CLI credentials
        3. Visual Studio credentials
        4. Managed Identity (if running in Azure)

        Returns:
            Azure credential object

        Raises:
            ValueError: If no credentials found
        """
        if self._azure_credential is None:
            try:
                self._azure_credential = DefaultAzureCredential()
                logger.debug("Initialized Azure DefaultAzureCredential")
            except Exception as e:
                logger.error(f"Failed to initialize Azure credentials: {e}")
                raise ValueError(
                    "Could not initialize Azure credentials. Ensure you have valid Azure credentials configured."
                )

        return self._azure_credential

    def get_cosmos_connection_string(self) -> str:
        """Get Cosmos DB connection string.

        Returns:
            Cosmos DB connection string from config

        Raises:
            ValueError: If connection string not configured
        """
        if not self.config.azure_cosmos_endpoint or not self.config.azure_cosmos_key:
            raise ValueError(
                "Cosmos DB endpoint and key must be configured. Set AZURE_COSMOS_ENDPOINT and AZURE_COSMOS_KEY."
            )

        # Format: AccountEndpoint=https://...;AccountKey=...;
        return f"AccountEndpoint={self.config.azure_cosmos_endpoint};AccountKey={self.config.azure_cosmos_key};"

    def get_storage_connection_string(self) -> str:
        """Get Azure Storage connection string.

        Returns:
            Storage connection string from config

        Raises:
            ValueError: If connection string not configured
        """
        if not self.config.azure_storage_connection_string:
            raise ValueError(
                "Azure Storage connection string must be configured. Set AZURE_STORAGE_CONNECTION_STRING."
            )

        return self.config.azure_storage_connection_string

    def get_anthropic_api_key(self) -> str:
        """Get Anthropic API key.

        Returns:
            Anthropic API key from config

        Raises:
            ValueError: If API key not configured
        """
        if not self.config.anthropic_api_key:
            raise ValueError(
                "Anthropic API key must be configured. Set ANTHROPIC_API_KEY."
            )

        return self.config.anthropic_api_key

    def validate_all_credentials(self) -> Tuple[bool, str]:
        """Validate all required credentials are available.

        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []

        try:
            self.get_anthropic_api_key()
        except ValueError as e:
            errors.append(str(e))

        try:
            self.get_azure_credential()
        except ValueError as e:
            errors.append(str(e))

        try:
            self.get_cosmos_connection_string()
        except ValueError as e:
            errors.append(str(e))

        try:
            self.get_storage_connection_string()
        except ValueError as e:
            errors.append(str(e))

        if errors:
            error_msg = "; ".join(errors)
            return False, error_msg

        return True, "All credentials validated successfully"

    def log_credential_status(self) -> None:
        """Log credential configuration status (with masking for security)."""
        config_dict = self.config.to_dict(mask_sensitive=True)

        logger.info("Credential Configuration Status:")
        for key, value in config_dict.items():
            if key.startswith("azure_") or key.startswith("anthropic_"):
                logger.info(f"  {key}: {value if value else 'NOT SET'}")
