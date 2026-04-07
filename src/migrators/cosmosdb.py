"""Cosmos DB migrator for creating containers and uploading documents."""

from typing import Any, Dict, List, Optional

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError
from src.utils.logger import get_logger
from src.utils.manifest import MigrationManifest
from src.utils.tagger import ResourceTagger

logger = get_logger(__name__)


class CosmosDBMigrator:
    """Migrate data to Azure Cosmos DB."""

    def __init__(
        self,
        connection_string: str,
        manifest: Optional[MigrationManifest] = None,
    ):
        """Initialize Cosmos DB migrator.

        Args:
            connection_string: Cosmos DB connection string
            manifest: Migration manifest for tracking resources
        """
        self.connection_string = connection_string
        self.client = CosmosClient.from_connection_string(connection_string)
        self.manifest = manifest
        self.database = None
        self.containers: Dict[str, Any] = {}

    def create_database(self, database_name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Create Cosmos DB database.

        Args:
            database_name: Database name
            tags: Optional tags for the database

        Raises:
            CosmosHttpResponseError: If database creation fails
        """
        try:
            self.database = self.client.create_database(database_name)
            logger.info(f"Created Cosmos DB database: {database_name}")

            if self.manifest:
                self.manifest.log_resource(
                    "cosmos_database",
                    f"/dbs/{database_name}",
                    database_name,
                    metadata={"tags": tags or {}},
                )

        except CosmosHttpResponseError as e:
            if e.status_code == 409:
                logger.info(f"Database {database_name} already exists")
                self.database = self.client.get_database_client(database_name)
            else:
                logger.error(f"Failed to create database: {e}")
                raise

    def create_container(
        self,
        container_name: str,
        partition_key: str,
        throughput: int = 400,
        indexing_policy: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Create container in Cosmos DB.

        Args:
            container_name: Container name
            partition_key: Partition key field
            throughput: Provisioned throughput in RU/s
            indexing_policy: Optional indexing policy
            ttl_seconds: Optional time-to-live in seconds
            tags: Optional tags for the container

        Raises:
            ValueError: If database not initialized
            CosmosHttpResponseError: If container creation fails
        """
        if not self.database:
            raise ValueError("Database must be created first")

        try:
            # Create default indexing policy if not provided
            if not indexing_policy:
                indexing_policy = {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [{"path": "/*"}],
                    "excludedPaths": [{"path": '/"_etag"/?'}],
                }

            container_options = {
                "indexing_policy": indexing_policy,
            }

            if ttl_seconds:
                container_options["default_ttl"] = ttl_seconds

            container = self.database.create_container(
                id=container_name,
                partition_key=PartitionKey(path=f"/{partition_key}"),
                offer_throughput=throughput,
                **container_options,
            )

            self.containers[container_name] = container
            logger.info(
                f"Created container: {container_name} with partition key: {partition_key}"
            )

            if self.manifest:
                self.manifest.log_resource(
                    "cosmos_container",
                    f"/dbs/{self.database.id}/colls/{container_name}",
                    container_name,
                    metadata={
                        "partition_key": partition_key,
                        "throughput": throughput,
                        "ttl": ttl_seconds,
                        "tags": tags or {},
                    },
                )

        except CosmosHttpResponseError as e:
            if e.status_code == 409:
                logger.info(f"Container {container_name} already exists")
                container = self.database.get_container_client(container_name)
                self.containers[container_name] = container
            else:
                logger.error(f"Failed to create container: {e}")
                raise

    def upsert_items_batch(
        self,
        container_name: str,
        items: List[Dict[str, Any]],
        batch_number: int = 1,
        retry_attempts: int = 3,
    ) -> Dict[str, Any]:
        """Upsert batch of items to container.

        Args:
            container_name: Target container name
            items: List of items to upsert
            batch_number: Batch number for tracking
            retry_attempts: Number of retry attempts for failed items

        Returns:
            Batch result with success count and failures

        Raises:
            ValueError: If container not found
        """
        if container_name not in self.containers:
            raise ValueError(f"Container not found: {container_name}")

        container = self.containers[container_name]
        successful = 0
        failed_items = []

        for item in items:
            # Ensure each item has an id
            if "id" not in item:
                item["id"] = str(hash(str(item)))

            for attempt in range(retry_attempts):
                try:
                    container.upsert_item(item)
                    successful += 1
                    break

                except CosmosHttpResponseError as e:
                    if attempt == retry_attempts - 1:
                        logger.warning(f"Failed to upsert item after {retry_attempts} attempts: {e}")
                        failed_items.append({
                            "item_id": item.get("id"),
                            "error": str(e),
                        })
                    else:
                        logger.debug(f"Retry {attempt + 1}/{retry_attempts} for item {item.get('id')}")

        result = {
            "batch_number": batch_number,
            "container": container_name,
            "total_items": len(items),
            "successful": successful,
            "failed": len(failed_items),
            "failed_items": failed_items,
        }

        if self.manifest:
            self.manifest.log_batch(
                batch_number,
                "cosmos_items",
                successful,
                bytes_transferred=sum(len(str(item)) for item in items),
            )

        return result

    def delete_container(self, container_name: str) -> None:
        """Delete container from database.

        Args:
            container_name: Container to delete

        Raises:
            ValueError: If database not initialized
        """
        if not self.database:
            raise ValueError("Database must be initialized")

        try:
            self.database.delete_container(container_name)
            del self.containers[container_name]
            logger.info(f"Deleted container: {container_name}")
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to delete container: {e}")
            raise

    def delete_database(self) -> None:
        """Delete entire database."""
        if not self.database:
            return

        try:
            self.client.delete_database(self.database.id)
            logger.info(f"Deleted database: {self.database.id}")
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to delete database: {e}")
            raise

    def query_items(
        self,
        container_name: str,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Query items from container.

        Args:
            container_name: Container to query
            query: SQL query string
            parameters: Optional query parameters

        Returns:
            Query results

        Raises:
            ValueError: If container not found
        """
        if container_name not in self.containers:
            raise ValueError(f"Container not found: {container_name}")

        container = self.containers[container_name]

        try:
            items = list(container.query_items(
                query,
                parameters=parameters or [],
            ))
            return items

        except CosmosHttpResponseError as e:
            logger.error(f"Query failed: {e}")
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

        container = self.containers[container_name]

        try:
            # Query for count
            count_results = list(container.query_items(
                "SELECT VALUE COUNT(1) FROM c"
            ))
            count = count_results[0] if count_results else 0

            return {
                "container_name": container_name,
                "document_count": count,
                "status": "active",
            }

        except CosmosHttpResponseError as e:
            logger.error(f"Failed to get stats: {e}")
            raise
