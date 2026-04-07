"""Pytest configuration and fixtures for tests."""

import pytest
from unittest.mock import MagicMock, patch

from src.utils.config import Config
from src.utils.manifest import MigrationManifest


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock(spec=Config)
    config.anthropic_api_key = "test-key"
    config.azure_cosmos_endpoint = "https://test.documents.azure.com:443/"
    config.azure_cosmos_key = "test-key"
    config.azure_storage_connection_string = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test=="
    config.source_mongodb_uri = "mongodb://localhost:27017/test"
    config.dry_run = False
    config.sample_size = 100
    return config


@pytest.fixture
def mock_manifest(tmp_path):
    """Create a temporary manifest for testing."""
    manifest_path = tmp_path / "test_manifest.json"
    manifest = MigrationManifest(str(manifest_path))
    return manifest


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            "id": "order-001",
            "customer_id": "cust-001",
            "order_date": "2024-01-15",
            "items": [
                {"sku": "SKU-001", "quantity": 2, "price": 29.99},
                {"sku": "SKU-002", "quantity": 1, "price": 49.99}
            ],
            "total": 109.97,
            "status": "completed"
        },
        {
            "id": "order-002",
            "customer_id": "cust-002",
            "order_date": "2024-01-16",
            "shipping_address": {
                "street": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip": "10001"
            },
            "items": [
                {"sku": "SKU-003", "quantity": 1}
            ],
            "status": "pending"
        },
        {
            "id": "order-003",
            "customer_id": "cust-001",
            "order_date": "2024-01-17",
            "items": [],
            "status": "cancelled"
        },
    ]


@pytest.fixture
def sample_csv_data(tmp_path):
    """Create sample CSV file for testing."""
    csv_file = tmp_path / "test_data.csv"
    csv_content = """id,name,email,age,active
1,John Doe,john@example.com,30,true
2,Jane Smith,jane@example.com,28,false
3,Bob Johnson,bob@example.com,35,true
"""
    csv_file.write_text(csv_content)
    return str(csv_file)


@pytest.fixture
def sample_json_data(tmp_path):
    """Create sample JSON file for testing."""
    json_file = tmp_path / "test_data.json"
    json_content = """[
    {"id": 1, "name": "Item 1", "category": "A"},
    {"id": 2, "name": "Item 2", "category": "B"},
    {"id": 3, "name": "Item 3", "category": "A"}
]"""
    json_file.write_text(json_content)
    return str(json_file)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = MagicMock()

    # Mock response for analysis
    message = MagicMock()
    message.content = [MagicMock(text='{"fields": ["id", "name", "email"], "patterns": ["sequential-id"]}')]
    message.usage = MagicMock(input_tokens=100, output_tokens=50)

    client.messages.create.return_value = message

    return client


@pytest.fixture
def mock_cosmos_client():
    """Mock Cosmos DB client."""
    from unittest.mock import MagicMock

    client = MagicMock()
    db = MagicMock()
    container = MagicMock()

    client.create_database.return_value = db
    client.get_database_client.return_value = db
    db.create_container.return_value = container
    db.get_container_client.return_value = container
    db.id = "test_db"

    container.upsert_item.return_value = {"id": "test"}
    container.query_items.return_value = [{"id": "test", "data": "value"}]

    return client


@pytest.fixture
def mock_blob_client():
    """Mock Blob Storage client."""
    from unittest.mock import MagicMock

    client = MagicMock()
    container = MagicMock()
    blob = MagicMock()

    client.create_container.return_value = container
    client.get_container_client.return_value = container
    container.get_blob_client.return_value = blob
    container.upload_blob = MagicMock()

    return client


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the Config singleton between tests."""
    Config._instance = None
    yield
    Config._instance = None
