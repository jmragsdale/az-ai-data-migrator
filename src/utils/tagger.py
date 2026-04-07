"""Resource tagging for Azure resources with standard metadata."""

from datetime import datetime
from typing import Any, Dict, Optional


class ResourceTagger:
    """Generate and apply standardized Azure resource tags."""

    @staticmethod
    def generate_default_tags(
        migration_source: str = "unknown",
        data_classification: str = "internal",
        cost_center: Optional[str] = None,
        custom_tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Generate standard tag set for resources.

        Args:
            migration_source: Source system name (mongodb, filesystem, etc.)
            data_classification: Data sensitivity level (public, internal, confidential, restricted)
            cost_center: Cost center code for chargeback
            custom_tags: Additional custom tags to merge

        Returns:
            Dictionary of tags suitable for Azure resources
        """
        tags = {
            "migration-source": migration_source,
            "migration-date": datetime.now().isoformat(),
            "migrated-by": "az-ai-data-migrator",
            "data-classification": data_classification,
            "environment": "production",
        }

        if cost_center:
            tags["cost-center"] = cost_center

        # Merge custom tags
        if custom_tags:
            tags.update(custom_tags)

        return tags

    @staticmethod
    def format_tags_for_cosmos(
        tags: Dict[str, str],
    ) -> Dict[str, Any]:
        """Format tags dictionary for Cosmos DB resource tagging.

        Args:
            tags: Tags dictionary

        Returns:
            Formatted tags for Cosmos DB
        """
        # Cosmos DB tags are just key-value strings
        return {k: str(v) for k, v in tags.items()}

    @staticmethod
    def format_tags_for_blob(
        tags: Dict[str, str],
    ) -> Dict[str, str]:
        """Format tags dictionary for Blob Storage resource tagging.

        Args:
            tags: Tags dictionary

        Returns:
            Formatted tags for Blob Storage
        """
        # Azure Storage tags are key-value strings
        return {k: str(v) for k, v in tags.items()}

    @staticmethod
    def add_blob_metadata_tags(
        blob_tags: Dict[str, str],
        source_file: Optional[str] = None,
        content_type: Optional[str] = None,
        record_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Add blob-specific metadata tags for blob items.

        Args:
            blob_tags: Existing blob tags
            source_file: Source file name
            content_type: MIME type
            record_id: Source record identifier

        Returns:
            Updated tags dictionary
        """
        if source_file:
            blob_tags["source-file"] = source_file
        if content_type:
            blob_tags["content-type"] = content_type
        if record_id:
            blob_tags["record-id"] = record_id

        return blob_tags

    @staticmethod
    def validate_tag_name(tag_name: str) -> bool:
        """Validate Azure tag name format.

        Azure tag names have restrictions:
        - Max 512 characters
        - Alphanumeric, spaces, hyphens, underscores, periods allowed
        - Cannot start/end with special characters

        Args:
            tag_name: Tag name to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        if not tag_name or len(tag_name) > 512:
            return False

        # Azure allows: alphanumeric, space, hyphen, underscore, period
        pattern = r"^[a-zA-Z0-9\s\-_\.]+$"
        return bool(re.match(pattern, tag_name))

    @staticmethod
    def validate_tag_value(tag_value: str) -> bool:
        """Validate Azure tag value format.

        Azure tag values have restrictions:
        - Max 256 characters
        - Most characters allowed except < > % & \

        Args:
            tag_value: Tag value to validate

        Returns:
            True if valid, False otherwise
        """
        if not tag_value or len(tag_value) > 256:
            return False

        forbidden_chars = ["<", ">", "%", "&", "\\"]
        return not any(char in tag_value for char in forbidden_chars)

    @staticmethod
    def sanitize_tags(tags: Dict[str, str]) -> Dict[str, str]:
        """Sanitize tags to comply with Azure restrictions.

        Args:
            tags: Input tags dictionary

        Returns:
            Sanitized tags dictionary
        """
        sanitized = {}

        for key, value in tags.items():
            # Truncate if too long
            safe_key = key[:512] if key else "tag"
            safe_value = str(value)[:256] if value else ""

            # Remove forbidden characters from value
            for char in ["<", ">", "%", "&", "\\"]:
                safe_value = safe_value.replace(char, "-")

            sanitized[safe_key] = safe_value

        return sanitized
