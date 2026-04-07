"""Structured logging configuration with sensitive data masking."""

import logging
import re
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive information in log records."""

    # Patterns for sensitive data
    PATTERNS = [
        (r"ANTHROPIC_API_KEY[=:][\s]*[^\s]+", "ANTHROPIC_API_KEY=***"),
        (r"api[_-]?key[=:][\s]*[^\s]+", "api_key=***"),
        (r"sk-ant-[^\s]+", "sk-ant-***"),
        (r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "SSN-***"),
        (r"\b[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b", "CARD-***"),
        (r"Bearer\s+[^\s]+", "Bearer ***"),
        (r"connection[_-]?string[=:][\s]*[^\s;]+", "connection_string=***"),
        (r"mongodb://[^/]+", "mongodb://***"),
        (r"password[=:][\s]*[^\s]+", "password=***"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log message."""
        record.msg = self._mask_sensitive_data(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._mask_sensitive_data(str(v))
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._mask_sensitive_data(str(arg)) for arg in record.args
                )
        return True

    @staticmethod
    def _mask_sensitive_data(text: str) -> str:
        """Apply all masking patterns to text."""
        for pattern, replacement in SensitiveDataFilter.PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    include_sensitive: bool = False,
) -> logging.Logger:
    """Configure logging with optional file output and sensitive data masking.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        include_sensitive: If False, masks sensitive data in logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("az-migrate")
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))

    # Detailed format with timestamps
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    # Add sensitive data filter if enabled
    if not include_sensitive:
        filter_obj = SensitiveDataFilter()
        console_handler.addFilter(filter_obj)

    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)

        if not include_sensitive:
            file_handler.addFilter(SensitiveDataFilter())

        logger.addHandler(file_handler)

    return logger


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Get or create a logger with the specified name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        setup_logging(level=level)
    return logger
