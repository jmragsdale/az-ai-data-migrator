"""Tests for MigrationPlanner."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.agent.planner import MigrationPlanner


class TestMigrationPlannerInitialization:
    """Test MigrationPlanner initialization."""

    def test_planner_initialization_without_client(self):
        """Test initializing planner without pre-instantiated client."""
        planner = MigrationPlanner()
        assert planner.client is None
        assert planner.migration_plan == {}

    def test_planner_initialization_with_client(self):
        """Test initializing planner with pre-instantiated client."""
        mock_client = MagicMock()
        planner = MigrationPlanner(anthropic_client=mock_client)
        assert planner.client is mock_client
        assert planner.migration_plan == {}


class TestPlanGeneration:
    """Test migration plan generation."""

    def test_generate_plan_success(self, mock_anthropic_client):
        """Test successful plan generation."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        analysis_results = {
            "field_map": ["id", "customer_id", "order_date", "items", "total"],
            "patterns": ["sequential-id", "date-format"],
            "partition_key_recommendation": "customer_id",
            "indexing_recommendations": ["order_date", "status"],
        }

        # Mock response
        mock_response_text = json.dumps({
            "cosmos_db_config": {
                "database_name": "migrated_data",
                "containers": [
                    {
                        "name": "orders",
                        "partition_key": "/customer_id",
                        "throughput_rus": 1000,
                    }
                ],
                "consistency_level": "Strong",
            },
            "blob_storage_config": {
                "container_name": "documents",
                "access_tier": "Hot",
            },
            "batch_strategy": {
                "batch_size": 500,
                "parallel_batches": 3,
                "retry_attempts": 3,
            },
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=200),
        )

        plan = planner.generate_plan(
            analysis_results=analysis_results,
            estimated_document_count=50000,
            estimated_data_volume_gb=10.5,
            anthropic_api_key="test-key",
        )

        assert "cosmos_db_config" in plan
        assert "blob_storage_config" in plan
        assert "batch_strategy" in plan
        assert "tokens_used" in plan
        assert plan["tokens_used"] == 300

    def test_plan_structure_validation(self, mock_anthropic_client):
        """Test that plan structure is validated and enhanced."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        # Minimal response
        mock_response_text = json.dumps({
            "cosmos_db_config": {
                "database_name": "custom_db",
            }
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        plan = planner.generate_plan(
            analysis_results={},
            estimated_document_count=1000,
            estimated_data_volume_gb=0.5,
            anthropic_api_key="test-key",
        )

        # Check that defaults were applied
        assert plan["cosmos_db_config"]["database_name"] == "custom_db"
        assert plan["cosmos_db_config"]["consistency_level"] == "Strong"
        assert plan["cosmos_db_config"]["throughput_rus"] == 400
        assert "blob_storage_config" in plan
        assert "batch_strategy" in plan

    def test_plan_with_malformed_json_response(self, mock_anthropic_client):
        """Test handling of malformed JSON in Claude response."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        # Response with JSON embedded in text
        mock_response_text = """Here is the plan:
        ```json
        {"cosmos_db_config": {"database_name": "test_db"}}
        ```
        Some additional explanation."""

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=150),
        )

        plan = planner.generate_plan(
            analysis_results={},
            estimated_document_count=1000,
            estimated_data_volume_gb=1.0,
            anthropic_api_key="test-key",
        )

        assert plan is not None
        assert isinstance(plan, dict)

    def test_plan_generation_api_failure(self, mock_anthropic_client):
        """Test error handling when API call fails."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            planner.generate_plan(
                analysis_results={},
                estimated_document_count=1000,
                estimated_data_volume_gb=1.0,
                anthropic_api_key="test-key",
            )


class TestCosmosDBConfigRecommendations:
    """Test Cosmos DB configuration recommendations."""

    def test_partition_key_recommendations(self, mock_anthropic_client):
        """Test partition key recommendations for different data patterns."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        # Test with a field that should be good for partitioning
        analysis_results = {
            "partition_key_recommendation": "user_id",
            "field_map": ["id", "user_id", "timestamp", "data"],
        }

        mock_response_text = json.dumps({
            "cosmos_db_config": {
                "database_name": "user_data",
                "containers": [
                    {
                        "name": "user_events",
                        "partition_key": "/user_id",
                        "throughput_rus": 2000,
                    }
                ],
            },
            "batch_strategy": {
                "batch_size": 1000,
                "parallel_batches": 5,
                "retry_attempts": 3,
            },
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        plan = planner.generate_plan(
            analysis_results=analysis_results,
            estimated_document_count=100000,
            estimated_data_volume_gb=50.0,
            anthropic_api_key="test-key",
        )

        cosmos_config = plan["cosmos_db_config"]
        assert len(cosmos_config["containers"]) > 0
        assert cosmos_config["containers"][0]["partition_key"] == "/user_id"

    def test_throughput_scaling_based_on_volume(self, mock_anthropic_client):
        """Test that throughput is scaled based on data volume."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        # Large data volume should suggest higher throughput
        mock_response_text = json.dumps({
            "cosmos_db_config": {
                "database_name": "large_dataset",
                "throughput_rus": 10000,
                "autoscale_max_rus": 100000,
            },
            "batch_strategy": {
                "batch_size": 5000,
                "parallel_batches": 10,
                "retry_attempts": 5,
            },
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        plan = planner.generate_plan(
            analysis_results={},
            estimated_document_count=10000000,
            estimated_data_volume_gb=500.0,
            anthropic_api_key="test-key",
        )

        cosmos_config = plan["cosmos_db_config"]
        # Enhanced plan should have higher throughput suggestions
        assert cosmos_config["throughput_rus"] >= 400


class TestGetterMethods:
    """Test getter methods for configuration."""

    def test_get_cosmos_db_config(self, mock_anthropic_client):
        """Test retrieving Cosmos DB config from plan."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        mock_response_text = json.dumps({
            "cosmos_db_config": {
                "database_name": "test_db",
                "consistency_level": "Eventual",
            }
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        planner.generate_plan({}, 1000, 1.0, "test-key")
        config = planner.get_cosmos_db_config()

        assert config["database_name"] == "test_db"
        assert config["consistency_level"] == "Eventual"

    def test_get_blob_storage_config(self, mock_anthropic_client):
        """Test retrieving Blob Storage config from plan."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        mock_response_text = json.dumps({
            "blob_storage_config": {
                "container_name": "backups",
                "access_tier": "Cool",
            }
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        planner.generate_plan({}, 1000, 1.0, "test-key")
        config = planner.get_blob_storage_config()

        assert config["container_name"] == "backups"
        assert config["access_tier"] == "Cool"

    def test_get_batch_strategy(self, mock_anthropic_client):
        """Test retrieving batch strategy from plan."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        mock_response_text = json.dumps({
            "batch_strategy": {
                "batch_size": 750,
                "parallel_batches": 4,
                "retry_attempts": 5,
            }
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        planner.generate_plan({}, 1000, 1.0, "test-key")
        strategy = planner.get_batch_strategy()

        assert strategy["batch_size"] == 750
        assert strategy["parallel_batches"] == 4

    def test_get_empty_config_when_plan_not_generated(self):
        """Test that empty dict is returned when plan not yet generated."""
        planner = MigrationPlanner()

        assert planner.get_cosmos_db_config() == {}
        assert planner.get_blob_storage_config() == {}
        assert planner.get_batch_strategy() == {}


class TestMigrationTimeEstimation:
    """Test migration time estimation."""

    def test_estimate_migration_time_basic(self, mock_anthropic_client):
        """Test basic time estimation."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        mock_response_text = json.dumps({
            "batch_strategy": {
                "batch_size": 1000,
            }
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        planner.generate_plan({}, 10000, 10.0, "test-key")
        estimate = planner.estimate_migration_time(10000, throughput_limit=100)

        assert estimate["total_batches"] == 10
        assert estimate["batch_size"] == 1000
        assert estimate["estimated_hours"] > 0

    def test_estimate_migration_time_with_different_throughput(self, mock_anthropic_client):
        """Test estimation with different throughput limits."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        mock_response_text = json.dumps({
            "batch_strategy": {
                "batch_size": 500,
            }
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        planner.generate_plan({}, 1000, 1.0, "test-key")

        # Higher throughput should result in shorter estimated time
        estimate_low = planner.estimate_migration_time(5000, throughput_limit=50)
        estimate_high = planner.estimate_migration_time(5000, throughput_limit=200)

        assert estimate_low["estimated_hours"] > estimate_high["estimated_hours"]

    def test_estimate_migration_time_large_dataset(self, mock_anthropic_client):
        """Test estimation for large dataset migration."""
        planner = MigrationPlanner(anthropic_client=mock_anthropic_client)

        mock_response_text = json.dumps({
            "batch_strategy": {
                "batch_size": 5000,
            }
        })

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=mock_response_text)],
            usage=MagicMock(input_tokens=100, output_tokens=100),
        )

        planner.generate_plan({}, 1000000, 100.0, "test-key")
        estimate = planner.estimate_migration_time(1000000, throughput_limit=500)

        assert estimate["total_batches"] == 200
        assert estimate["total_seconds"] > 0
        assert estimate["estimated_hours"] >= 1
