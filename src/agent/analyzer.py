"""Schema analysis using Claude API for intelligent document understanding."""

import json
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SchemaAnalyzer:
    """Analyze raw document samples to infer schemas and detect patterns."""

    def __init__(self, anthropic_client: Optional[Anthropic] = None):
        """Initialize schema analyzer.

        Args:
            anthropic_client: Anthropic client for API calls
        """
        self.client = anthropic_client
        self.analysis_results: Dict[str, Any] = {
            "field_map": {},
            "patterns": [],
            "inconsistencies": [],
            "inferred_types": {},
        }

    def analyze_samples(
        self,
        samples: List[Dict[str, Any]],
        anthropic_api_key: str,
    ) -> Dict[str, Any]:
        """Analyze raw document samples to infer schema and patterns.

        Args:
            samples: List of sample documents
            anthropic_api_key: Anthropic API key for Claude calls

        Returns:
            Analysis results with field map, patterns, and inconsistencies
        """
        if not self.client:
            self.client = Anthropic(api_key=anthropic_api_key)

        # Prepare analysis input
        sample_text = json.dumps(samples[:5], indent=2)[:2000]

        system_prompt = """You are an expert data schema analyzer for cloud migrations.
        Analyze the provided document samples and generate insights about the data structure.

        Your analysis should identify:
        1. All fields present across documents
        2. Data types for each field
        3. Patterns and relationships
        4. Inconsistencies and missing fields
        5. Recommended partition keys for Cosmos DB
        6. Suggested indexing strategy

        Provide structured analysis in JSON format."""

        user_message = f"""Analyze these document samples and provide schema insights:

        {sample_text}

        Provide a structured JSON analysis with:
        - fields: List of all fields found
        - field_types: Inferred types for each field
        - patterns: Detected patterns in the data
        - inconsistencies: Fields present in some but not all documents
        - partition_key_recommendation: Best field for partitioning
        - indexing_recommendations: Fields to index"""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = message.content[0].text

            # Parse response
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Claude might wrap response, try to extract JSON
                import re
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {"raw_response": response_text}

            self.analysis_results = {
                "field_map": analysis.get("fields", []),
                "field_types": analysis.get("field_types", {}),
                "patterns": analysis.get("patterns", []),
                "inconsistencies": analysis.get("inconsistencies", []),
                "partition_key_recommendation": analysis.get(
                    "partition_key_recommendation"
                ),
                "indexing_recommendations": analysis.get(
                    "indexing_recommendations", []
                ),
                "tokens_used": message.usage.input_tokens
                + message.usage.output_tokens,
            }

            logger.info(
                f"Schema analysis complete. Found {len(self.analysis_results['field_map'])} fields"
            )
            return self.analysis_results

        except Exception as e:
            logger.error(f"Schema analysis failed: {e}")
            raise

    def detect_field_types(
        self, samples: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Detect field types by analyzing sample values.

        Args:
            samples: List of sample documents

        Returns:
            Dictionary mapping fields to detected types
        """
        field_types: Dict[str, set] = {}

        for sample in samples:
            for field, value in sample.items():
                if field not in field_types:
                    field_types[field] = set()

                if value is None:
                    field_types[field].add("null")
                elif isinstance(value, bool):
                    field_types[field].add("boolean")
                elif isinstance(value, int):
                    field_types[field].add("integer")
                elif isinstance(value, float):
                    field_types[field].add("number")
                elif isinstance(value, str):
                    field_types[field].add("string")
                elif isinstance(value, dict):
                    field_types[field].add("object")
                elif isinstance(value, list):
                    field_types[field].add("array")

        return {k: sorted(list(v)) for k, v in field_types.items()}

    def find_inconsistencies(
        self, samples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find schema inconsistencies across documents.

        Args:
            samples: List of sample documents

        Returns:
            List of inconsistencies found
        """
        inconsistencies = []

        # Find fields that appear in some but not all documents
        all_fields = set()
        for sample in samples:
            all_fields.update(sample.keys())

        for field in all_fields:
            present_count = sum(1 for s in samples if field in s)
            total_count = len(samples)

            if 0 < present_count < total_count:
                inconsistencies.append({
                    "type": "missing_field",
                    "field": field,
                    "present_in": present_count,
                    "total": total_count,
                    "percentage": (present_count / total_count) * 100,
                })

        # Find fields with type inconsistencies
        field_types = self.detect_field_types(samples)
        for field, types in field_types.items():
            if len(types) > 1:
                inconsistencies.append({
                    "type": "type_mismatch",
                    "field": field,
                    "observed_types": types,
                })

        return inconsistencies

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis results.

        Returns:
            Summary dictionary
        """
        return {
            "total_fields": len(self.analysis_results.get("field_map", [])),
            "patterns_found": len(self.analysis_results.get("patterns", [])),
            "inconsistencies_found": len(
                self.analysis_results.get("inconsistencies", [])
            ),
            "partition_key_recommendation": self.analysis_results.get(
                "partition_key_recommendation"
            ),
            "indexing_count": len(
                self.analysis_results.get("indexing_recommendations", [])
            ),
        }
