from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from .generator import canonical_json, read_jsonl


LABELS = ("injection", "benign", "borderline")


def annotator_hash(annotator: str) -> str:
    return hashlib.sha256(annotator.encode("utf-8")).hexdigest()[:16]


def export_blind(dataset: Path, output: Path, annotator: str) -> int:
    rows = read_jsonl(dataset)
    output.parent.mkdir(parents=True, exist_ok=True)
    anon = annotator_hash(annotator)
    with output.open("w", encoding="utf-8", newline="\n") as fh:
        for row in sorted(rows, key=lambda r: r["record_id"]):
            assignment = {
                "assignment_id": hashlib.sha256(f'{anon}:{row["record_id"]}'.encode()).hexdigest()[:20],
                "annotator_id_hash": anon, "record_id": row["record_id"],
                "language": row["language"], "scenario": row["scenario"],
                "user_task": row["user_task"], "source": row["source"],
                "carrier_text": row["carrier_text"],
                "decision": {"label": None, "injection_spans": [], "rationale": None,
                             "confidence": None, "needs_adjudication": False},
            }
            fh.write(canonical_json(assignment) + "\n")
    return len(rows)


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    if not labels_a or len(labels_a) != len(labels_b):
        return 0.0
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / len(labels_a)
    count_a, count_b = Counter(labels_a), Counter(labels_b)
    expected = sum((count_a[x] / len(labels_a)) * (count_b[x] / len(labels_b)) for x in LABELS)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def merge_annotations(file_a: Path, file_b: Path, output_dir: Path) -> dict:
    a = {r["record_id"]: r for r in read_jsonl(file_a)}
    b = {r["record_id"]: r for r in read_jsonl(file_b)}
    common = sorted(set(a) & set(b))
    labels_a, labels_b, disagreements = [], [], []
    exact_span_matches = 0
    for record_id in common:
        da, db = a[record_id]["decision"], b[record_id]["decision"]
        la, lb = da.get("label"), db.get("label")
        if la not in LABELS or lb not in LABELS:
            raise ValueError(f"Missing/invalid decision label for {record_id}")
        labels_a.append(la); labels_b.append(lb)
        span_match = da.get("injection_spans", []) == db.get("injection_spans", [])
        exact_span_matches += span_match
        if la != lb or not span_match or da.get("needs_adjudication") or db.get("needs_adjudication"):
            disagreements.append({"record_id": record_id, "annotator_a": da, "annotator_b": db,
                                  "adjudication": {"label": None, "injection_spans": [], "rationale": None}})
    output_dir.mkdir(parents=True, exist_ok=True)
    queue = output_dir / "adjudication_queue.jsonl"
    queue.write_text("".join(canonical_json(r) + "\n" for r in disagreements), encoding="utf-8")
    summary = {
        "common_records": len(common), "label_agreement": sum(x == y for x, y in zip(labels_a, labels_b)) / len(common) if common else 0,
        "cohen_kappa": cohen_kappa(labels_a, labels_b),
        "span_exact_match": exact_span_matches / len(common) if common else 0,
        "adjudication_count": len(disagreements), "adjudication_queue": str(queue),
        "annotator_a_hash": next(iter(a.values())).get("annotator_id_hash") if a else None,
        "annotator_b_hash": next(iter(b.values())).get("annotator_id_hash") if b else None,
    }
    (output_dir / "agreement.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
