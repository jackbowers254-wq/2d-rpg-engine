"""
Data-loading infrastructure: schema validation with human-readable errors.

A typo in a JSON content file should tell you *exactly what and where* — not
raise a cryptic ``TypeError`` deep in a constructor. The lightweight validator
here (no external dependency) reports issues as ``file -> field path: message``
and suggests close matches for misspelled keys.
"""

from engine.data.validation import (
    DataError,
    validate,
    validate_or_raise,
)

__all__ = ["DataError", "validate", "validate_or_raise"]
