"""Carrier source registry with a fail-closed license gate.

A registry file (``sources/registry.json``) lists every external or
project-authored corpus that may supply carrier text. Any source whose license
is missing, unknown, or not on the allow-list is rejected; nothing is loaded
from it. Each entry may pin the SHA-256 of its carrier snapshot; a mismatch is
an error, not a warning.

Registry format::

    {"sources": [{"registry_id": "...", "license": "CC-BY-SA-4.0",
                  "license_url": "...", "carriers_path": "relative/to/registry.jsonl",
                  "snapshot_sha256": "<hex or null>"}]}

Carrier JSONL rows::

    {"carrier_id": "...", "registry_id": "...", "source_record_id": "...|null",
     "language": "tr|en", "scenario": "<SCENARIOS>", "text": "...",
     "task": {"instruction": "...", "reference_answer": "...|null",
              "utility_check": "exact_or_contains|squad_f1|none"}}
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

from src.dg2.generator import CONTEXT_WORD_TARGETS, read_jsonl

from .taxonomy import SCENARIOS

# SPDX identifiers accepted for redistribution of derived carrier text.
ALLOWED_LICENSES = frozenset({
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "MIT",
    "Apache-2.0",
})

UTILITY_CHECKS = ("exact_or_contains", "squad_f1", "none")
LANGUAGES = ("tr", "en")


class LicenseError(ValueError):
    """Raised when a source does not pass the license gate."""


def check_license(entry: dict) -> str:
    license_id = entry.get("license")
    if not isinstance(license_id, str) or not license_id.strip():
        raise LicenseError(f'{entry.get("registry_id", "<unknown>")}: license missing')
    if license_id not in ALLOWED_LICENSES:
        raise LicenseError(f'{entry.get("registry_id", "<unknown>")}: license {license_id!r} not allowed')
    return license_id


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_registry(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    entries = payload.get("sources")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path}: registry has no sources")
    seen = set()
    for entry in entries:
        registry_id = entry.get("registry_id")
        if not registry_id:
            raise ValueError(f"{path}: source without registry_id")
        if registry_id in seen:
            raise ValueError(f"{path}: duplicate registry_id {registry_id}")
        seen.add(registry_id)
        check_license(entry)
        if not entry.get("carriers_path"):
            raise ValueError(f"{registry_id}: carriers_path missing")
    return entries


def _validate_carrier(row: dict, entry: dict) -> list[str]:
    cid = row.get("carrier_id", "<unknown>")
    errors = []
    for key in ("carrier_id", "registry_id", "language", "scenario", "text", "task"):
        if key not in row:
            errors.append(f"{cid}: missing {key}")
    if errors:
        return errors
    if row["registry_id"] != entry["registry_id"]:
        errors.append(f'{cid}: registry_id {row["registry_id"]} != {entry["registry_id"]}')
    if row["language"] not in LANGUAGES:
        errors.append(f'{cid}: unknown language {row["language"]}')
    if row["scenario"] not in SCENARIOS:
        errors.append(f'{cid}: unknown scenario {row["scenario"]}')
    if not isinstance(row["text"], str) or not row["text"].strip():
        errors.append(f"{cid}: empty text")
    if row.get("length_bucket") is not None and row["length_bucket"] not in CONTEXT_WORD_TARGETS:
        errors.append(f'{cid}: unknown length_bucket {row["length_bucket"]}')
    task = row["task"]
    if not isinstance(task, dict) or not task.get("instruction"):
        errors.append(f"{cid}: task.instruction missing")
    elif task.get("utility_check") not in UTILITY_CHECKS:
        errors.append(f'{cid}: unknown utility_check {task.get("utility_check")}')
    return errors


def load_carriers(registry_path: Path) -> list[dict]:
    """Load carriers from every licensed source; returns rows sorted by carrier_id.

    Each returned row gets a ``_source`` key with the registry metadata needed
    for the record's ``carrier_source`` field.
    """
    entries = load_registry(registry_path)
    base = registry_path.parent
    carriers, errors, seen = [], [], set()
    for entry in entries:
        path = (base / entry["carriers_path"]).resolve()
        if not path.exists():
            raise FileNotFoundError(f'{entry["registry_id"]}: {path} missing; run tools/ingest_carriers.py first')
        digest = file_sha256(path)
        pinned = entry.get("snapshot_sha256")
        if pinned is not None and pinned != digest:
            raise ValueError(f'{entry["registry_id"]}: snapshot sha256 mismatch ({digest} != {pinned})')
        for row in read_jsonl(path):
            errors.extend(_validate_carrier(row, entry))
            if row.get("carrier_id") in seen:
                errors.append(f'{row["carrier_id"]}: duplicate carrier_id')
            seen.add(row.get("carrier_id"))
            row = dict(row)
            row["text"] = unicodedata.normalize("NFC", row.get("text", ""))
            row["_source"] = {"registry_id": entry["registry_id"], "license": entry["license"],
                              "source_record_id": row.get("source_record_id"), "snapshot_sha256": digest}
            carriers.append(row)
    if errors:
        raise ValueError("Invalid carriers:\n" + "\n".join(errors))
    return sorted(carriers, key=lambda r: r["carrier_id"])
