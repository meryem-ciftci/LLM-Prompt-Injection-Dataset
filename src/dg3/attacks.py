"""Attack component loading and taxonomy validation.

Components live in ``data/attack_components/*.jsonl``. One row::

    {"component_id": "...", "language": "tr|en", "goal": "<ATTACK_GOALS>",
     "techniques": ["<ATTACK_TECHNIQUES>", ...],
     "instruction": "... must contain witness.value verbatim ...",
     "witness": {"type": "<WITNESS_TYPES>", "value": "..."},
     "trigger_benign_text": "... trigger words, no redirection, no witness ...",
     "annotation_status": "<ANNOTATION_STATUSES>",
     "safety": {"fictional": true, "live_secret": false, "executable_payload": false}}

Components with status ``model_proposed`` load but are never assembled; the
automatic QC in ``qc.py`` promotes valid candidates to ``auto_qc_passed``
(see ``ASSEMBLABLE_STATUSES``). No human review is required. The remaining
human statuses stay accepted only for externally supplied, already-reviewed
components; the generator itself never claims them.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

from src.dg2.generator import read_jsonl

from .taxonomy import ANNOTATION_STATUSES, ATTACK_GOALS, ATTACK_TECHNIQUES, WITNESS_TYPES

ASSEMBLABLE_STATUSES = frozenset({"auto_qc_passed", "single_annotated", "adjudicated", "gold_calibration"})
REQUIRED = ("component_id", "language", "goal", "techniques", "instruction", "witness",
            "trigger_benign_text", "annotation_status", "safety")


def validate_component(row: dict) -> list[str]:
    cid = row.get("component_id", "<unknown>")
    missing = [k for k in REQUIRED if k not in row]
    if missing:
        return [f"{cid}: missing {missing}"]
    errors = []
    if row["language"] not in ("tr", "en"):
        errors.append(f'{cid}: unknown language {row["language"]}')
    if row["goal"] not in ATTACK_GOALS:
        errors.append(f'{cid}: unknown goal {row["goal"]}')
    techniques = row["techniques"]
    if not isinstance(techniques, list) or not techniques:
        errors.append(f"{cid}: techniques must be a non-empty list")
    else:
        unknown = [t for t in techniques if t not in ATTACK_TECHNIQUES]
        if unknown:
            errors.append(f"{cid}: unknown techniques {unknown}")
        if len(set(techniques)) != len(techniques):
            errors.append(f"{cid}: duplicate techniques")
    if row["annotation_status"] not in ANNOTATION_STATUSES:
        errors.append(f'{cid}: unknown annotation_status {row["annotation_status"]}')
    witness = row["witness"]
    if not isinstance(witness, dict) or witness.get("type") not in WITNESS_TYPES:
        errors.append(f"{cid}: invalid witness type")
    else:
        value = witness.get("value", "")
        if not isinstance(value, str) or len(value) < 4:
            errors.append(f"{cid}: witness value shorter than 4 characters")
        elif value not in row["instruction"]:
            errors.append(f"{cid}: witness value not present in instruction")
        elif value.casefold() in row["trigger_benign_text"].casefold():
            errors.append(f"{cid}: witness value leaks into trigger_benign_text")
    if not row["instruction"].strip() or not row["trigger_benign_text"].strip():
        errors.append(f"{cid}: empty instruction or trigger_benign_text")
    safety = row["safety"]
    if safety.get("live_secret") is not False or safety.get("executable_payload") is not False:
        errors.append(f"{cid}: safety flags must declare no live secret and no executable payload")
    return errors


def load_components(directory: Path) -> list[dict]:
    """Load and validate every ``*.jsonl`` in ``directory``; sorted by component_id."""
    files = sorted(directory.glob("*.jsonl"))
    if not files:
        raise ValueError(f"{directory}: no attack component files")
    rows, errors, seen = [], [], set()
    for path in files:
        for row in read_jsonl(path):
            errors.extend(validate_component(row))
            cid = row.get("component_id")
            if cid in seen:
                errors.append(f"{cid}: duplicate component_id")
            seen.add(cid)
            row = dict(row)
            for key in ("instruction", "trigger_benign_text"):
                if isinstance(row.get(key), str):
                    row[key] = unicodedata.normalize("NFC", row[key])
            rows.append(row)
    if errors:
        raise ValueError("Invalid attack components:\n" + "\n".join(errors))
    return sorted(rows, key=lambda r: r["component_id"])


def assemblable(components: list[dict]) -> list[dict]:
    return [c for c in components if c["annotation_status"] in ASSEMBLABLE_STATUSES]
