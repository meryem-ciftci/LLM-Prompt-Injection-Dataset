"""Propose candidate attack components with a local model (goal x technique x language grid).

    python tools/local/propose_attacks.py --model qwen3:8b [--per-cell 1] [--limit N]

Output: data/proposals/attacks_<model>.jsonl (resumable; status model_proposed).
Candidates that fail the automatic taxonomy/safety checks are kept with
auto_check.passed = false so the failure rate can be reported. Nothing here is
assembled until a human reviews it (tools/local/review_attacks.py).
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from _boot import ROOT, model_slug, open_model

from src.dg2.generator import stable_id
from src.dg3.local_models import PROPOSE_SYSTEM, ResumableJsonl, cell_key, proposal_grid, propose_one


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="qwen3:8b")
    p.add_argument("--host")
    p.add_argument("--seed", type=int, default=20261116)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--per-cell", type=int, default=1)
    p.add_argument("--languages", nargs="+", default=["en", "tr"])
    p.add_argument("--limit", type=int, help="stop after N new candidates (smoke runs)")
    args = p.parse_args(argv)

    out = ResumableJsonl(ROOT / "data" / "proposals" / f"attacks_{model_slug(args.model)}.jsonl", "component_id")
    chat, meta = open_model(args.model, tool="propose_attacks", seed=args.seed, temperature=args.temperature,
                            system_prompt=PROPOSE_SYSTEM, host=args.host,
                            log_path=ROOT / "data" / "proposals" / "run_log.jsonl")
    cells = proposal_grid(tuple(args.languages), per_cell=args.per_cell)
    made, status = 0, Counter()
    for cell in cells:
        key = cell_key(cell, args.seed)
        if stable_id("ATKP", key, args.model) in out.done:
            continue
        if args.limit is not None and made >= args.limit:
            break
        try:
            row = propose_one(chat, args.model, cell, seed=args.seed, temperature=args.temperature, meta=meta)
        except Exception as exc:  # keep going; report at the end
            status["error"] += 1
            print(f"error {key}: {exc}", file=sys.stderr)
            continue
        out.append(row)
        made += 1
        status["passed" if row["auto_check"]["passed"] else "failed_auto_check"] += 1
        print(f"[{made}] {key} -> {'ok' if row['auto_check']['passed'] else row['auto_check']['errors']}")
    print(f"done: {dict(status)}; total in file: {len(out.done)} / grid {len(cells)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
