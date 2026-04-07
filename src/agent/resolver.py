"""Conflict resolution using Claude API for handling schema inconsistencies."""

import json
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConflictResolver:
    """Resolve data inconsistencies using Claude API."""

    def __init__(self, anthropic_client: Optional[Anthropic] = None):
        """Initialize conflict resolver.

        Args:
            anthropic_client: Anthropic client for API calls
        """
        self.client = anthropic_client
        self.resolution_strategies: Dict[str, Any] = {}

    def resolve_inconsistencies(
        self,
        inconsistencies: List[Dict[str, Any]],
        anthropic_api_key: str,
    ) -> Dict[str, Any]:
        """Propose resolution strategies for detected inconsistencies.

        Args:
            inconsistencies: List of inconsistencies from analyzer
            anthropic_api_key: Anthropic API key

        Returns:
            Resolution plan with recommended strategies
        """
        if not self.client:
            self.client = Anthropic(api_key=anthropic_api_key)

        # Prepare input
        inconsistencies_json = json.dumps(inconsistencies[:10], indent=2)

        system_prompt = """You are a data quality expert specializing in schema reconciliation.
        Analyze the provided data inconsistencies and propose remediation strategies.

        For each inconsistency, recommend one of:
        1. coerce: Convert values to a consistent type
        2. split: Create separate fields for different data types
        3. nullable: Allow NULL values for missing fields
        4. skip: Exclude problematic fields from migration
        5. custom_transform: Apply custom transformation logic

        Provide structured resolution plan in JSON format."""

        user_message = f"""Propose resolution strategies for these data inconsistencies:

        {inconsistencies_json}

        For each inconsistency, provide:
        - inconsistency_id: Field name or type identifier
        - recommended_strategy: One of the five strategies
        - rationale: Why this strategy is recommended
        - implementation_steps: How to implement the resolution
        - risk_level: high, medium, or low"""

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
                resolution_data = json.loads(response_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    resolution_data = json.loads(json_match.group())
                else:
                    resolution_data = {"raw_response": response_text}

            self.resolution_strategies = {
                "inconsistencies_count": len(inconsistencies),
                "resolutions": resolution_data.get("resolutions", []),
                "summary": resolution_data.get("summary", {}),
                "tokens_used": message.usage.input_tokens
                + message.usage.output_tokens,
            }

            logger.info(
                f"Generated {len(self.resolution_strategies['resolutions'])} resolution strategies"
            )
            return self.resolution_strategies

        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            raise

    def apply_coercion(
        self, value: Any, target_type: str
    ) -> Any:
        """Apply type coercion to a value.

        Args:
            value: Value to coerce
            target_type: Target type (string, integer, number, boolean)

        Returns:
            Coerced value or None if coercion fails
        """
        if value is None:
            return None

        try:
            if target_type == "string":
                return str(value)
            elif target_type == "integer":
                return int(float(value))
            elif target_type == "number":
                return float(value)
            elif target_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "yes", "1")
                return bool(value)
            else:
                return value
        except (ValueError, TypeError):
            logger.warning(
                f"Failed to coerce {value} to {target_type}"
            )
            return None

    def split_field(
        self, field_name: str, value: Any
    ) -> Dict[str, Any]:
        """Split a field with multiple types into separate fields.

        Args:
            field_name: Name of field to split
            value: Value that might need splitting

        Returns:
            Dictionary with split fields
        """
        result = {}

        if isinstance(value, dict):
            for key, val in value.items():
                result[f"{field_name}_{key}"] = val
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                result[f"{field_name}_{idx}"] = item
        else:
            result[field_name] = value

        return result

    def get_resolution_summary(self) -> Dict[str, Any]:
        """Get summary of resolution strategies.

        Returns:
            Summary of resolutions
        """
        resolutions = self.resolution_strategies.get("resolutions", [])

        summary = {
            "total_resolutions": len(resolutions),
            "by_strategy": {},
            "by_risk_level": {
                "high": 0,
                "medium": 0,
                "low": 0,
            },
        }

        for resolution in resolutions:
            strategy = resolution.get("recommended_strategy", "unknown")
            risk = resolution.get("risk_level", "unknown")

            summary["by_strategy"][strategy] = (
                summary["by_strategy"].get(strategy, 0) + 1
            )
            if risk in summary["by_risk_level"]:
                summary["by_risk_level"][risk] += 1

        return summary
