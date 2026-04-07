"""Tests for CosmosDB and BlobStorage migrators."""

import pytest
import tempfile
import json
from unittest.mock import patch, MagicMock, call
from azure.cosmos.exceptions import CosmosHttpResponseError

from src.migrators.cosmosdb import CosmosDBMigrator
from src.migrators.blob_storage import BlobStorageMigrator


class TestCosmosDBMigratorInitialization:
    """Test CosmosDBMigrator initialization."""

    def test_initialization(self, mock_cosmos_client):
        """Test migrator initialization."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")

            assert migrator.connection_string == "test-connection-string"
            assert migrator.client == mock_cosmos_client
            assert migrator.database is None
            assert migrator.containers == {}

    def test_initialization_with_manifest(self, mock_cosmos_client, mock_manifest):
        """Test initialization with manifest."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string", manifest=mock_manifest)

            assert migrator.manifest == mock_manifest


class TestCosmosDBDatabaseCreation:
    """Test Cosmos DB database creation."""

    def test_create_database_success(self, mock_cosmos_client, mock_manifest):
        """Test successful database creation."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string", manifest=mock_manifest)
            migrator.create_database("test_db", tags={"env": "test"})

            mock_cosmos_client.create_database.assert_called_once_with("test_db")
            assert migrator.database == mock_cosmos_client.create_database.return_value

    def test_create_database_already_exists(self, mock_cosmos_client):
        """Test handling of existing database."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            # Simulate database already exists error
            mock_cosmos_client.create_database.side_effect = CosmosHttpResponseError(
                status_code=409,
                message="Conflict"
            )

            migrator = CosmosDBMigrator("test-connection-string")
            migrator.create_database("test_db")

            # Should call get_database_client on conflict
            mock_cosmos_client.get_database_client.assert_called_once_with("test_db")

    def test_create_database_other_error(self, mock_cosmos_client):
        """Test handling of other database creation errors."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            mock_cosmos_client.create_database.side_effect = CosmosHttpResponseError(
                status_code=400,
                message="Bad Request"
            )

            migrator = CosmosDBMigrator("test-connection-string")

            with pytest.raises(CosmosHttpResponseError):
                migrator.create_database("test_db")


class TestCosmosDBContainerCreation:
    """Test Cosmos DB container creation."""

    def test_create_container_success(self, mock_cosmos_client, mock_manifest):
        """Test successful container creation."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string", manifest=mock_manifest)
            migrator.database = mock_cosmos_client.create_database.return_value

            migrator.create_container(
                "orders",
                partition_key="customer_id",
                throughput=1000,
            )

            assert "orders" in migrator.containers

    def test_create_container_without_database(self):
        """Test that container creation fails without database."""
        with patch('src.migrators.cosmosdb.CosmosClient'):
            migrator = CosmosDBMigrator("test-connection-string")

            with pytest.raises(ValueError, match="Database must be created first"):
                migrator.create_container("orders", partition_key="id")

    def test_create_container_with_custom_indexing(self, mock_cosmos_client):
        """Test container creation with custom indexing policy."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            migrator.database = mock_cosmos_client.create_database.return_value

            custom_policy = {
                "indexingMode": "lazy",
                "automatic": False,
            }

            migrator.create_container(
                "test",
                partition_key="id",
                indexing_policy=custom_policy,
            )

            assert "test" in migrator.containers

    def test_create_container_with_ttl(self, mock_cosmos_client, mock_manifest):
        """Test container creation with TTL."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string", manifest=mock_manifest)
            migrator.database = mock_cosmos_client.create_database.return_value

            migrator.create_container(
                "logs",
                partition_key="timestamp",
                ttl_seconds=86400,
            )

            assert "logs" in migrator.containers


class TestCosmosDBUpsertItems:
    """Test upserting items to Cosmos DB."""

    def test_upsert_items_batch_success(self, mock_cosmos_client, mock_manifest, sample_documents):
        """Test successful batch upsert."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string", manifest=mock_manifest)
            migrator.database = mock_cosmos_client.create_database.return_value
            migrator.containers["orders"] = mock_cosmos_client.get_database_client.return_value

            result = migrator.upsert_items_batch(
                "orders",
                sample_documents,
                batch_number=1,
            )

            assert result["successful"] == len(sample_documents)
            assert result["failed"] == 0
            assert result["batch_number"] == 1
            assert result["container"] == "orders"

    def test_upsert_items_batch_with_failures(self, mock_cosmos_client):
        """Test batch upsert with some failures."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            mock_container = MagicMock()
            migrator.containers["orders"] = mock_container

            # First item succeeds, second fails
            mock_container.upsert_item.side_effect = [
                None,  # Success
                CosmosHttpResponseError(status_code=429, message="Too many requests"),
            ]

            items = [
                {"id": "1", "name": "Item 1"},
                {"id": "2", "name": "Item 2"},
            ]

            result = migrator.upsert_items_batch("orders", items, retry_attempts=1)

            assert result["successful"] == 1
            assert result["failed"] == 1

    def test_upsert_items_batch_with_retry(self, mock_cosmos_client):
        """Test retry logic for failed items."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            mock_container = MagicMock()
            migrator.containers["orders"] = mock_container

            # Fail twice, then succeed
            mock_container.upsert_item.side_effect = [
                CosmosHttpResponseError(status_code=429, message="Throttled"),
                CosmosHttpResponseError(status_code=429, message="Throttled"),
                None,  # Success on third attempt
            ]

            items = [{"id": "1", "name": "Item 1"}]
            result = migrator.upsert_items_batch("orders", items, retry_attempts=3)

            assert result["successful"] == 1
            assert mock_container.upsert_item.call_count == 3

    def test_upsert_items_batch_container_not_found(self, mock_cosmos_client):
        """Test error when container not found."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")

            with pytest.raises(ValueError, match="Container not found"):
                migrator.upsert_items_batch("nonexistent", [])

    def test_upsert_items_auto_generate_ids(self, mock_cosmos_client):
        """Test auto-generating IDs for items without id."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            mock_container = MagicMock()
            migrator.containers["orders"] = mock_container

            items = [{"name": "Item 1"}, {"name": "Item 2"}]
            migrator.upsert_items_batch("orders", items)

            # Verify that items now have IDs
            for call_obj in mock_container.upsert_item.call_args_list:
                item = call_obj[0][0]
                assert "id" in item


class TestCosmosDBQueryAndStats:
    """Test querying and getting statistics."""

    def test_query_items(self, mock_cosmos_client):
        """Test querying items from container."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            mock_container = MagicMock()
            mock_container.query_items.return_value = [
                {"id": "1", "name": "Item 1"},
                {"id": "2", "name": "Item 2"},
            ]
            migrator.containers["orders"] = mock_container

            results = migrator.query_items(
                "orders",
                "SELECT * FROM c WHERE c.status = @status",
                parameters=[{"name": "@status", "value": "active"}],
            )

            assert len(results) == 2
            mock_container.query_items.assert_called_once()

    def test_get_container_stats(self, mock_cosmos_client):
        """Test getting container statistics."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            mock_container = MagicMock()
            mock_container.query_items.return_value = [100]  # Document count
            migrator.containers["orders"] = mock_container

            stats = migrator.get_container_stats("orders")

            assert stats["document_count"] == 100
            assert stats["status"] == "active"


class TestBlobStorageMigratorInitialization:
    """Test BlobStorageMigrator initialization."""

    def test_initialization(self, mock_blob_client):
        """Test migrator initialization."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string")

            assert migrator.connection_string == "test-connection-string"
            assert migrator.client == mock_blob_client
            assert migrator.containers == {}

    def test_initialization_with_manifest(self, mock_blob_client, mock_manifest):
        """Test initialization with manifest."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string", manifest=mock_manifest)

            assert migrator.manifest == mock_manifest


class TestBlobStorageContainerCreation:
    """Test blob storage container creation."""

    def test_create_container_success(self, mock_blob_client, mock_manifest):
        """Test successful container creation."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string", manifest=mock_manifest)
            migrator.create_container("documents")

            assert "documents" in migrator.containers

    def test_create_container_with_tags(self, mock_blob_client, mock_manifest):
        """Test container creation with tags."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string", manifest=mock_manifest)
            migrator.create_container("documents", tags={"env": "test", "app": "migrator"})

            assert "documents" in migrator.containers


class TestBlobStorageUpload:
    """Test blob upload functionality."""

    def test_upload_blob_success(self, mock_blob_client, mock_manifest):
        """Test successful blob upload."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp.write("test content")
                tmp_path = tmp.name

            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string", manifest=mock_manifest)
            migrator.containers["documents"] = mock_blob_client.create_container.return_value

            result = migrator.upload_blob(
                "documents",
                "test.txt",
                tmp_path,
                content_type="text/plain",
            )

            assert result["status"] == "success"
            assert result["container"] == "documents"
            assert result["blob_name"] == "test.txt"

    def test_upload_blob_file_not_found(self, mock_blob_client):
        """Test error when file not found."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string")
            migrator.containers["documents"] = mock_blob_client.create_container.return_value

            with pytest.raises(ValueError, match="File not found"):
                migrator.upload_blob(
                    "documents",
                    "test.txt",
                    "/nonexistent/file.txt",
                )

    def test_upload_blob_container_not_found(self, mock_blob_client):
        """Test error when container not found."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("test")
            tmp_path = tmp.name

        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string")

            with pytest.raises(ValueError, match="Container not found"):
                migrator.upload_blob("nonexistent", "test.txt", tmp_path)

    def test_upload_blobs_batch(self, mock_blob_client, mock_manifest):
        """Test batch blob upload."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp1:
            tmp1.write("content 1")
            path1 = tmp1.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp2:
            tmp2.write("content 2")
            path2 = tmp2.name

        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string", manifest=mock_manifest)
            migrator.containers["documents"] = mock_blob_client.create_container.return_value

            specs = [
                {"blob_name": "file1.txt", "file_path": path1},
                {"blob_name": "file2.txt", "file_path": path2},
            ]

            result = migrator.upload_blobs_batch("documents", specs, batch_number=1)

            assert result["batch_number"] == 1
            assert result["total_blobs"] == 2


class TestRollbackFunctionality:
    """Test rollback functionality."""

    def test_cosmos_delete_container(self, mock_cosmos_client):
        """Test deleting container for rollback."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            migrator.database = mock_cosmos_client.create_database.return_value
            migrator.containers["orders"] = mock_cosmos_client.get_database_client.return_value

            migrator.delete_container("orders")

            migrator.database.delete_container.assert_called_once_with("orders")
            assert "orders" not in migrator.containers

    def test_cosmos_delete_database(self, mock_cosmos_client):
        """Test deleting database for rollback."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string")
            migrator.database = mock_cosmos_client.create_database.return_value
            migrator.database.id = "test_db"

            migrator.delete_database()

            mock_cosmos_client.delete_database.assert_called_once_with("test_db")

    def test_blob_delete_container(self, mock_blob_client):
        """Test deleting blob container for rollback."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string")
            mock_container = MagicMock()
            mock_container.list_blobs.return_value = [
                MagicMock(name="blob1.txt"),
                MagicMock(name="blob2.txt"),
            ]
            migrator.containers["documents"] = mock_container

            migrator.delete_container("documents")

            assert "documents" not in migrator.containers


class TestManifestTracking:
    """Test manifest tracking during migration."""

    def test_cosmos_logs_resources_to_manifest(self, mock_cosmos_client, mock_manifest):
        """Test that Cosmos DB operations log to manifest."""
        with patch('src.migrators.cosmosdb.CosmosClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_cosmos_client

            migrator = CosmosDBMigrator("test-connection-string", manifest=mock_manifest)
            migrator.create_database("test_db", tags={"env": "test"})

            mock_manifest.log_resource.assert_called()

    def test_blob_logs_resources_to_manifest(self, mock_blob_client, mock_manifest):
        """Test that Blob Storage operations log to manifest."""
        with patch('src.migrators.blob_storage.BlobServiceClient') as mock_client_class:
            mock_client_class.from_connection_string.return_value = mock_blob_client

            migrator = BlobStorageMigrator("test-connection-string", manifest=mock_manifest)
            migrator.create_container("documents", tags={"env": "test"})

            mock_manifest.log_resource.assert_called()
