"""PII detection using regex patterns and Claude API for deeper analysis."""

import re
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PIIScanner:
    """Detect personally identifiable information in documents and fields."""

    # Regex patterns for common PII
    PII_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ipv4": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "passport": r"\b[A-Z]{1,2}\d{6,9}\b",
        "drivers_license": r"\b[A-Z]{1,2}\d{5,8}\b",
        "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b",
    }

    def __init__(self, anthropic_client: Optional[Anthropic] = None):
        """Initialize PII scanner.

        Args:
            anthropic_client: Anthropic client for deeper analysis
        """
        self.client = anthropic_client
        self.pii_report: Dict[str, Any] = {
            "fields_scanned": 0,
            "pii_detected": False,
            "findings": [],
            "recommendations": [],
        }

    def scan_field(self, field_name: str, field_value: Any) -> Dict[str, Any]:
        """Scan a single field for PII using regex patterns.

        Args:
            field_name: Name of the field
            field_value: Value to scan

        Returns:
            Scan result with detected PII types
        """
        result = {
            "field": field_name,
            "detected_patterns": [],
            "severity": "none",
            "raw_value": None,
        }

        if field_value is None:
            return result

        str_value = str(field_value)
        if not str_value:
            return result

        for pii_type, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, str_value):
                result["detected_patterns"].append(pii_type)
                self.pii_report["pii_detected"] = True

        # Determine severity based on detected patterns
        if result["detected_patterns"]:
            high_severity = {"ssn", "credit_card", "passport"}
            medium_severity = {"email", "phone", "iban", "drivers_license"}

            detected_set = set(result["detected_patterns"])
            if detected_set & high_severity:
                result["severity"] = "high"
            elif detected_set & medium_severity:
                result["severity"] = "medium"
            else:
                result["severity"] = "low"

        return result

    def scan_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Scan entire document for PII.

        Args:
            document: Document dictionary to scan

        Returns:
            Scan results with all findings
        """
        findings = []

        def scan_recursive(obj: Any, path: str = "") -> None:
            """Recursively scan nested structures."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if isinstance(value, (dict, list)):
                        scan_recursive(value, new_path)
                    else:
                        result = self.scan_field(new_path, value)
                        if result["detected_patterns"]:
                            findings.append(result)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    new_path = f"{path}[{idx}]"
                    if isinstance(item, (dict, list)):
                        scan_recursive(item, new_path)
                    else:
                        result = self.scan_field(new_path, item)
                        if result["detected_patterns"]:
                            findings.append(result)

        scan_recursive(document)

        return {
            "document_scan": True,
            "total_findings": len(findings),
            "findings": findings,
            "has_high_severity": any(f["severity"] == "high" for f in findings),
        }

    def analyze_with_claude(
        self,
        sample_documents: List[Dict[str, Any]],
        anthropic_api_key: str,
    ) -> Dict[str, Any]:
        """Use Claude API for deeper PII analysis on sample data.

        Args:
            sample_documents: Sample documents to analyze
            anthropic_api_key: Anthropic API key

        Returns:
            Deeper analysis results from Claude
        """
        if not self.client:
            self.client = Anthropic(api_key=anthropic_api_key)

        # Prepare sample for analysis (truncate if needed)
        sample_text = str(sample_documents[:3])[:2000]

        system_prompt = """You are a data privacy expert specializing in PII detection.
        Analyze the provided document samples for personally identifiable information.

        Identify:
        1. Types of PII present (SSN, credit card, email, phone, etc.)
        2. Fields that appear to contain PII
        3. Severity levels (high, medium, low)
        4. Recommended remediation actions (encrypt, mask, exclude, flag)

        Provide structured analysis."""

        user_message = f"""Analyze these document samples for PII:

        {sample_text}

        Provide a structured analysis in JSON format."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            analysis_text = message.content[0].text

            # Parse response
            return {
                "claude_analysis": analysis_text,
                "model": "claude-3-5-sonnet-20241022",
                "tokens_used": message.usage.input_tokens
                + message.usage.output_tokens,
            }

        except Exception as e:
            logger.error(f"Claude PII analysis failed: {e}")
            return {
                "error": str(e),
                "fallback": "Using regex-only analysis",
            }

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive PII detection report.

        Returns:
            PII detection report with findings and recommendations
        """
        recommendations = []

        if self.pii_report["pii_detected"]:
            high_severity_found = any(
                f["severity"] == "high" for f in self.pii_report["findings"]
            )

            if high_severity_found:
                recommendations.append(
                    {
                        "action": "encrypt",
                        "priority": "critical",
                        "description": "Encrypt fields containing high-severity PII at rest and in transit",
                    }
                )
                recommendations.append(
                    {
                        "action": "azure_purview",
                        "priority": "critical",
                        "description": "Register data sources with Azure Purview for data governance",
                    }
                )

            recommendations.extend([
                {
                    "action": "mask_sensitive_fields",
                    "priority": "high",
                    "description": "Apply data masking policies to detected PII fields",
                },
                {
                    "action": "access_control",
                    "priority": "high",
                    "description": "Implement role-based access controls for data containing PII",
                },
                {
                    "action": "audit_logging",
                    "priority": "medium",
                    "description": "Enable comprehensive audit logging for PII access",
                },
            ])

        self.pii_report["recommendations"] = recommendations

        return self.pii_report

    def reset(self) -> None:
        """Reset scanner state for next scan."""
        self.pii_report = {
            "fields_scanned": 0,
            "pii_detected": False,
            "findings": [],
            "recommendations": [],
        }
