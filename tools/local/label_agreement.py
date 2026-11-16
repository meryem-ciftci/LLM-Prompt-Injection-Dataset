"""Automatic label agreement report (two independent local models vs construction labels).

    python tools/local/prelabel.py data/generated/dg3_pilot_v0.jsonl --model qwen3:8b
    python tools/local/prelabel.py data/generated/dg3_pilot_v0.jsonl --model mistral:latest
    python tools/local/label_agreement.py data/generated/dg3_pilot_v0.jsonl \
        data/annotation/prelabels_dg3_pilot_v0_qwen3_8b.jsonl \
        data/annotation/prelabels_dg3_pilot_v0_mistral_latest.jsonl

Writes data/annotation/agreement_<dataset>__<a>__<b>.json. Not a human annotation study.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _boot import ROOT, model_slug

from src.dg3.agreement import agreement_report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dataset", type=Path)
    p.add_argument("labels_a", type=Path)
    p.add_argument("labels_b", type=Path)
    args = p.parse_args(argv)
    report = agreement_report(args.dataset, args.labels_a, args.labels_b)
    m = report["models"]
    out = ROOT / "data" / "annotation" / (f"agreement_{args.dataset.stem}__{model_slug(m['a'])}"
                                          f"__{model_slug(m['b'])}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
