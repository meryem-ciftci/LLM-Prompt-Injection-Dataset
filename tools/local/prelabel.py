"""Suggest labels and spans for annotators with a local model. NEVER gold.

    python tools/local/prelabel.py DATASET.jsonl --model qwen3:8b [--limit N]

Output: data/annotation/prelabels_<model>.jsonl (resumable), one row per record
with status model_prelabel_not_gold. Show these to annotators only after their
blind first pass, otherwise the kappa report is contaminated.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from _boot import ROOT, model_slug, open_model

from src.dg2.generator import read_jsonl
from src.dg3.local_models import PRELABEL_SYSTEM, ResumableJsonl, prelabel_record


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dataset", type=Path)
    p.add_argument("--model", default="qwen3:8b")
    p.add_argument("--host")
    p.add_argument("--seed", type=int, default=20261116)
    p.add_argument("--limit", type=int)
    args = p.parse_args(argv)

    out = ResumableJsonl(ROOT / "data" / "annotation" / f"prelabels_{model_slug(args.model)}.jsonl", "record_id")
    chat, meta = open_model(args.model, tool="prelabel", seed=args.seed, temperature=0.0,
                            system_prompt=PRELABEL_SYSTEM, host=args.host,
                            log_path=ROOT / "data" / "annotation" / "prelabel_run_log.jsonl")
    made, labels = 0, Counter()
    for record in sorted(read_jsonl(args.dataset), key=lambda r: r["record_id"]):
        if record["record_id"] in out.done:
            continue
        if args.limit is not None and made >= args.limit:
            break
        try:
            row = prelabel_record(chat, args.model, record, seed=args.seed, meta=meta)
        except Exception as exc:
            print(f"error {record['record_id']}: {exc}", file=sys.stderr)
            continue
        out.append(row)
        made += 1
        labels[row["suggested_label"]] += 1
    print(f"done: {made} new; suggested label counts (not gold): {dict(labels)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
