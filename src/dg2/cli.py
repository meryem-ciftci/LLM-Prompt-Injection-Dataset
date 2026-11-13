from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

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


def parser() -> argparse.ArgumentParser:
    base = root()
    p = argparse.ArgumentParser(prog="dataset-generator-2")
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate", help="Generate a deterministic context-aware dataset")
    g.add_argument("--config", type=Path, default=base / "configs" / "generator2.json")
    g.add_argument("--calibration", type=Path, default=base / "data" / "calibration" / "Calibration_Records_v1.jsonl")
    g.add_argument("--output", type=Path, default=base / "data" / "generated" / "dataset_v2.jsonl")
    g.set_defaults(func=command_generate)
    v = sub.add_parser("validate", help="Validate a generated JSONL release")
    v.add_argument("input", type=Path)
    v.set_defaults(func=command_validate)
    s = sub.add_parser("stats", help="Print dataset distributions")
    s.add_argument("input", type=Path)
    s.set_defaults(func=command_stats)
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

