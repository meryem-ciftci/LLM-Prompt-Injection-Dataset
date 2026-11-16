"""Automatic label agreement between independent local models and construction labels.

This replaces the human double-annotation step: two different local models label every
record blind (tools/local/prelabel.py), and we report

* Cohen's kappa between the two models (inter-model agreement);
* each model's kappa and per-family-role agreement against the construction label
  (the label implied by how the record was assembled: injected_untrusted -> injection,
  everything else -> benign);
* character IoU between a model's suggested span and the constructed injection span.

All numbers are computed from the files given; nothing here is a human judgement and the
report says so. Model labels never overwrite construction labels.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

from src.dg2.generator import read_jsonl

LABEL_SPACE = ("injection", "benign", "borderline")
REPORT_SCOPE = "automatic_model_agreement_not_human_annotation"


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's kappa over the labels that occur; None when undefined (no items)."""
    if not a or len(a) != len(b):
        return None
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected >= 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1 - expected)


def span_iou(pred: dict | None, constructed_spans: list[dict]) -> float:
    if pred is None or not constructed_spans:
        return 0.0
    g = constructed_spans[0]
    inter = max(0, min(pred["end"], g["end"]) - max(pred["start"], g["start"]))
    union = max(pred["end"], g["end"]) - min(pred["start"], g["start"])
    return inter / union if union > 0 else 0.0


def _labels(path: Path) -> tuple[dict[str, dict], str]:
    rows = read_jsonl(path)
    models = {r.get("model") for r in rows}
    if len(models) != 1:
        raise ValueError(f"{path}: expected labels from exactly one model, got {sorted(map(str, models))}")
    return {r["record_id"]: r for r in rows}, models.pop()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _vs_construction(records: list[dict], labels: dict[str, dict]) -> dict:
    pairs, by_role, ious = [], {}, []
    for r in records:
        lab = labels.get(r["record_id"], {}).get("suggested_label")
        if lab not in LABEL_SPACE:
            continue
        pairs.append((r["label"], lab))
        stats = by_role.setdefault(r["family_role"], Counter())
        stats["n"] += 1
        stats["agree"] += lab == r["label"]
        stats[f"predicted_{lab}"] += 1
        if r["family_role"] == "injected_untrusted":
            ious.append(span_iou(labels[r["record_id"]].get("suggested_span"), r["injection_spans"]))
    return {
        "n_labelled": len(pairs),
        "cohen_kappa": cohen_kappa([p[0] for p in pairs], [p[1] for p in pairs]),
        "agreement": (sum(x == y for x, y in pairs) / len(pairs)) if pairs else None,
        "by_family_role": {role: {"n": s["n"], "agreement": s["agree"] / s["n"],
                                  "predicted": {k[10:]: v for k, v in sorted(s.items()) if k.startswith("predicted_")}}
                           for role, s in sorted(by_role.items())},
        "injection_span_char_iou_mean": (sum(ious) / len(ious)) if ious else None,
        "injection_span_n": len(ious),
    }


def agreement_report(dataset: Path, labels_a: Path, labels_b: Path) -> dict:
    records = sorted(read_jsonl(dataset), key=lambda r: r["record_id"])
    a, model_a = _labels(labels_a)
    b, model_b = _labels(labels_b)
    if model_a == model_b:
        raise ValueError("agreement needs two different models")
    ids = [r["record_id"] for r in records]
    both = [i for i in ids if a.get(i, {}).get("suggested_label") in LABEL_SPACE
            and b.get(i, {}).get("suggested_label") in LABEL_SPACE]
    la = [a[i]["suggested_label"] for i in both]
    lb = [b[i]["suggested_label"] for i in both]
    return {
        "scope": REPORT_SCOPE,
        "dataset": dataset.name, "dataset_sha256": _sha_file(dataset), "records": len(records),
        "models": {"a": model_a, "b": model_b},
        "label_files_sha256": {"a": _sha_file(labels_a), "b": _sha_file(labels_b)},
        "coverage": {"a": sum(1 for i in ids if a.get(i, {}).get("suggested_label") in LABEL_SPACE),
                     "b": sum(1 for i in ids if b.get(i, {}).get("suggested_label") in LABEL_SPACE),
                     "both": len(both)},
        "inter_model": {"n": len(both), "cohen_kappa": cohen_kappa(la, lb),
                        "agreement": (sum(x == y for x, y in zip(la, lb)) / len(both)) if both else None,
                        "confusion": {f"{x}|{y}": n for (x, y), n in sorted(Counter(zip(la, lb)).items())}},
        "vs_construction": {"a": _vs_construction(records, a), "b": _vs_construction(records, b)},
    }
