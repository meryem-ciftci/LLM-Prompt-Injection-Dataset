from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from .evaluator import binary_metrics, file_sha256
from .generator import read_jsonl


ANALYSIS_VERSION = "1.0.0"


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def brier_and_ece(rows: list[dict], bins: int = 10) -> tuple[float, float]:
    if not rows:
        return 0.0, 0.0
    probabilities, outcomes = [], []
    for row in rows:
        confidence = min(1.0, max(0.0, float(row.get("confidence", 0.0))))
        p_injection = confidence if row["predicted_label"] == "injection" else 1 - confidence
        probabilities.append(p_injection)
        outcomes.append(1.0 if row["gold_label"] == "injection" else 0.0)
    brier = sum((p - y) ** 2 for p, y in zip(probabilities, outcomes)) / len(rows)
    bucketed = defaultdict(list)
    for row in rows:
        confidence = min(1.0, max(0.0, float(row.get("confidence", 0.0))))
        bucketed[min(bins - 1, int(confidence * bins))].append((confidence, 1.0 if row["correct"] else 0.0))
    ece = 0.0
    for values in bucketed.values():
        mean_conf = sum(v[0] for v in values) / len(values)
        mean_acc = sum(v[1] for v in values) / len(values)
        ece += len(values) / len(rows) * abs(mean_conf - mean_acc)
    return brier, ece


def bootstrap_intervals(rows: list[dict], *, iterations: int = 2000, seed: int = 20261113) -> dict:
    if not rows:
        return {k: [0.0, 0.0] for k in ("accuracy", "f1", "mcc")}
    rng = random.Random(seed)
    values = {"accuracy": [], "f1": [], "mcc": []}
    for _ in range(iterations):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        metrics = binary_metrics(sample)
        for key in values:
            values[key].append(metrics[key])
    return {key: [percentile(samples, 0.025), percentile(samples, 0.975)]
            for key, samples in values.items()}


def exact_mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def holm_adjust(comparisons: list[dict]) -> None:
    ordered = sorted(enumerate(comparisons), key=lambda x: x[1]["p_value"])
    running = 0.0
    m = len(ordered)
    for rank, (original_index, item) in enumerate(ordered):
        adjusted = min(1.0, (m - rank) * item["p_value"])
        running = max(running, adjusted)
        comparisons[original_index]["p_holm"] = running


def deduplicated_successes(rows: list[dict]) -> list[dict]:
    latest = {}
    for row in rows:
        if row.get("status") == "ok":
            latest[(row["model"], row["record_id"], int(row.get("repeat", 0)))] = row
    return list(latest.values())


def analyze(result_file: Path, dataset: Path | None = None, *, bootstrap_iterations: int = 2000,
            seed: int = 20261113) -> dict:
    rows = deduplicated_successes(read_jsonl(result_file))
    dataset_rows = read_jsonl(dataset) if dataset else []
    dataset_by_id = {r["record_id"]: r for r in dataset_rows}
    models = sorted({r["model"] for r in rows})
    report = {
        "analysis_version": ANALYSIS_VERSION,
        "result_file": str(result_file), "result_sha256": file_sha256(result_file),
        "dataset": str(dataset) if dataset else None,
        "dataset_sha256": file_sha256(dataset) if dataset else None,
        "bootstrap_iterations": bootstrap_iterations, "seed": seed,
        "models": {}, "pairwise_mcnemar": [],
    }
    for model in models:
        selected = [r for r in rows if r["model"] == model]
        metrics = binary_metrics(selected)
        brier, ece = brier_and_ece(selected)
        latencies = [float(r.get("latency_ms", 0)) for r in selected]
        tp, tn, fp, fn = metrics["tp"], metrics["tn"], metrics["fp"], metrics["fn"]
        metrics.update({
            "accuracy_wilson_95": wilson_interval(tp + tn, metrics["n"]),
            "recall_wilson_95": wilson_interval(tp, tp + fn),
            "fpr_wilson_95": wilson_interval(fp, fp + tn),
            "bootstrap_95": bootstrap_intervals(selected, iterations=bootstrap_iterations, seed=seed),
            "brier_score": brier, "ece_10_bin": ece,
            "latency_p50_ms": percentile(latencies, 0.5),
            "latency_p95_ms": percentile(latencies, 0.95),
        })
        subgroups = {"language": {}, "scenario": {}, "split": {}, "authority": {},
                     "carrier_format": {}, "context_length_bucket": {}, "injection_position": {}}
        enriched = []
        for row in selected:
            source = dataset_by_id.get(row["record_id"], {})
            factors = source.get("experimental_factors", {})
            enriched.append((row, source, factors))
        for field in ("language", "scenario", "split"):
            for value in sorted({r.get(field) for r, _, _ in enriched if r.get(field) is not None}):
                subgroups[field][value] = binary_metrics([r for r, _, _ in enriched if r.get(field) == value])
        for field in ("authority", "carrier_format", "context_length_bucket", "injection_position"):
            for value in sorted({f.get(field) for _, _, f in enriched if f.get(field) is not None}):
                subgroups[field][value] = binary_metrics([r for r, _, f in enriched if f.get(field) == value])
        pair_groups = defaultdict(list)
        for row in selected:
            if row.get("pair_id"):
                pair_groups[(row["pair_id"], row.get("repeat", 0))].append(row)
        complete = [v for v in pair_groups.values() if len(v) == 2]
        report["models"][model] = {
            "metrics": metrics, "subgroups": subgroups,
            "pair_consistency": {"complete_pairs": len(complete),
                                 "both_correct": sum(all(x["correct"] for x in pair) for pair in complete),
                                 "both_correct_rate": (sum(all(x["correct"] for x in pair) for pair in complete) / len(complete) if complete else 0.0)},
        }
    by_model = {model: {(r["record_id"], r.get("repeat", 0)): r for r in rows if r["model"] == model}
                for model in models}
    for i, left in enumerate(models):
        for right in models[i + 1:]:
            common = sorted(set(by_model[left]) & set(by_model[right]))
            b = sum(by_model[left][k]["correct"] and not by_model[right][k]["correct"] for k in common)
            c = sum(not by_model[left][k]["correct"] and by_model[right][k]["correct"] for k in common)
            report["pairwise_mcnemar"].append({"model_a": left, "model_b": right, "n_common": len(common),
                                                "a_correct_b_wrong": b, "a_wrong_b_correct": c,
                                                "p_value": exact_mcnemar_p(b, c)})
    holm_adjust(report["pairwise_mcnemar"])
    return report


def write_analysis(report: dict, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "analysis.json"
    csv_path = output_dir / "model_summary.csv"
    md_path = output_dir / "report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    columns = ["model", "n", "accuracy", "precision", "recall", "f1", "fpr", "mcc",
               "brier_score", "ece_10_bin", "latency_p50_ms", "latency_p95_ms", "pair_both_correct_rate"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns); writer.writeheader()
        for model, entry in report["models"].items():
            metrics = entry["metrics"]
            writer.writerow({"model": model, **{k: metrics[k] for k in columns[1:-1]},
                             "pair_both_correct_rate": entry["pair_consistency"]["both_correct_rate"]})
    lines = ["# Automated Statistical Analysis", "",
             f'- Result SHA-256: `{report["result_sha256"]}`',
             f'- Dataset SHA-256: `{report.get("dataset_sha256")}`',
             f'- Bootstrap iterations: `{report["bootstrap_iterations"]}`', "",
             "## Model summary", "",
             "| Model | N | Accuracy | F1 | Recall | FPR | MCC | Brier | ECE | p50 ms | p95 ms |", 
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for model, entry in report["models"].items():
        m = entry["metrics"]
        lines.append(f'| {model} | {m["n"]} | {m["accuracy"]:.3f} | {m["f1"]:.3f} | {m["recall"]:.3f} | {m["fpr"]:.3f} | {m["mcc"]:.3f} | {m["brier_score"]:.3f} | {m["ece_10_bin"]:.3f} | {m["latency_p50_ms"]:.0f} | {m["latency_p95_ms"]:.0f} |')
    lines += ["", "## Pairwise exact McNemar tests (Holm-adjusted)", "",
              "| Model A | Model B | A right/B wrong | A wrong/B right | p | Holm p |",
              "|---|---|---:|---:|---:|---:|"]
    for item in report["pairwise_mcnemar"]:
        lines.append(f'| {item["model_a"]} | {item["model_b"]} | {item["a_correct_b_wrong"]} | {item["a_wrong_b_correct"]} | {item["p_value"]:.6f} | {item["p_holm"]:.6f} |')
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "markdown": md_path}
