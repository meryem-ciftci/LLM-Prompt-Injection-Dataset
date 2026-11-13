from __future__ import annotations

import hashlib
import json
import random
import unicodedata
from collections import Counter
from pathlib import Path


def canonical_json(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(prefix: str, *parts: object) -> str:
    raw = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(raw).hexdigest()[:16].upper()}"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def split_for(family_id: str, seed: int, ratios: dict[str, float]) -> str:
    total = sum(ratios.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError("split_ratios must sum to 1.0")
    value = int(hashlib.sha256(f"{seed}:{family_id}".encode()).hexdigest()[:12], 16) / float(16**12)
    acc = 0.0
    for name in ("train", "validation", "test"):
        acc += ratios[name]
        if value < acc:
            return name
    return "test"


WRAPPERS = (
    ("original", "{text}"),
    ("document_block", "[BELGE BAŞLANGICI / DOCUMENT START]\n{text}\n[BELGE SONU / DOCUMENT END]"),
    ("quoted_block", "> {text}"),
    ("metadata_block", "content_type: external_text\ncontent:\n{text}"),
)


def transform(seed_record: dict, variant: int) -> tuple[str, list[dict], str]:
    name, template = WRAPPERS[variant % len(WRAPPERS)]
    source_text = unicodedata.normalize("NFC", seed_record["carrier_text"])
    carrier = template.format(text=source_text)
    spans = []
    for span in seed_record["injection_spans"]:
        span_text = unicodedata.normalize("NFC", span["text"])
        start = carrier.index(span_text)
        spans.append({"start": start, "end": start + len(span_text),
                      "span_type": "injected_instruction", "text": span_text})
    return carrier, spans, name


def make_record(seed_record: dict, config: dict, variant: int, *, trusted_twin: bool) -> dict:
    carrier, spans, transformation = transform(seed_record, variant)
    family_id = stable_id("FAM", seed_record["record_id"], variant)
    pair_id = stable_id("PAIR", family_id)
    label = "benign" if trusted_twin else "injection"
    source = ({"type": "authorized_user_message", "role": "authorized_user", "trust_level": "trusted_instruction"}
              if trusted_twin else seed_record["source"])
    record_id = stable_id("DG2", family_id, label)
    record = {
        "record_id": record_id,
        "schema_version": "2.0.0",
        "generator_version": "2.0.0",
        "generation_seed": config["seed"],
        "family_id": family_id,
        "pair_id": pair_id,
        "parent_id": seed_record["record_id"],
        "language": seed_record["language"],
        "scenario": seed_record["scenario"],
        "user_task": seed_record["user_task"],
        "source": source,
        "carrier_text": carrier,
        "label": label,
        "injection_spans": [] if trusted_twin else spans,
        "trust_boundary_decision": ("authorized_instruction_in_scope" if trusted_twin else "instruction_from_untrusted_source_crosses_boundary"),
        "decision_rationale": ("The same text is delivered through the authorized instruction channel."
                               if trusted_twin else "External content attempts to direct model behavior across the trust boundary."),
        "annotation_status": "generated_candidate",
        "transformation": {"type": transformation, "variant_index": variant},
        "split": split_for(family_id, config["seed"], config["split_ratios"]),
        "provenance": {
            "origin": "derived_from_human_verified_calibration",
            "source_record_id": seed_record["record_id"],
            "source_pack": "Calibration_Records_v1",
            "license_intent": seed_record["provenance"]["license_intent"],
        },
        "safety": seed_record["safety"],
    }
    record["content_sha256"] = hashlib.sha256(carrier.encode("utf-8")).hexdigest()
    return record


def make_hard_benign(seed_record: dict, config: dict, variant: int) -> dict:
    carrier, _, transformation = transform(seed_record, variant)
    family_id = stable_id("FAM", seed_record["record_id"], "hard-benign", variant)
    record = {
        "record_id": stable_id("DG2", family_id, "benign"),
        "schema_version": "2.0.0", "generator_version": "2.0.0",
        "generation_seed": config["seed"], "family_id": family_id, "pair_id": None,
        "parent_id": seed_record["record_id"], "language": seed_record["language"],
        "scenario": seed_record["scenario"], "user_task": seed_record["user_task"],
        "source": seed_record["source"], "carrier_text": carrier, "label": "benign",
        "injection_spans": [], "trust_boundary_decision": "no_unauthorized_instruction_crossing",
        "decision_rationale": seed_record["decision_rationale"],
        "annotation_status": "generated_candidate",
        "transformation": {"type": transformation, "variant_index": variant},
        "split": split_for(family_id, config["seed"], config["split_ratios"]),
        "provenance": {"origin": "derived_from_human_verified_calibration",
                       "source_record_id": seed_record["record_id"],
                       "source_pack": "Calibration_Records_v1",
                       "license_intent": seed_record["provenance"]["license_intent"]},
        "safety": seed_record["safety"],
    }
    record["content_sha256"] = hashlib.sha256(carrier.encode("utf-8")).hexdigest()
    return record


def generate(config: dict, calibration_path: Path) -> list[dict]:
    seeds = read_jsonl(calibration_path)
    attacks = sorted((r for r in seeds if r["label"] == "injection"), key=lambda r: r["record_id"])
    benign = sorted((r for r in seeds if r["label"] == "benign"), key=lambda r: r["record_id"])
    if not attacks or not benign:
        raise ValueError("Calibration pack must contain injection and benign seeds")
    rng = random.Random(config["seed"])
    rng.shuffle(attacks); rng.shuffle(benign)
    records = []
    for i in range(config["pair_families"]):
        seed = attacks[i % len(attacks)]
        variant = i // len(attacks)
        records.append(make_record(seed, config, variant, trusted_twin=False))
        records.append(make_record(seed, config, variant, trusted_twin=True))
    for i in range(config["hard_benign"]):
        seed = benign[i % len(benign)]
        variant = i // len(benign)
        records.append(make_hard_benign(seed, config, variant))
    records.sort(key=lambda r: r["record_id"])
    return records


def validate(records: list[dict]) -> list[str]:
    errors = []
    ids = [r.get("record_id") for r in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate record_id")
    family_splits: dict[str, set[str]] = {}
    for r in records:
        required = ("record_id", "family_id", "language", "scenario", "user_task", "source",
                    "carrier_text", "label", "injection_spans", "split", "provenance", "safety")
        missing = [x for x in required if x not in r]
        if missing:
            errors.append(f'{r.get("record_id", "<unknown>")}: missing {missing}')
            continue
        family_splits.setdefault(r["family_id"], set()).add(r["split"])
        if r["label"] == "injection" and not r["injection_spans"]:
            errors.append(f'{r["record_id"]}: injection has no span')
        if r["label"] == "benign" and r["injection_spans"]:
            errors.append(f'{r["record_id"]}: benign has injection spans')
        for span in r["injection_spans"]:
            actual = r["carrier_text"][span["start"]:span["end"]]
            if actual != span["text"]:
                errors.append(f'{r["record_id"]}: span round-trip failed')
        digest = hashlib.sha256(r["carrier_text"].encode("utf-8")).hexdigest()
        if r.get("content_sha256") != digest:
            errors.append(f'{r["record_id"]}: content hash mismatch')
    for family, splits in family_splits.items():
        if len(splits) != 1:
            errors.append(f"{family}: family split leakage {sorted(splits)}")
    return errors


def write_release(records: list[dict], output: Path, config: dict) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_json(r) + "\n" for r in records)
    payload_bytes = payload.encode("utf-8")
    output.write_bytes(payload_bytes)
    manifest = {
        "schema_version": "2.0.0", "generator_version": "2.0.0",
        "seed": config["seed"], "record_count": len(records),
        "labels": dict(Counter(r["label"] for r in records)),
        "languages": dict(Counter(r["language"] for r in records)),
        "splits": dict(Counter(r["split"] for r in records)),
        "sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "canonical_file": output.name,
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest

