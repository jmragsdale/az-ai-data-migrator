"""Migration manifest tracking for audit trails and rollback operations."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MigrationManifest:
    """Track all resources created during migration for audit and rollback purposes."""

    def __init__(self, manifest_path: str = "migration_manifest.json"):
        """Initialize migration manifest.

        Args:
            manifest_path: Path to manifest JSON file
        """
        self.manifest_path = manifest_path
        self.migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.created_resources: List[Dict[str, Any]] = []
        self.manifest_data: Dict[str, Any] = {
            "migration_id": self.migration_id,
            "start_time": datetime.now().isoformat(),
            "resources": [],
            "status": "in_progress",
        }

    def log_resource(
        self,
        resource_type: str,
        resource_id: str,
        resource_name: str,
        resource_group: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log creation of a resource.

        Args:
            resource_type: Type of resource (cosmos_container, blob_container, etc.)
            resource_id: Full resource ID or path
            resource_name: Friendly name of resource
            resource_group: Azure resource group (if applicable)
            metadata: Additional metadata to track
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": resource_type,
            "id": resource_id,
            "name": resource_name,
            "resource_group": resource_group,
            "metadata": metadata or {},
        }
        self.created_resources.append(entry)
        self.manifest_data["resources"].append(entry)

    def log_batch(
        self,
        batch_number: int,
        resource_type: str,
        count: int,
        bytes_transferred: int = 0,
    ) -> None:
        """Log completion of a migration batch.

        Args:
            batch_number: Batch number
            resource_type: Type of resources in batch
            count: Number of items in batch
            bytes_transferred: Total bytes transferred
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": f"batch_{resource_type}",
            "batch_number": batch_number,
            "count": count,
            "bytes_transferred": bytes_transferred,
        }
        self.manifest_data["resources"].append(entry)

    def save(self, status: str = "completed") -> str:
        """Save manifest to file.

        Args:
            status: Final status of migration

        Returns:
            Path to saved manifest file
        """
        self.manifest_data["status"] = status
        self.manifest_data["end_time"] = datetime.now().isoformat()

        # Ensure directory exists
        Path(self.manifest_path).parent.mkdir(parents=True, exist_ok=True)

        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest_data, f, indent=2)

        return self.manifest_path

    @staticmethod
    def load(manifest_path: str) -> "MigrationManifest":
        """Load manifest from file.

        Args:
            manifest_path: Path to manifest JSON file

        Returns:
            MigrationManifest instance

        Raises:
            FileNotFoundError: If manifest file not found
        """
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        manifest = MigrationManifest(manifest_path)
        with open(manifest_path, "r") as f:
            manifest.manifest_data = json.load(f)
            manifest.created_resources = manifest.manifest_data.get("resources", [])

        return manifest

    def get_resources_by_type(self, resource_type: str) -> List[Dict[str, Any]]:
        """Get all resources of a specific type from manifest.

        Args:
            resource_type: Type of resource to retrieve

        Returns:
            List of resource entries
        """
        return [
            r
            for r in self.manifest_data["resources"]
            if r.get("type") == resource_type
        ]

    def get_all_cosmos_containers(self) -> List[Dict[str, Any]]:
        """Get all Cosmos DB containers from manifest."""
        return self.get_resources_by_type("cosmos_container")

    def get_all_blob_containers(self) -> List[Dict[str, Any]]:
        """Get all Blob Storage containers from manifest."""
        return self.get_resources_by_type("blob_container")

    def get_migration_summary(self) -> Dict[str, Any]:
        """Get summary of migration from manifest.

        Returns:
            Summary dictionary with counts and stats
        """
        return {
            "migration_id": self.manifest_data["migration_id"],
            "start_time": self.manifest_data["start_time"],
            "end_time": self.manifest_data.get("end_time"),
            "status": self.manifest_data["status"],
            "total_resources": len(
                [r for r in self.manifest_data["resources"] if r.get("type")]
            ),
            "cosmos_containers": len(self.get_all_cosmos_containers()),
            "blob_containers": len(self.get_all_blob_containers()),
        }
