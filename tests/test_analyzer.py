"""Tests for SchemaAnalyzer."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.agent.analyzer import SchemaAnalyzer


def test_analyzer_initialization():
    """Test SchemaAnalyzer initialization."""
    analyzer = SchemaAnalyzer()
    assert analyzer.client is None
    assert analyzer.analysis_results["field_map"] == {}


def test_detect_field_types(sample_documents):
    """Test field type detection."""
    analyzer = SchemaAnalyzer()
    field_types = analyzer.detect_field_types(sample_documents)

    assert "id" in field_types
    assert "string" in field_types["id"]
    assert "items" in field_types
    assert "array" in field_types["items"]
    assert "total" in field_types
    assert "number" in field_types["total"]


def test_find_inconsistencies(sample_documents):
    """Test inconsistency detection."""
    analyzer = SchemaAnalyzer()
    inconsistencies = analyzer.find_inconsistencies(sample_documents)

    # Check for missing fields
    missing_field_issues = [i for i in inconsistencies if i["type"] == "missing_field"]
    assert len(missing_field_issues) > 0

    # Shipping address should be missing in some documents
    shipping_issues = [i for i in missing_field_issues if i["field"] == "shipping_address"]
    assert len(shipping_issues) > 0


def test_detect_field_types_with_nulls():
    """Test field type detection with null values."""
    analyzer = SchemaAnalyzer()

    samples = [
        {"id": "1", "value": None},
        {"id": "2", "value": "text"},
        {"id": "3"},
    ]

    field_types = analyzer.detect_field_types(samples)

    assert "null" in field_types["value"]
    assert "string" in field_types["value"]


@patch('src.agent.analyzer.Anthropic')
def test_analyze_samples_with_claude(mock_anthropic_class, sample_documents, mock_anthropic_client):
    """Test Claude-based analysis."""
    mock_anthropic_class.return_value = mock_anthropic_client

    analyzer = SchemaAnalyzer()
    results = analyzer.analyze_samples(sample_documents, "test-key")

    assert "field_map" in results
    assert "patterns" in results
    assert "tokens_used" in results


def test_get_analysis_summary(sample_documents):
    """Test analysis summary generation."""
    analyzer = SchemaAnalyzer()

    # Manually set analysis results
    analyzer.analysis_results = {
        "field_map": ["id", "customer_id", "order_date", "items", "total", "status"],
        "patterns": ["sequential-id", "date-format"],
        "inconsistencies": [
            {"field": "shipping_address", "type": "missing_field"},
            {"field": "items", "type": "type_mismatch"}
        ],
        "partition_key_recommendation": "customer_id",
        "indexing_recommendations": ["order_date", "status"],
    }

    summary = analyzer.get_analysis_summary()

    assert summary["total_fields"] == 6
    assert summary["patterns_found"] == 2
    assert summary["inconsistencies_found"] == 2
    assert summary["partition_key_recommendation"] == "customer_id"
    assert summary["indexing_count"] == 2


def test_analyze_samples_error_handling(sample_documents):
    """Test error handling in analysis."""
    analyzer = SchemaAnalyzer()

    with patch('src.agent.analyzer.Anthropic') as mock_anthropic_class:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic_class.return_value = mock_client

        with pytest.raises(Exception):
            analyzer.analyze_samples(sample_documents, "test-key")
