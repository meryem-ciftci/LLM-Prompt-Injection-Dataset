"""Minimal JSON Schema checker for the keyword subset used by the v3 schema.

Supported: type, enum, const, required, properties, additionalProperties
(boolean), items, minItems, uniqueItems, minLength, minimum, pattern.
Unsupported keywords raise, so a schema change cannot silently weaken checks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_IGNORED = {"$schema", "$id", "title", "description"}
_SUPPORTED = {"type", "enum", "const", "required", "properties", "additionalProperties",
              "items", "minItems", "uniqueItems", "minLength", "minimum", "pattern"} | _IGNORED
_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(value, schema: dict, path: str = "$") -> list[str]:
    unknown = set(schema) - _SUPPORTED
    if unknown:
        raise ValueError(f"{path}: unsupported schema keywords {sorted(unknown)}")
    errors: list[str] = []
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](value) for t in types):
            return [f"{path}: expected {types}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(seen) != len(set(seen)):
                errors.append(f"{path}: items not unique")
        if "items" in schema:
            for i, item in enumerate(value):
                errors.extend(check(item, schema["items"], f"{path}[{i}]"))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required {key}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(props))
            if extra:
                errors.append(f"{path}: unexpected properties {extra}")
        for key, sub in props.items():
            if key in value:
                errors.extend(check(value[key], sub, f"{path}.{key}"))
    return errors
