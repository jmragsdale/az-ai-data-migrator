"""Tests for PII Scanner."""

import pytest
from unittest.mock import patch, MagicMock

from src.security.pii_scanner import PIIScanner


class TestPIIPatternDetection:
    """Test PII pattern detection using regex."""

    def test_detect_ssn(self):
        """Test Social Security Number detection."""
        scanner = PIIScanner()
        result = scanner.scan_field("ssn", "123-45-6789")

        assert "ssn" in result["detected_patterns"]
        assert result["severity"] == "high"

    def test_detect_email(self):
        """Test email address detection."""
        scanner = PIIScanner()
        result = scanner.scan_field("email", "john.doe@example.com")

        assert "email" in result["detected_patterns"]
        assert result["severity"] == "medium"

    def test_detect_phone_number(self):
        """Test phone number detection."""
        scanner = PIIScanner()

        # Standard US format
        result = scanner.scan_field("phone", "(555) 123-4567")
        assert "phone" in result["detected_patterns"]

        # Dot format
        result = scanner.scan_field("phone", "555.123.4567")
        assert "phone" in result["detected_patterns"]

        # Dash format
        result = scanner.scan_field("phone", "555-123-4567")
        assert "phone" in result["detected_patterns"]

    def test_detect_credit_card(self):
        """Test credit card number detection."""
        scanner = PIIScanner()

        # Standard credit card format
        result = scanner.scan_field("card", "4532-1234-5678-9010")
        assert "credit_card" in result["detected_patterns"]
        assert result["severity"] == "high"

        # No-dash format
        result = scanner.scan_field("card", "4532123456789010")
        assert "credit_card" in result["detected_patterns"]

    def test_detect_ipv4(self):
        """Test IPv4 address detection."""
        scanner = PIIScanner()
        result = scanner.scan_field("ip", "192.168.1.1")

        assert "ipv4" in result["detected_patterns"]

    def test_detect_passport(self):
        """Test passport number detection."""
        scanner = PIIScanner()
        result = scanner.scan_field("passport", "AB123456")

        assert "passport" in result["detected_patterns"]

    def test_detect_drivers_license(self):
        """Test driver's license detection."""
        scanner = PIIScanner()
        result = scanner.scan_field("license", "CA12345678")

        assert "drivers_license" in result["detected_patterns"]

    def test_detect_iban(self):
        """Test IBAN detection."""
        scanner = PIIScanner()
        result = scanner.scan_field("iban", "DE89370400440532013000")

        assert "iban" in result["detected_patterns"]


class TestCleanDataNoDetection:
    """Test that clean data produces no PII flags."""

    def test_no_pii_in_names(self):
        """Test that regular names don't trigger false positives."""
        scanner = PIIScanner()
        result = scanner.scan_field("name", "John Smith")

        assert len(result["detected_patterns"]) == 0
        assert result["severity"] == "none"

    def test_no_pii_in_addresses(self):
        """Test that regular addresses don't trigger false positives."""
        scanner = PIIScanner()
        result = scanner.scan_field("address", "123 Main Street, Anytown, USA")

        assert len(result["detected_patterns"]) == 0
        assert result["severity"] == "none"

    def test_no_pii_in_dates(self):
        """Test that dates don't trigger false positives."""
        scanner = PIIScanner()
        result = scanner.scan_field("date", "2024-01-15")

        assert len(result["detected_patterns"]) == 0
        assert result["severity"] == "none"

    def test_no_pii_in_product_ids(self):
        """Test that product IDs don't trigger false positives."""
        scanner = PIIScanner()
        result = scanner.scan_field("product_id", "PROD-123-456-789")

        assert len(result["detected_patterns"]) == 0

    def test_null_value_handling(self):
        """Test handling of null/None values."""
        scanner = PIIScanner()
        result = scanner.scan_field("optional_field", None)

        assert len(result["detected_patterns"]) == 0
        assert result["severity"] == "none"

    def test_empty_string_handling(self):
        """Test handling of empty strings."""
        scanner = PIIScanner()
        result = scanner.scan_field("empty_field", "")

        assert len(result["detected_patterns"]) == 0


class TestDocumentScanning:
    """Test scanning entire documents."""

    def test_scan_document_with_pii(self):
        """Test scanning document containing PII."""
        scanner = PIIScanner()

        document = {
            "id": "cust-001",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-123-4567",
            "ssn": "123-45-6789",
        }

        result = scanner.scan_document(document)

        assert result["document_scan"] is True
        assert result["total_findings"] > 0
        assert result["has_high_severity"] is True

    def test_scan_document_without_pii(self):
        """Test scanning document without PII."""
        scanner = PIIScanner()

        document = {
            "id": "order-001",
            "customer_id": "cust-001",
            "order_date": "2024-01-15",
            "total": 99.99,
            "status": "completed",
        }

        result = scanner.scan_document(document)

        assert result["document_scan"] is True
        assert result["total_findings"] == 0
        assert result["has_high_severity"] is False

    def test_scan_nested_document(self):
        """Test scanning nested document structure."""
        scanner = PIIScanner()

        document = {
            "id": "order-001",
            "customer": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "555-987-6543",
            },
            "shipping": {
                "address": "123 Main St",
                "city": "Anytown",
            },
            "payment": {
                "card": "4532-1234-5678-9010",
            },
        }

        result = scanner.scan_document(document)

        assert result["total_findings"] > 0
        findings = result["findings"]
        assert any("email" in f["field"] for f in findings)
        assert any("card" in f["field"] for f in findings)

    def test_scan_document_with_arrays(self):
        """Test scanning document with array fields."""
        scanner = PIIScanner()

        document = {
            "id": "order-001",
            "contact_emails": [
                "john@example.com",
                "jane@example.com",
            ],
            "phone_numbers": [
                "555-123-4567",
                "555-987-6543",
            ],
            "items": [
                {"sku": "SKU-001", "price": 29.99},
                {"sku": "SKU-002", "price": 49.99},
            ],
        }

        result = scanner.scan_document(document)

        assert result["total_findings"] > 0
        assert any("[0]" in f["field"] for f in result["findings"])


class TestSeverityLevels:
    """Test PII severity level assignment."""

    def test_high_severity_pii(self):
        """Test identification of high-severity PII."""
        scanner = PIIScanner()

        # SSN is high severity
        result = scanner.scan_field("ssn", "123-45-6789")
        assert result["severity"] == "high"

        # Credit card is high severity
        result = scanner.scan_field("card", "4532-1234-5678-9010")
        assert result["severity"] == "high"

        # Passport is high severity
        result = scanner.scan_field("passport", "AB123456")
        assert result["severity"] == "high"

    def test_medium_severity_pii(self):
        """Test identification of medium-severity PII."""
        scanner = PIIScanner()

        # Email is medium severity
        result = scanner.scan_field("email", "john@example.com")
        assert result["severity"] == "medium"

        # Phone is medium severity
        result = scanner.scan_field("phone", "555-123-4567")
        assert result["severity"] == "medium"

        # IBAN is medium severity
        result = scanner.scan_field("iban", "DE89370400440532013000")
        assert result["severity"] == "medium"

    def test_low_severity_pii(self):
        """Test identification of low-severity PII."""
        scanner = PIIScanner()

        # IPv4 is low severity
        result = scanner.scan_field("ip", "192.168.1.1")
        assert result["severity"] == "low"


class TestReportGeneration:
    """Test PII detection report generation."""

    def test_generate_report_with_pii(self):
        """Test report generation with detected PII."""
        scanner = PIIScanner()

        # Simulate scanning multiple documents
        document = {
            "email": "test@example.com",
            "ssn": "123-45-6789",
        }

        scanner.scan_document(document)
        report = scanner.generate_report()

        assert report["pii_detected"] is True
        assert len(report["findings"]) > 0
        assert len(report["recommendations"]) > 0

    def test_generate_report_without_pii(self):
        """Test report generation without PII."""
        scanner = PIIScanner()

        document = {
            "id": "test-001",
            "name": "Test Item",
            "price": 99.99,
        }

        scanner.scan_document(document)
        report = scanner.generate_report()

        assert report["pii_detected"] is False
        assert len(report["findings"]) == 0

    def test_report_recommendations_for_high_severity(self):
        """Test that high-severity PII triggers critical recommendations."""
        scanner = PIIScanner()

        document = {
            "ssn": "123-45-6789",
            "card": "4532-1234-5678-9010",
        }

        scanner.scan_document(document)
        report = scanner.generate_report()

        recommendations = report["recommendations"]

        # Should include encryption recommendation
        encrypt_recs = [r for r in recommendations if r["action"] == "encrypt"]
        assert len(encrypt_recs) > 0
        assert encrypt_recs[0]["priority"] == "critical"

        # Should include Azure Purview recommendation
        purview_recs = [r for r in recommendations if r["action"] == "azure_purview"]
        assert len(purview_recs) > 0

    def test_report_recommendations_for_medium_severity(self):
        """Test recommendations for medium-severity PII."""
        scanner = PIIScanner()

        document = {
            "email": "test@example.com",
            "phone": "555-123-4567",
        }

        scanner.scan_document(document)
        report = scanner.generate_report()

        recommendations = report["recommendations"]

        # Should include masking recommendation
        mask_recs = [r for r in recommendations if r["action"] == "mask_sensitive_fields"]
        assert len(mask_recs) > 0
        assert mask_recs[0]["priority"] == "high"

        # Should include access control recommendation
        access_recs = [r for r in recommendations if r["action"] == "access_control"]
        assert len(access_recs) > 0


class TestClaudeIntegration:
    """Test Claude API integration for deeper analysis."""

    @patch('src.security.pii_scanner.Anthropic')
    def test_analyze_with_claude(self, mock_anthropic_class, sample_documents):
        """Test Claude-based PII analysis."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock Claude response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"pii_found": true, "fields": ["email", "phone"]}')]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
        mock_client.messages.create.return_value = mock_response

        scanner = PIIScanner()
        result = scanner.analyze_with_claude(sample_documents, "test-key")

        assert "claude_analysis" in result
        assert "tokens_used" in result
        assert result["tokens_used"] == 150

    @patch('src.security.pii_scanner.Anthropic')
    def test_analyze_with_claude_error_handling(self, mock_anthropic_class, sample_documents):
        """Test error handling in Claude analysis."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_client.messages.create.side_effect = Exception("API Error")

        scanner = PIIScanner()
        result = scanner.analyze_with_claude(sample_documents, "test-key")

        assert "error" in result
        assert "fallback" in result


class TestScannerState:
    """Test scanner state management."""

    def test_multiple_scans_accumulate(self):
        """Test that multiple scans accumulate findings."""
        scanner = PIIScanner()

        doc1 = {"email": "test@example.com"}
        doc2 = {"phone": "555-123-4567"}

        result1 = scanner.scan_document(doc1)
        result2 = scanner.scan_document(doc2)

        assert result1["total_findings"] > 0
        assert result2["total_findings"] > 0

    def test_reset_scanner_state(self):
        """Test resetting scanner state."""
        scanner = PIIScanner()

        document = {"ssn": "123-45-6789"}
        scanner.scan_document(document)

        scanner.reset()

        assert scanner.pii_report["pii_detected"] is False
        assert len(scanner.pii_report["findings"]) == 0

    def test_mixed_pii_in_single_field(self):
        """Test detection of multiple PII types in single field."""
        scanner = PIIScanner()

        # Text with both phone and email
        text = "Contact: john@example.com or 555-123-4567"
        result = scanner.scan_field("contact", text)

        assert "email" in result["detected_patterns"]
        assert "phone" in result["detected_patterns"]
        assert result["severity"] == "medium"  # Highest of the two


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_document(self):
        """Test scanning very long documents."""
        scanner = PIIScanner()

        # Create large document
        document = {
            f"field_{i}": f"value_{i}" for i in range(100)
        }
        document["email"] = "test@example.com"

        result = scanner.scan_document(document)

        # Should still find the email
        assert any("email" in f["field"] for f in result["findings"])

    def test_deeply_nested_structure(self):
        """Test scanning deeply nested structures."""
        scanner = PIIScanner()

        document = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "ssn": "123-45-6789"
                        }
                    }
                }
            }
        }

        result = scanner.scan_document(document)

        assert result["total_findings"] > 0
        assert any("ssn" in f["field"] for f in result["findings"])

    def test_special_characters_in_values(self):
        """Test handling of special characters."""
        scanner = PIIScanner()

        # Email with special characters
        result = scanner.scan_field("email", "john+test@example.co.uk")
        assert "email" in result["detected_patterns"]

        # IP address with leading zeros
        result = scanner.scan_field("ip", "192.001.001.001")
        assert "ipv4" in result["detected_patterns"]

    def test_unicode_content(self):
        """Test handling of unicode content."""
        scanner = PIIScanner()

        document = {
            "name": "José García",
            "email": "josé@example.com",
            "phone": "555-123-4567",
        }

        result = scanner.scan_document(document)

        # Should still detect email and phone
        assert any("email" in f["field"] for f in result["findings"])
        assert any("phone" in f["field"] for f in result["findings"])
