"""Automatic, independent QC of model-proposed attack components (no human review).

    python tools/local/auto_qc.py data/proposals/attacks_qwen3_8b_<tag>.jsonl --judge llama3.1:8b

Stages (src/dg3/qc.py): deterministic checks -> independent judge model (must
differ from the proposer) -> template near-duplicate filter.

Outputs:
  data/proposals/qc_<stem>__<judge>_<prompt>.jsonl         judge verdicts (resumable cache)
  data/proposals/qc_<stem>__<judge>_<prompt>.all.jsonl     every candidate with its qc block
  data/proposals/qc_<stem>__<judge>_<prompt>.summary.json  counts for the data card
  data/attack_components/qc-<version>/auto_<stem>.jsonl     passed rows, status auto_qc_passed
  data/attack_components/qc-<version>/auto_<stem>.qc_summary.json

QC measures candidate validity only; attack success (ASR) is measured later on
target models and is never inferred from passing QC.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _boot import ROOT, model_slug, open_model

from src.dg2.generator import canonical_json, read_jsonl
from src.dg3.qc import JUDGE_SYSTEM, QC_VERSION, deterministic_issues, finalize, judge_one, summary
from src.dg3.local_models import ResumableJsonl, sha


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("proposals", type=Path)
    p.add_argument("--judge", default="llama3.1:8b")
    p.add_argument("--host")
    p.add_argument("--seed", type=int, default=20261116)
    p.add_argument("--limit", type=int, help="judge at most N new candidates (smoke runs)")
    args = p.parse_args(argv)

    src = args.proposals if args.proposals.is_absolute() else ROOT / args.proposals
    rows = sorted(read_jsonl(src), key=lambda r: r["component_id"])
    proposers = {r.get("proposal", {}).get("model") for r in rows}
    if args.judge in proposers:
        print(f"judge {args.judge} also proposed these candidates; pick an independent model", file=sys.stderr)
        return 2

    stem = src.stem
    base = f"qc_{stem}__{model_slug(args.judge)}_{sha(JUDGE_SYSTEM)[:8]}"  # model slugs may contain dots
    cache = ResumableJsonl(src.parent / f"{base}.jsonl", "component_id")
    verdicts = {r["component_id"]: r["verdict"] for r in read_jsonl(cache.path)} if cache.path.exists() else {}
    chat, meta = open_model(args.judge, tool="auto_qc", seed=args.seed, temperature=0.0,
                            system_prompt=JUDGE_SYSTEM, host=args.host,
                            log_path=src.parent / "qc_run_log.jsonl")
    judged = 0
    for row in rows:
        cid = row["component_id"]
        if cid in verdicts or deterministic_issues(row):
            continue  # judge only what survives the rule stage
        if args.limit is not None and judged >= args.limit:
            break
        try:
            verdict = judge_one(chat, args.judge, row, seed=args.seed, meta=meta)
        except Exception as exc:
            print(f"error {cid}: {exc}", file=sys.stderr)
            continue
        cache.append({"component_id": cid, "verdict": verdict})
        verdicts[cid] = verdict
        judged += 1
        print(f"[{judged}] {cid} techniques={verdict['techniques_present']} goal={verdict['goal_match']} "
              f"plaus={verdict['plausibility']}")

    pending = [r["component_id"] for r in rows if not deterministic_issues(r) and r["component_id"] not in verdicts]
    if pending:
        print(f"{len(pending)} candidates still need a judge verdict; rerun to finish (no outputs written)")
        return 1
    final = finalize([(r, verdicts.get(r["component_id"])) for r in rows])
    (src.parent / f"{base}.all.jsonl").write_text("".join(canonical_json(r) + "\n" for r in final),
                                              encoding="utf-8", newline="\n")
    passed = [r for r in final if r["qc"]["passed"]]
    out = ROOT / "data" / "attack_components" / f"qc-{QC_VERSION}" / f"auto_{stem}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(canonical_json(r) + "\n" for r in passed), encoding="utf-8", newline="\n")
    report = summary(final) | {"proposals": src.name, "judge": args.judge, "judge_digest": meta["model_digest"]}
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (src.parent / f"{base}.summary.json").write_text(text, encoding="utf-8", newline="\n")
    out.with_name(f"auto_{stem}.qc_summary.json").write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"passed {len(passed)}/{len(final)} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
