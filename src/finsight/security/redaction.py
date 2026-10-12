"""Sensitive data redaction for financial records, logs, and model explanations."""

import re
from typing import Any, Dict, List, Union

# Patterns for sensitive financial identifiers
PATTERNS = {
    "ACCOUNT_NUMBER": re.compile(r"\b\d{8,16}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "PHONE_BD": re.compile(r"(\+880|01)[3-9]\d{8}\b"),
    "CARD_NUMBER": re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
}


def redact_text(text: str) -> str:
    """Mask sensitive PII and account numbers from strings."""
    if not isinstance(text, str):
        return text

    redacted = text
    # Mask card numbers first
    redacted = PATTERNS["CARD_NUMBER"].sub("[REDACTED_CARD]", redacted)
    # Mask bank account numbers
    redacted = PATTERNS["ACCOUNT_NUMBER"].sub("[REDACTED_ACCOUNT]", redacted)
    # Mask emails
    redacted = PATTERNS["EMAIL"].sub("[REDACTED_EMAIL]", redacted)
    # Mask phones
    redacted = PATTERNS["PHONE_BD"].sub("[REDACTED_PHONE]", redacted)

    return redacted


def redact_data_structure(data: Union[Dict, List, Any]) -> Any:
    """Recursively mask sensitive identifiers from dictionaries or lists."""
    if isinstance(data, dict):
        return {
            k: ("[REDACTED]" if k.lower() in ("secret", "password", "api_key", "token") else redact_data_structure(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [redact_data_structure(item) for item in data]
    elif isinstance(data, str):
        return redact_text(data)
    return data
