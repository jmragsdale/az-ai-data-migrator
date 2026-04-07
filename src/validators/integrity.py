"""Post-migration integrity validation."""

import random
from typing import Any, Dict, List, Optional

from src.migrators.blob_storage import BlobStorageMigrator
from src.migrators.cosmosdb import CosmosDBMigrator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IntegrityValidator:
    """Validate data integrity after migration."""

    def __init__(
        self,
        cosmos_migrator: Optional[CosmosDBMigrator] = None,
        blob_migrator: Optional[BlobStorageMigrator] = None,
    ):
        """Initialize integrity validator.

        Args:
            cosmos_migrator: Cosmos DB migrator instance
            blob_migrator: Blob Storage migrator instance
        """
        self.cosmos_migrator = cosmos_migrator
        self.blob_migrator = blob_migrator
        self.validation_report: Dict[str, Any] = {
            "status": "pending",
            "checks": [],
            "summary": {},
        }

    def validate_cosmos_db_records(
        self,
        container_name: str,
        expected_count: int,
        tolerance_percent: float = 5.0,
    ) -> Dict[str, Any]:
        """Validate Cosmos DB record count.

        Args:
            container_name: Container to validate
            expected_count: Expected number of records
            tolerance_percent: Acceptable variance percentage

        Returns:
            Validation result

        Raises:
            ValueError: If migrator not initialized
        """
        if not self.cosmos_migrator:
            raise ValueError("Cosmos DB migrator not initialized")

        try:
            stats = self.cosmos_migrator.get_container_stats(container_name)
            actual_count = stats["document_count"]

            # Calculate tolerance
            tolerance = int(expected_count * (tolerance_percent / 100))
            lower_bound = expected_count - tolerance
            upper_bound = expected_count + tolerance

            is_valid = lower_bound <= actual_count <= upper_bound

            result = {
                "check_type": "record_count",
                "container": container_name,
                "expected": expected_count,
                "actual": actual_count,
                "tolerance_percent": tolerance_percent,
                "is_valid": is_valid,
                "variance_percent": (
                    ((actual_count - expected_count) / expected_count * 100)
                    if expected_count > 0
                    else 0
                ),
            }

            self.validation_report["checks"].append(result)
            return result

        except Exception as e:
            logger.error(f"Failed to validate record count: {e}")
            raise

    def spot_check_cosmos_db_records(
        self,
        container_name: str,
        sample_size: int = 10,
    ) -> Dict[str, Any]:
        """Spot-check random records from Cosmos DB.

        Args:
            container_name: Container to validate
            sample_size: Number of records to sample

        Returns:
            Spot-check result

        Raises:
            ValueError: If migrator not initialized
        """
        if not self.cosmos_migrator:
            raise ValueError("Cosmos DB migrator not initialized")

        try:
            query = f"SELECT TOP {sample_size} * FROM c"
            items = self.cosmos_migrator.query_items(container_name, query)

            # Check that items are valid
            validation_items = []
            for item in items:
                is_valid = isinstance(item, dict) and "id" in item

                validation_items.append({
                    "has_id": "id" in item,
                    "has_content": len(item) > 1,
                    "is_valid": is_valid,
                })

            passed = sum(1 for v in validation_items if v["is_valid"])

            result = {
                "check_type": "spot_check",
                "container": container_name,
                "sample_size": len(items),
                "valid_records": passed,
                "invalid_records": len(items) - passed,
                "pass_rate": (passed / len(items) * 100) if items else 0,
                "sample_validations": validation_items[:3],
            }

            self.validation_report["checks"].append(result)
            return result

        except Exception as e:
            logger.error(f"Failed to perform spot check: {e}")
            raise

    def validate_blob_storage_blobs(
        self,
        container_name: str,
        expected_count: int,
        expected_size_bytes: Optional[int] = None,
        tolerance_percent: float = 5.0,
    ) -> Dict[str, Any]:
        """Validate Blob Storage blob count and size.

        Args:
            container_name: Container to validate
            expected_count: Expected number of blobs
            expected_size_bytes: Expected total size
            tolerance_percent: Acceptable variance percentage

        Returns:
            Validation result

        Raises:
            ValueError: If migrator not initialized
        """
        if not self.blob_migrator:
            raise ValueError("Blob Storage migrator not initialized")

        try:
            stats = self.blob_migrator.get_container_stats(container_name)
            actual_count = stats["blob_count"]
            actual_size = stats["total_size_bytes"]

            # Validate count
            tolerance = int(expected_count * (tolerance_percent / 100))
            count_valid = abs(actual_count - expected_count) <= tolerance

            # Validate size if provided
            size_valid = True
            size_variance = 0
            if expected_size_bytes:
                tolerance = int(expected_size_bytes * (tolerance_percent / 100))
                size_valid = abs(actual_size - expected_size_bytes) <= tolerance
                size_variance = (
                    ((actual_size - expected_size_bytes) / expected_size_bytes * 100)
                    if expected_size_bytes > 0
                    else 0
                )

            result = {
                "check_type": "blob_validation",
                "container": container_name,
                "expected_count": expected_count,
                "actual_count": actual_count,
                "count_valid": count_valid,
                "expected_size_bytes": expected_size_bytes,
                "actual_size_bytes": actual_size,
                "size_valid": size_valid,
                "size_variance_percent": size_variance,
                "overall_valid": count_valid and size_valid,
            }

            self.validation_report["checks"].append(result)
            return result

        except Exception as e:
            logger.error(f"Failed to validate blobs: {e}")
            raise

    def validate_blob_storage_integrity(
        self,
        container_name: str,
        sample_size: int = 5,
    ) -> Dict[str, Any]:
        """Spot-check random blobs for integrity.

        Args:
            container_name: Container to validate
            sample_size: Number of blobs to sample

        Returns:
            Integrity check result

        Raises:
            ValueError: If migrator not initialized
        """
        if not self.blob_migrator:
            raise ValueError("Blob Storage migrator not initialized")

        try:
            container_client = self.blob_migrator.containers[container_name]
            blobs = list(container_client.list_blobs())

            if not blobs:
                return {
                    "check_type": "blob_integrity",
                    "container": container_name,
                    "sample_size": 0,
                    "accessible_blobs": 0,
                    "pass_rate": 0,
                }

            # Sample random blobs
            sample = random.sample(blobs, min(sample_size, len(blobs)))

            accessible_count = 0
            for blob in sample:
                try:
                    blob_client = container_client.get_blob_client(blob.name)
                    # Try to get blob properties (validates accessibility)
                    blob_client.get_blob_properties()
                    accessible_count += 1
                except Exception as e:
                    logger.warning(f"Blob {blob.name} not accessible: {e}")

            result = {
                "check_type": "blob_integrity",
                "container": container_name,
                "sample_size": len(sample),
                "accessible_blobs": accessible_count,
                "pass_rate": (accessible_count / len(sample) * 100) if sample else 0,
            }

            self.validation_report["checks"].append(result)
            return result

        except Exception as e:
            logger.error(f"Failed to check blob integrity: {e}")
            raise

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report.

        Returns:
            Complete validation report
        """
        all_valid = all(c.get("is_valid") or c.get("overall_valid") or c.get("pass_rate", 0) > 90
                        for c in self.validation_report["checks"])

        failed_checks = [c for c in self.validation_report["checks"]
                        if not (c.get("is_valid") or c.get("overall_valid") or c.get("pass_rate", 0) > 90)]

        self.validation_report["status"] = "passed" if all_valid else "failed"
        self.validation_report["summary"] = {
            "total_checks": len(self.validation_report["checks"]),
            "passed": len(self.validation_report["checks"]) - len(failed_checks),
            "failed": len(failed_checks),
            "overall_valid": all_valid,
            "failed_checks": [
                {
                    "type": c.get("check_type"),
                    "container": c.get("container"),
                    "reason": f"Check failed with {c.get('variance_percent', 0):.1f}% variance"
                }
                for c in failed_checks
            ],
        }

        return self.validation_report
