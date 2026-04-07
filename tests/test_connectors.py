"""Tests for data connectors."""

import pytest
import json
from pathlib import Path

from src.connectors.json_csv import JsonCsvConnector


def test_load_json_file(sample_json_data):
    """Test loading JSON file."""
    data = JsonCsvConnector.load_json_file(sample_json_data)

    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0]["id"] == 1
    assert data[0]["name"] == "Item 1"


def test_load_csv_file(sample_csv_data):
    """Test loading CSV file."""
    records = JsonCsvConnector.load_csv_file(sample_csv_data)

    assert len(records) == 3
    assert records[0]["name"] == "John Doe"
    assert records[0]["email"] == "john@example.com"


def test_normalize_json_to_records(sample_documents):
    """Test JSON normalization."""
    # Test with list
    normalized = JsonCsvConnector.normalize_json_to_records(sample_documents)
    assert len(normalized) == 3

    # Test with single dict
    single = {"id": "1", "name": "Test"}
    normalized = JsonCsvConnector.normalize_json_to_records(single)
    assert len(normalized) == 1
    assert normalized[0] == single


def test_normalize_csv_records():
    """Test CSV record normalization."""
    records = [
        {"id": "1", "name": "John", "active": "true", "age": "30"},
        {"id": "2", "name": "Jane", "active": "false", "age": "28"},
    ]

    normalized = JsonCsvConnector.normalize_csv_records(records)

    assert len(normalized) == 2
    assert normalized[0]["active"] is True
    assert normalized[1]["active"] is False
    assert normalized[0]["age"] == 30


def test_flatten_nested_json():
    """Test JSON flattening."""
    data = {
        "id": "1",
        "user": {
            "name": "John",
            "address": {
                "city": "New York",
                "zip": "10001"
            }
        },
        "tags": ["tag1", "tag2"]
    }

    flattened = JsonCsvConnector.flatten_nested_json(data)

    assert "id" in flattened
    assert "user_name" in flattened
    assert "user_address_city" in flattened
    assert flattened["user_address_city"] == "New York"
    assert "tags[0]" in flattened


def test_stream_json_records(sample_json_data):
    """Test streaming JSON records."""
    batches = list(JsonCsvConnector.stream_json_records(sample_json_data, batch_size=2))

    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


def test_stream_csv_records(sample_csv_data):
    """Test streaming CSV records."""
    batches = list(JsonCsvConnector.stream_csv_records(sample_csv_data, batch_size=2))

    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


def test_detect_source_type(sample_json_data, sample_csv_data):
    """Test source type detection."""
    assert JsonCsvConnector.detect_source_type(sample_json_data) == "json"
    assert JsonCsvConnector.detect_source_type(sample_csv_data) == "csv"


def test_load_json_file_not_found():
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        JsonCsvConnector.load_json_file("/nonexistent/file.json")


def test_load_csv_file_not_found():
    """Test error handling for missing CSV file."""
    with pytest.raises(FileNotFoundError):
        JsonCsvConnector.load_csv_file("/nonexistent/file.csv")


def test_normalize_json_invalid_data():
    """Test error handling for invalid data type."""
    with pytest.raises(ValueError):
        JsonCsvConnector.normalize_json_to_records("invalid string")
