from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .analysis import analyze, write_analysis
from .annotation import export_blind, merge_annotations
from .evaluator import OllamaClient, build_report, run_evaluation
from .generator import generate, read_jsonl, validate, write_release


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        config = json.load(fh)
    for key in ("seed", "pair_families", "hard_benign", "split_ratios"):
        if key not in config:
            raise ValueError(f"Missing configuration key: {key}")
    if config["pair_families"] < 1 or config["hard_benign"] < 0:
        raise ValueError("Invalid requested record counts")
    return config


def command_generate(args) -> int:
    config = load_config(args.config)
    records = generate(config, args.calibration)
    errors = validate(records)
    if errors:
        raise ValueError("Generated data failed validation:\n" + "\n".join(errors))
    manifest = write_release(records, args.output, config)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_validate(args) -> int:
    rows = read_jsonl(args.input)
    errors = validate(rows)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"VALID: {len(rows)} records")
    return 0


def command_stats(args) -> int:
    rows = read_jsonl(args.input)
    for field in ("label", "language", "scenario", "split"):
        print(f"{field}: {dict(sorted(Counter(r[field] for r in rows).items()))}")
    return 0


def command_models(args) -> int:
    client = OllamaClient(args.host)
    print(f"Ollama {client.version()} at {client.host}")
    for model in client.tags():
        details = model.get("details", {})
        print(f'{model["name"]}\t{model["digest"]}\t{details.get("parameter_size")}\t{details.get("quantization_level")}')
    return 0


def command_evaluate(args) -> int:
    manifest = run_evaluation(args.dataset, args.output, args.models, host=args.host,
                              limit=args.limit, repeats=args.repeats, temperature=args.temperature,
                              seed=args.seed, num_predict=args.num_predict, retries=args.retries,
                              input_modes=args.input_modes)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_report(args) -> int:
    report = build_report(args.results)
    target = args.output or args.results.with_suffix(".report.json")
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"Report written to {target}")
    return 0


def command_analyze(args) -> int:
    report = analyze(args.results, args.dataset, bootstrap_iterations=args.bootstrap_iterations,
                     seed=args.seed)
    paths = write_analysis(report, args.output)
    print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2, sort_keys=True))
    return 0


def command_annotation_export(args) -> int:
    count = export_blind(args.dataset, args.output, args.annotator)
    print(f"Exported {count} blinded assignments to {args.output}")
    return 0


def command_annotation_merge(args) -> int:
    print(json.dumps(merge_annotations(args.annotator_a, args.annotator_b, args.output), indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    base = root()
    p = argparse.ArgumentParser(prog="dataset-generator-2")
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate", help="Generate a deterministic context-aware dataset")
    g.add_argument("--config", type=Path, default=base / "configs" / "generator2.json")
    g.add_argument("--calibration", type=Path, default=base / "data" / "calibration" / "Calibration_Records_v1.jsonl")
    g.add_argument("--output", type=Path, default=base / "data" / "generated" / "dataset_v2_2.jsonl")
    g.set_defaults(func=command_generate)
    v = sub.add_parser("validate", help="Validate a generated JSONL release")
    v.add_argument("input", type=Path)
    v.set_defaults(func=command_validate)
    s = sub.add_parser("stats", help="Print dataset distributions")
    s.add_argument("input", type=Path)
    s.set_defaults(func=command_stats)
    m = sub.add_parser("models", help="List installed Ollama models and immutable digests")
    m.add_argument("--host")
    m.set_defaults(func=command_models)
    e = sub.add_parser("evaluate", help="Run resumable Ollama detection evaluation")
    e.add_argument("--dataset", type=Path, default=base / "data" / "generated" / "dataset_v2_2.jsonl")
    e.add_argument("--output", type=Path, default=base / "evaluation" / "results" / "ollama_detection_v1.jsonl")
    e.add_argument("--models", nargs="+", required=True)
    e.add_argument("--host")
    e.add_argument("--limit", type=int)
    e.add_argument("--repeats", type=int, default=1)
    e.add_argument("--temperature", type=float, default=0)
    e.add_argument("--seed", type=int, default=42)
    e.add_argument("--num-predict", type=int, default=120)
    e.add_argument("--retries", type=int, default=2)
    e.add_argument("--input-modes", nargs="+", choices=["text_only", "context_aware"],
                   default=["text_only", "context_aware"])
    e.set_defaults(func=command_evaluate)
    rep = sub.add_parser("report", help="Build metrics from evaluator JSONL")
    rep.add_argument("results", type=Path)
    rep.add_argument("--output", type=Path)
    rep.set_defaults(func=command_report)
    a = sub.add_parser("analyze", help="Produce publication-oriented statistical analysis")
    a.add_argument("results", type=Path)
    a.add_argument("--dataset", type=Path, default=base / "data" / "generated" / "dataset_v2_2.jsonl")
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--bootstrap-iterations", type=int, default=2000)
    a.add_argument("--seed", type=int, default=20261113)
    a.set_defaults(func=command_analyze)
    ae = sub.add_parser("annotation-export", help="Create a blinded annotation assignment JSONL")
    ae.add_argument("--dataset", type=Path, default=base / "data" / "generated" / "dataset_v2_2.jsonl")
    ae.add_argument("--annotator", required=True)
    ae.add_argument("--output", type=Path, required=True)
    ae.set_defaults(func=command_annotation_export)
    am = sub.add_parser("annotation-merge", help="Measure agreement and create adjudication queue")
    am.add_argument("annotator_a", type=Path)
    am.add_argument("annotator_b", type=Path)
    am.add_argument("--output", type=Path, required=True)
    am.set_defaults(func=command_annotation_merge)
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

