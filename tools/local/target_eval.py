"""Run target models on a G3 release and report ASR / utility / MR (src/dg3/target_eval.py).

    # 0) quick stratified check first (1 family per language x scenario x goal cell)
    python tools/local/target_eval.py run data/generated/dg3_pilot_v1.jsonl --model llama3.1:8b --exp EXP-004a --per-cell 1
    # 1) collect responses (resumable; one file per model)
    python tools/local/target_eval.py run data/generated/dg3_pilot_v0.jsonl --model llama3.1:8b --exp EXP-003
    # 2) score and aggregate every model of the experiment (+ optional detector label files)
    python tools/local/target_eval.py report data/generated/dg3_pilot_v0.jsonl --exp EXP-003 \
        --labels data/annotation/prelabels_dg3_pilot_v0_qwen3_8b_<tag>.jsonl

Raw responses: evaluation/results/<exp>__<model>.jsonl (git-ignored; archive with the release).
Report:        evaluation/reports/<exp>.json
Responses are stored unscored, so the oracle can be re-applied without re-running models.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from _boot import ROOT, model_slug, open_model

from src.dg2.generator import read_jsonl
from src.dg3.local_models import NUM_CTX, ResumableJsonl, sha
from src.dg3.target_eval import (EVAL_VERSION, TARGET_SYSTEM, family_attacks, injection_text,
                                 localization_report, render, score, summarize)

RESULTS = ROOT / "evaluation" / "results"
REPORTS = ROOT / "evaluation" / "reports"
NUM_PREDICT = 1024  # EXP-003 used 400; mistral was truncated in 275/750 responses


def select_families(records: list[dict], limit_families: int | None = None,
                    per_cell: int | None = None) -> set[str]:
    """Families to run. ``per_cell`` takes the first N family ids of every language x scenario x goal
    cell (a deterministic, stratified subset for quick checks); ``limit_families`` the first N overall."""
    if per_cell is not None:
        cells: dict[tuple, list[str]] = {}
        for r in records:
            if r["family_role"] == "injected_untrusted":
                key = (r["language"], r["scenario"], r["experimental_factors"]["goal"])
                cells.setdefault(key, []).append(r["family_id"])
        return {f for fams in cells.values() for f in sorted(fams)[:per_cell]}
    families = sorted({r["family_id"] for r in records})
    return set(families[:limit_families] if limit_families is not None else families)


def jobs(records: list[dict], limit_families: int | None = None,
         per_cell: int | None = None) -> list[tuple[str, dict, str]]:
    """(condition, record, user_prompt) for every record plus one injected_alone per family."""
    keep = select_families(records, limit_families, per_cell)
    out = []
    for r in sorted(records, key=lambda r: (r["family_id"], r["family_role"])):
        if r["family_id"] not in keep:
            continue
        out.append((r["family_role"], r, render(r)))
        if r["family_role"] == "injected_untrusted":
            out.append(("injected_alone", r, injection_text(r)))
    return out


def cmd_run(args) -> int:
    records = read_jsonl(args.dataset)
    out = ResumableJsonl(RESULTS / f"{args.exp}__{model_slug(args.model)}.jsonl", "key")
    chat, meta = open_model(args.model, tool="target_eval", seed=args.seed, temperature=0.0,
                            system_prompt=TARGET_SYSTEM, host=args.host, log_path=RESULTS / "run_log.jsonl")
    dataset_sha = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    todo = jobs(records, args.limit_families, args.per_cell)
    for i, (condition, record, prompt) in enumerate(todo, 1):
        key = f"{record['record_id']}|{condition}"
        if key in out.done:
            continue
        try:
            reply = chat.chat_text(args.model, TARGET_SYSTEM, prompt, seed=args.seed, temperature=0.0,
                                   num_predict=args.num_predict)
        except Exception as exc:
            print(f"error {key}: {exc}", file=sys.stderr)
            continue
        out.append({"key": key, "record_id": record["record_id"], "family_id": record["family_id"],
                    "condition": condition, **reply, "model": args.model, "model_digest": meta["model_digest"],
                    "system_prompt_sha256": sha(TARGET_SYSTEM), "user_prompt_sha256": sha(prompt),
                    "dataset_sha256": dataset_sha, "seed": args.seed, "num_ctx": NUM_CTX,
                    "num_predict": args.num_predict})
        print(f"[{len(out.done)}/{len(todo)}] {key}", flush=True)
    print(f"done: {len(out.done)}/{len(todo)} responses in {out.path.relative_to(ROOT).as_posix()}")
    return 0


def cmd_report(args) -> int:
    records = read_jsonl(args.dataset)
    by_id = {r["record_id"]: r for r in records}
    attacks = family_attacks(records)
    dataset_sha = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    report = {"exp": args.exp, "eval_version": EVAL_VERSION, "dataset": args.dataset.name,
              "dataset_sha256": dataset_sha, "target_system_prompt_sha256": sha(TARGET_SYSTEM),
              "scope": "measured from the result files listed; witness oracle, no LLM judge",
              "targets": {}, "detectors": {}}
    files = sorted(RESULTS.glob(f"{args.exp}__*.jsonl"))
    if not files:
        print(f"no result files for {args.exp} in {RESULTS}", file=sys.stderr)
        return 1
    for path in files:
        rows = read_jsonl(path)
        if {r["dataset_sha256"] for r in rows} != {dataset_sha}:
            print(f"{path.name}: responses belong to a different dataset version; skipped", file=sys.stderr)
            continue
        scored = [score(by_id[r["record_id"]], r["condition"], r["response"], attacks[r["family_id"]])
                  for r in rows]
        model = rows[0]["model"]
        report["targets"][model] = {"results_file": path.name,
                                    "results_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                    "model_digest": rows[0]["model_digest"],
                                    "truncated_responses": sum(r.get("done_reason") == "length" for r in rows),
                                    "aborted_responses": sum(r.get("done_reason") == "aborted_repeat_limit"
                                                             for r in rows),
                                    **summarize(records, scored)}
    for labels_path in args.labels or []:
        labels = {r["record_id"]: r for r in read_jsonl(labels_path)}
        model = next(iter(labels.values()))["model"]
        report["detectors"][model] = {"labels_file": labels_path.name,
                                      **localization_report(records, labels)}
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"{args.exp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"-> {out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("dataset", type=Path)
    r.add_argument("--model", required=True)
    r.add_argument("--exp", default="EXP-003")
    r.add_argument("--host")
    r.add_argument("--seed", type=int, default=20261116)
    r.add_argument("--limit-families", type=int)
    r.add_argument("--per-cell", type=int, help="N families per language x scenario x goal cell (quick stratified check)")
    r.add_argument("--num-predict", type=int, default=NUM_PREDICT)
    r.set_defaults(func=cmd_run)
    g = sub.add_parser("report")
    g.add_argument("dataset", type=Path)
    g.add_argument("--exp", default="EXP-003")
    g.add_argument("--labels", type=Path, nargs="*")
    g.set_defaults(func=cmd_report)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
