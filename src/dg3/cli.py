from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.dg2.generator import read_jsonl

from .assembler import generate, load_default_schema, validate, write_release
from .attacks import load_components
from .sources import load_carriers


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    for key in ("seed", "families", "split_ratios"):
        if key not in config:
            raise ValueError(f"Missing configuration key: {key}")
    if config["families"] < 1:
        raise ValueError("families must be >= 1")
    return config


def command_generate(args) -> int:
    config = load_config(args.config)
    records = generate(config, load_carriers(args.registry), load_components(args.components))
    errors = validate(records, load_default_schema())
    if errors:
        raise ValueError("Generated data failed validation:\n" + "\n".join(errors))
    manifest = write_release(records, args.output, config)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_validate(args) -> int:
    rows = read_jsonl(args.input)
    errors = validate(rows, load_default_schema())
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"VALID: {len(rows)} records")
    return 0


def build_parser() -> argparse.ArgumentParser:
    base = root()
    parser = argparse.ArgumentParser(prog="python -m src.dg3", description="Dataset Generator 3")
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate", help="Assemble a deterministic four-member-family dataset")
    g.add_argument("--config", type=Path, required=True)
    g.add_argument("--registry", type=Path, default=base / "sources" / "registry.json")
    g.add_argument("--components", type=Path, default=base / "data" / "attack_components")
    g.add_argument("--output", type=Path, required=True)
    g.set_defaults(func=command_generate)
    v = sub.add_parser("validate", help="Validate a G3 JSONL release against schema and family rules")
    v.add_argument("input", type=Path)
    v.set_defaults(func=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
