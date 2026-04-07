"""JSON and CSV connector for loading and normalizing data."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from src.utils.logger import get_logger

logger = get_logger(__name__)


class JsonCsvConnector:
    """Load and normalize JSON and CSV files."""

    def __init__(self):
        """Initialize JSON/CSV connector."""
        pass

    @staticmethod
    def load_json_file(file_path: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Load JSON file (single document or array).

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON content (list or dict)

        Raises:
            FileNotFoundError: If file not found
            json.JSONDecodeError: If JSON is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Loaded JSON file: {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            raise

    @staticmethod
    def load_csv_file(
        file_path: str, delimiter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Load CSV file with auto-delimiter detection.

        Args:
            file_path: Path to CSV file
            delimiter: Optional delimiter (auto-detected if not provided)

        Returns:
            List of dictionaries (one per row)

        Raises:
            FileNotFoundError: If file not found
            ValueError: If CSV parsing fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                # Auto-detect delimiter if not provided
                if delimiter is None:
                    sample = f.read(1024)
                    f.seek(0)
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    logger.debug(f"Auto-detected CSV delimiter: {repr(delimiter)}")

                reader = csv.DictReader(f, delimiter=delimiter)
                records = list(reader)

            logger.debug(f"Loaded {len(records)} records from CSV: {file_path}")
            return records

        except (csv.Error, UnicodeDecodeError) as e:
            logger.error(f"Error parsing CSV {file_path}: {e}")
            raise ValueError(f"Failed to parse CSV: {e}")

    @staticmethod
    def normalize_json_to_records(
        data: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Normalize JSON data to list of record dictionaries.

        Args:
            data: Parsed JSON data (list or single dict)

        Returns:
            Normalized list of records
        """
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Check if it's wrapped in a key (e.g., {"data": [...]})
            if len(data) == 1:
                only_value = list(data.values())[0]
                if isinstance(only_value, list):
                    return only_value

            # Single record wrapped
            return [data]
        else:
            raise ValueError(f"Cannot normalize data type: {type(data)}")

    @staticmethod
    def flatten_nested_json(
        record: Dict[str, Any], separator: str = "_"
    ) -> Dict[str, Any]:
        """Flatten nested JSON structure into flat dictionary.

        Args:
            record: Potentially nested dictionary
            separator: Separator for flattened keys

        Returns:
            Flattened dictionary
        """
        flattened = {}

        def flatten(obj: Any, prefix: str = "") -> None:
            """Recursively flatten nested objects."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}{separator}{key}" if prefix else key
                    flatten(value, new_key)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    new_key = f"{prefix}[{idx}]"
                    flatten(item, new_key)
            else:
                flattened[prefix] = obj

        flatten(record)
        return flattened

    @staticmethod
    def unflatten_json(
        flattened: Dict[str, Any], separator: str = "_"
    ) -> Dict[str, Any]:
        """Convert flattened dictionary back to nested structure.

        Args:
            flattened: Flattened dictionary
            separator: Separator used for keys

        Returns:
            Nested dictionary
        """
        result: Dict[str, Any] = {}

        for key, value in flattened.items():
            parts = key.split(separator)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result

    @staticmethod
    def normalize_csv_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize CSV records (convert types, handle missing values).

        Args:
            records: List of CSV records

        Returns:
            Normalized records
        """
        normalized = []

        for record in records:
            normalized_record = {}

            for key, value in record.items():
                # Clean up key names
                clean_key = key.strip() if isinstance(key, str) else key

                # Try to convert values
                if value is None or value == "":
                    normalized_record[clean_key] = None
                elif value.lower() in ("true", "yes"):
                    normalized_record[clean_key] = True
                elif value.lower() in ("false", "no"):
                    normalized_record[clean_key] = False
                else:
                    # Try numeric conversion
                    try:
                        if "." in str(value):
                            normalized_record[clean_key] = float(value)
                        else:
                            normalized_record[clean_key] = int(value)
                    except (ValueError, TypeError):
                        normalized_record[clean_key] = str(value)

            normalized.append(normalized_record)

        return normalized

    @staticmethod
    def stream_json_records(
        file_path: str, batch_size: int = 100
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Stream JSON records in batches.

        Args:
            file_path: Path to JSON file
            batch_size: Number of records per batch

        Yields:
            Batches of records
        """
        data = JsonCsvConnector.load_json_file(file_path)
        records = JsonCsvConnector.normalize_json_to_records(data)

        batch = []
        for record in records:
            batch.append(record)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    @staticmethod
    def stream_csv_records(
        file_path: str, batch_size: int = 100
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Stream CSV records in batches.

        Args:
            file_path: Path to CSV file
            batch_size: Number of records per batch

        Yields:
            Batches of records
        """
        records = JsonCsvConnector.load_csv_file(file_path)
        normalized = JsonCsvConnector.normalize_csv_records(records)

        batch = []
        for record in normalized:
            batch.append(record)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    @staticmethod
    def detect_source_type(file_path: str) -> str:
        """Auto-detect source file type.

        Args:
            file_path: Path to file

        Returns:
            Source type: 'json' or 'csv'

        Raises:
            ValueError: If file type cannot be determined
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".json":
            return "json"
        elif suffix in (".csv", ".tsv"):
            return "csv"
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
