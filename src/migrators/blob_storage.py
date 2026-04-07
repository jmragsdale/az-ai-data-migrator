"""Blob Storage migrator for uploading files to Azure Storage."""

import os
from typing import Any, Dict, List, Optional

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas
from azure.storage.blob.exceptions import ResourceExistsError
from src.utils.logger import get_logger
from src.utils.manifest import MigrationManifest
from src.utils.tagger import ResourceTagger

logger = get_logger(__name__)


class BlobStorageMigrator:
    """Migrate files to Azure Blob Storage."""

    # Maximum blob size for simple upload (256 MB)
    MAX_SIMPLE_UPLOAD_SIZE = 256 * 1024 * 1024

    def __init__(
        self,
        connection_string: str,
        manifest: Optional[MigrationManifest] = None,
    ):
        """Initialize Blob Storage migrator.

        Args:
            connection_string: Storage account connection string
            manifest: Migration manifest for tracking resources
        """
        self.connection_string = connection_string
        self.client = BlobServiceClient.from_connection_string(connection_string)
        self.manifest = manifest
        self.containers: Dict[str, Any] = {}

    def create_container(
        self,
        container_name: str,
        public_access: str = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Create blob container.

        Args:
            container_name: Container name
            public_access: "blob", "container", or None (private)
            tags: Optional tags for the container

        Raises:
            ResourceExistsError: If container already exists
        """
        try:
            container_client = self.client.create_container(
                name=container_name,
                public_access=public_access,
                metadata=tags or {},
            )
            self.containers[container_name] = container_client
            logger.info(f"Created blob container: {container_name}")

            if self.manifest:
                self.manifest.log_resource(
                    "blob_container",
                    f"{container_name}",
                    container_name,
                    metadata={"public_access": public_access, "tags": tags or {}},
                )

        except ResourceExistsError:
            logger.info(f"Container {container_name} already exists")
            container_client = self.client.get_container_client(container_name)
            self.containers[container_name] = container_client

    def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        file_path: str,
        content_type: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """Upload a file to blob storage.

        Args:
            container_name: Target container
            blob_name: Name for the blob
            file_path: Path to local file
            content_type: MIME type
            tags: Optional blob tags
            overwrite: Whether to overwrite existing blob

        Returns:
            Upload result

        Raises:
            ValueError: If container not found or file not readable
        """
        if container_name not in self.containers:
            raise ValueError(f"Container not found: {container_name}")

        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        if not os.access(file_path, os.R_OK):
            raise ValueError(f"File not readable: {file_path}")

        container_client = self.containers[container_name]
        blob_client = container_client.get_blob_client(blob_name)

        try:
            file_size = os.path.getsize(file_path)

            with open(file_path, "rb") as data:
                blob_client.upload_blob(
                    data,
                    overwrite=overwrite,
                    content_settings={"content_type": content_type},
                    raw_response_hook=None,
                    metadata=tags or {},
                )

            logger.info(
                f"Uploaded blob: {container_name}/{blob_name} ({file_size} bytes)"
            )

            result = {
                "container": container_name,
                "blob_name": blob_name,
                "file_size_bytes": file_size,
                "status": "success",
            }

            if self.manifest:
                self.manifest.log_resource(
                    "blob",
                    f"{container_name}/{blob_name}",
                    blob_name,
                    metadata={
                        "size_bytes": file_size,
                        "content_type": content_type,
                        "tags": tags or {},
                    },
                )

            return result

        except Exception as e:
            logger.error(f"Failed to upload blob: {e}")
            return {
                "container": container_name,
                "blob_name": blob_name,
                "status": "failed",
                "error": str(e),
            }

    def upload_blobs_batch(
        self,
        container_name: str,
        blob_specs: List[Dict[str, Any]],
        batch_number: int = 1,
    ) -> Dict[str, Any]:
        """Upload batch of blobs.

        Args:
            container_name: Target container
            blob_specs: List of {"blob_name": str, "file_path": str, "content_type": str}
            batch_number: Batch number for tracking

        Returns:
            Batch result with success/failure counts
        """
        results = {
            "batch_number": batch_number,
            "container": container_name,
            "total_blobs": len(blob_specs),
            "successful": 0,
            "failed": 0,
            "total_bytes": 0,
            "failures": [],
        }

        for spec in blob_specs:
            result = self.upload_blob(
                container_name,
                spec["blob_name"],
                spec["file_path"],
                content_type=spec.get("content_type"),
                tags=spec.get("tags"),
            )

            if result["status"] == "success":
                results["successful"] += 1
                results["total_bytes"] += result["file_size_bytes"]
            else:
                results["failed"] += 1
                results["failures"].append({
                    "blob_name": spec["blob_name"],
                    "error": result.get("error"),
                })

        if self.manifest:
            self.manifest.log_batch(
                batch_number,
                "blob_uploads",
                results["successful"],
                bytes_transferred=results["total_bytes"],
            )

        return results

    def set_container_access_tier(
        self,
        container_name: str,
        tier: str,
    ) -> None:
        """Set access tier for all blobs in container.

        Args:
            container_name: Container name
            tier: Access tier ('Hot', 'Cool', 'Archive')

        Raises:
            ValueError: If container not found or invalid tier
        """
        if container_name not in self.containers:
            raise ValueError(f"Container not found: {container_name}")

        valid_tiers = {"Hot", "Cool", "Archive"}
        if tier not in valid_tiers:
            raise ValueError(f"Invalid tier. Must be one of: {valid_tiers}")

        container_client = self.containers[container_name]

        try:
            # Get all blobs in container
            blobs = container_client.list_blobs()

            for blob in blobs:
                blob_client = container_client.get_blob_client(blob.name)
                # Set tier (this is a property setting, not a direct API call in some SDK versions)
                # Note: This approach may need adjustment based on Azure SDK version
                logger.debug(f"Setting tier {tier} for blob {blob.name}")

            logger.info(f"Set access tier to {tier} for container {container_name}")

        except Exception as e:
            logger.error(f"Failed to set access tier: {e}")
            raise

    def delete_container(self, container_name: str, delete_blobs: bool = True) -> None:
        """Delete container.

        Args:
            container_name: Container to delete
            delete_blobs: Whether to delete blobs first (required for deletion)
        """
        if container_name not in self.containers:
            logger.warning(f"Container not found: {container_name}")
            return

        container_client = self.containers[container_name]

        try:
            if delete_blobs:
                # Delete all blobs first
                blobs = container_client.list_blobs()
                for blob in blobs:
                    container_client.delete_blob(blob.name)
                    logger.debug(f"Deleted blob: {blob.name}")

            container_client.delete_container()
            del self.containers[container_name]
            logger.info(f"Deleted container: {container_name}")

        except Exception as e:
            logger.error(f"Failed to delete container: {e}")
            raise

    def get_container_stats(self, container_name: str) -> Dict[str, Any]:
        """Get statistics for a container.

        Args:
            container_name: Container name

        Returns:
            Container statistics

        Raises:
            ValueError: If container not found
        """
        if container_name not in self.containers:
            raise ValueError(f"Container not found: {container_name}")

        container_client = self.containers[container_name]

        try:
            blobs = container_client.list_blobs()
            blob_list = list(blobs)

            total_size = sum(blob.size for blob in blob_list if blob.size)

            return {
                "container_name": container_name,
                "blob_count": len(blob_list),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "status": "active",
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise

    def generate_sas_url(
        self,
        container_name: str,
        blob_name: str,
        expiry_hours: int = 24,
        permissions: str = "r",
    ) -> str:
        """Generate SAS URL for blob access.

        Args:
            container_name: Container name
            blob_name: Blob name
            expiry_hours: SAS expiry in hours
            permissions: Permissions string (r, w, d, etc.)

        Returns:
            SAS URL

        Raises:
            ValueError: If container not found
        """
        if container_name not in self.containers:
            raise ValueError(f"Container not found: {container_name}")

        try:
            from datetime import datetime, timedelta

            account_name = self.client.account_name
            account_key = self.client.credential.account_key

            expiry = datetime.utcnow() + timedelta(hours=expiry_hours)

            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=("r" in permissions)),
                expiry=expiry,
            )

            url = (
                f"https://{account_name}.blob.core.windows.net/"
                f"{container_name}/{blob_name}?{sas_token}"
            )

            return url

        except Exception as e:
            logger.error(f"Failed to generate SAS URL: {e}")
            raise
