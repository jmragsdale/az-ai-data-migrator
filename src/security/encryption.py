"""Encryption configuration validation for Azure resources."""

from typing import Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionConfig:
    """Validate and configure encryption for Azure resources."""

    def __init__(self):
        """Initialize encryption configuration."""
        self.cosmos_db_config = {
            "encryption_at_rest": True,
            "key_type": "Microsoft-managed",
            "tls_version": "1.2",
            "consistency_level": "Strong",
        }

        self.blob_storage_config = {
            "encryption_at_rest": True,
            "https_only": True,
            "tls_version": "1.2",
            "key_type": "Microsoft-managed",
            "encryption_scope": "default",
        }

    def validate_cosmos_db_encryption(self) -> Dict[str, any]:
        """Validate Cosmos DB encryption settings.

        Returns:
            Validation result with status and recommendations
        """
        validation_result = {
            "valid": True,
            "checks": [],
            "recommendations": [],
        }

        # Check encryption at rest
        if self.cosmos_db_config.get("encryption_at_rest"):
            validation_result["checks"].append({
                "check": "Encryption at rest",
                "status": "PASS",
                "detail": "Encryption at rest is enabled",
            })
        else:
            validation_result["checks"].append({
                "check": "Encryption at rest",
                "status": "FAIL",
                "detail": "Encryption at rest is disabled",
            })
            validation_result["valid"] = False
            validation_result["recommendations"].append(
                "Enable encryption at rest in Cosmos DB account settings"
            )

        # Check TLS version
        tls_version = self.cosmos_db_config.get("tls_version")
        if tls_version and float(tls_version) >= 1.2:
            validation_result["checks"].append({
                "check": "TLS Version",
                "status": "PASS",
                "detail": f"TLS {tls_version} or higher is configured",
            })
        else:
            validation_result["checks"].append({
                "check": "TLS Version",
                "status": "FAIL",
                "detail": f"TLS {tls_version} is below recommended 1.2",
            })
            validation_result["valid"] = False
            validation_result["recommendations"].append(
                "Upgrade minimum TLS version to 1.2 or higher"
            )

        # Check consistency level
        consistency = self.cosmos_db_config.get("consistency_level")
        strong_levels = {"Strong", "BoundedStaleness"}
        if consistency in strong_levels:
            validation_result["checks"].append({
                "check": "Consistency Level",
                "status": "PASS",
                "detail": f"Strong consistency level ({consistency}) is configured",
            })
        else:
            validation_result["checks"].append({
                "check": "Consistency Level",
                "status": "INFO",
                "detail": f"Consistency level is {consistency} (weaker than Strong)",
            })
            validation_result["recommendations"].append(
                f"Consider upgrading consistency level from {consistency} to Strong or BoundedStaleness for critical data"
            )

        return validation_result

    def validate_blob_storage_encryption(self) -> Dict[str, any]:
        """Validate Blob Storage encryption settings.

        Returns:
            Validation result with status and recommendations
        """
        validation_result = {
            "valid": True,
            "checks": [],
            "recommendations": [],
        }

        # Check encryption at rest
        if self.blob_storage_config.get("encryption_at_rest"):
            validation_result["checks"].append({
                "check": "Encryption at rest",
                "status": "PASS",
                "detail": "Encryption at rest is enabled",
            })
        else:
            validation_result["checks"].append({
                "check": "Encryption at rest",
                "status": "FAIL",
                "detail": "Encryption at rest is disabled",
            })
            validation_result["valid"] = False

        # Check HTTPS only
        if self.blob_storage_config.get("https_only"):
            validation_result["checks"].append({
                "check": "HTTPS Only",
                "status": "PASS",
                "detail": "HTTPS-only access is enforced",
            })
        else:
            validation_result["checks"].append({
                "check": "HTTPS Only",
                "status": "FAIL",
                "detail": "HTTPS-only access is not enforced",
            })
            validation_result["valid"] = False
            validation_result["recommendations"].append(
                "Enable HTTPS-only access in storage account settings"
            )

        # Check TLS version
        tls_version = self.blob_storage_config.get("tls_version")
        if tls_version and float(tls_version) >= 1.2:
            validation_result["checks"].append({
                "check": "TLS Version",
                "status": "PASS",
                "detail": f"TLS {tls_version} or higher is configured",
            })
        else:
            validation_result["checks"].append({
                "check": "TLS Version",
                "status": "FAIL",
                "detail": f"TLS {tls_version} is below 1.2",
            })
            validation_result["valid"] = False

        return validation_result

    def get_key_vault_recommendations(self) -> Dict[str, any]:
        """Get recommendations for using customer-managed keys via Key Vault.

        Returns:
            Key Vault configuration recommendations
        """
        return {
            "recommendation": "Use customer-managed keys for sensitive data",
            "setup_steps": [
                "Create Azure Key Vault in same region as resources",
                "Generate RSA 2048+ key for Cosmos DB encryption",
                "Configure Cosmos DB with Key Vault reference",
                "Configure Storage Account with customer-managed key",
                "Enable key rotation policy (90-day recommended)",
                "Enable Key Vault purge protection and soft delete",
            ],
            "benefits": [
                "Full control over encryption keys",
                "Ability to revoke access immediately",
                "Compliance with regulatory requirements",
                "Audit trail of key operations",
            ],
            "cost_impact": "Adds ~$10-20/month per Key Vault",
        }

    def set_cosmos_db_config(
        self,
        encryption_at_rest: bool = True,
        tls_version: str = "1.2",
        consistency_level: str = "Strong",
        key_type: str = "Microsoft-managed",
    ) -> None:
        """Configure Cosmos DB encryption settings.

        Args:
            encryption_at_rest: Enable encryption at rest
            tls_version: Minimum TLS version
            consistency_level: Default consistency level
            key_type: Type of encryption key (Microsoft-managed or customer-managed)
        """
        self.cosmos_db_config = {
            "encryption_at_rest": encryption_at_rest,
            "tls_version": tls_version,
            "consistency_level": consistency_level,
            "key_type": key_type,
        }

    def set_blob_storage_config(
        self,
        encryption_at_rest: bool = True,
        https_only: bool = True,
        tls_version: str = "1.2",
        key_type: str = "Microsoft-managed",
    ) -> None:
        """Configure Blob Storage encryption settings.

        Args:
            encryption_at_rest: Enable encryption at rest
            https_only: Enforce HTTPS-only access
            tls_version: Minimum TLS version
            key_type: Type of encryption key
        """
        self.blob_storage_config = {
            "encryption_at_rest": encryption_at_rest,
            "https_only": https_only,
            "tls_version": tls_version,
            "key_type": key_type,
            "encryption_scope": "default",
        }

    def get_full_encryption_report(self) -> Dict[str, any]:
        """Get comprehensive encryption report for all resources.

        Returns:
            Complete encryption validation report
        """
        cosmos_validation = self.validate_cosmos_db_encryption()
        blob_validation = self.validate_blob_storage_encryption()
        keyvault_rec = self.get_key_vault_recommendations()

        overall_valid = cosmos_validation["valid"] and blob_validation["valid"]

        return {
            "overall_valid": overall_valid,
            "cosmos_db": cosmos_validation,
            "blob_storage": blob_validation,
            "key_vault_recommendations": keyvault_rec,
            "action_items": (
                []
                if overall_valid
                else cosmos_validation["recommendations"]
                + blob_validation["recommendations"]
            ),
        }
