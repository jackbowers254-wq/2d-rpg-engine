"""
engine.data.validation
=====================
A tiny declarative validator that turns malformed data into precise, friendly
errors instead of crashes. No external dependency (deliberately not jsonschema).

A schema is a plain dict:

    {
      "type": "object",
      "fields": {
        "name": {"type": "str", "required": True},
        "type": {"type": "str", "enum": ["consumable", "equipment"]},
        "effects": {"type": "dict", "values": {"type": "int"}},
        "icon_color": {"type": "list", "items": {"type": "int"}},
      },
      "allow_unknown": False,      # report unknown keys (with suggestions)
    }

Supported ``type`` values: str, int, float, number (int|float), bool, list,
dict, object, any. Containers recurse via ``fields`` / ``items`` / ``values``.

``validate`` collects every problem (so one run reports all of them);
``validate_or_raise`` raises a single :class:`DataError` whose message lists them
under the source filename.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List

from engine.utils.logger import get_logger

log = get_logger("data")


class DataError(Exception):
    """Raised when a content file fails validation. Message is human-readable."""


_PY_TYPES = {
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "object": dict,
}


def _typename(v: Any) -> str:
    return type(v).__name__


def _here(path: str) -> str:
    return path or "<root>"


def _check_type(value: Any, t: str, path: str, errors: List[str]) -> bool:
    if t in ("int", "float", "number"):
        # bool is a subclass of int in Python; reject it for numeric fields.
        if isinstance(value, bool):
            errors.append(f"{_here(path)}: expected {t}, got bool")
            return False
        ok = isinstance(value, (int, float)) if t == "number" else \
            isinstance(value, int) if t == "int" else isinstance(value, (int, float))
        if not ok:
            errors.append(f"{_here(path)}: expected {t}, got {_typename(value)}")
        return ok
    py = _PY_TYPES.get(t)
    if py is None:  # "any" or unknown type name -> accept
        return True
    if not isinstance(value, py):
        errors.append(f"{_here(path)}: expected {t}, got {_typename(value)}")
        return False
    return True


def validate(data: Any, schema: Dict, path: str = "", errors: List[str] | None = None) -> List[str]:
    """Validate ``data`` against ``schema``; return a list of error strings."""
    if errors is None:
        errors = []

    t = schema.get("type", "any")
    # Allow explicit null for non-required nullable fields.
    if data is None and schema.get("nullable"):
        return errors
    if t != "any" and not _check_type(data, t, path, errors):
        return errors  # type wrong -> don't recurse into it

    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{_here(path)}: must be one of {schema['enum']}, got {data!r}")

    if t in ("object", "dict") and isinstance(data, dict):
        fields = schema.get("fields")
        if fields is not None:
            for key, fschema in fields.items():
                child = f"{path}.{key}" if path else key
                if key not in data:
                    if fschema.get("required"):
                        errors.append(f"{child}: required field is missing")
                    continue
                validate(data[key], fschema, child, errors)
            if not schema.get("allow_unknown", True):
                valid = set(fields)
                for key in data:
                    if key in valid or str(key).startswith("_"):
                        continue
                    suggestion = difflib.get_close_matches(str(key), valid, n=1)
                    hint = f" (did you mean '{suggestion[0]}'?)" if suggestion else ""
                    errors.append(f"{_here(path)}: unknown field '{key}'{hint}")
        # free-form dict with a value schema
        vschema = schema.get("values")
        if vschema is not None:
            for key, value in data.items():
                if str(key).startswith("_"):
                    continue
                validate(value, vschema, f"{path}.{key}" if path else str(key), errors)

    if t == "list" and isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            validate(item, schema["items"], f"{path}[{i}]", errors)

    return errors


def validate_or_raise(data: Any, schema: Dict, source: str) -> None:
    """Validate and raise a single :class:`DataError` listing all problems."""
    errors = validate(data, schema)
    if errors:
        bullet = "\n  - ".join(errors)
        raise DataError(f"Invalid data in {source}:\n  - {bullet}")


def closest(name: str, options) -> str:
    """Return a ' (did you mean X?)' hint or '' for a misspelled name."""
    match = difflib.get_close_matches(str(name), list(options), n=1)
    return f" (did you mean '{match[0]}'?)" if match else ""
