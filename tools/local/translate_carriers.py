"""Translate EN carriers to Turkish with a local model, recording full lineage.

    python tools/local/translate_carriers.py --model gemma3:4b [--buckets short medium] [--limit N]

Input:  data/raw/carriers/squad11_dev.jsonl
Output: data/raw/carriers/squad11_dev_trmt.log.jsonl (resumable, completion order)
        data/raw/carriers/squad11_dev_trmt.jsonl     (canonical, sorted snapshot)
        data/raw/translation_cache/en-tr_<model>.jsonl
Overlapping windows share paragraphs, so each paragraph is translated once
(cache keyed by source SHA-256). After a full run, pin the printed sha256 in
sources/registry.json as registry_id squad11_dev_trmt (CC-BY-SA-4.0 derivative).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from _boot import ROOT, model_slug, open_model

from src.dg2.generator import read_jsonl
from src.dg3.ingest import carriers_payload
from src.dg3.local_models import (ALIGN_SYSTEM, TRANSLATE_SYSTEM, ResumableJsonl, TranslationCache, sha,
                                  translate_carrier)

TARGET = "squad11_dev_trmt"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="gemma3:4b")
    p.add_argument("--host")
    p.add_argument("--seed", type=int, default=20261116)
    p.add_argument("--input", type=Path, default=ROOT / "data" / "raw" / "carriers" / "squad11_dev.jsonl")
    p.add_argument("--buckets", nargs="+", default=["short", "medium", "long"])
    p.add_argument("--limit", type=int)
    args = p.parse_args(argv)

    raw = ROOT / "data" / "raw"
    out = ResumableJsonl(raw / "carriers" / f"{TARGET}.log.jsonl", "carrier_id")
    prompt_tag = sha(TRANSLATE_SYSTEM + ALIGN_SYSTEM)[:8]  # new prompts never reuse old translations
    cache = TranslationCache(raw / "translation_cache" / f"en-tr_{model_slug(args.model)}_{prompt_tag}.jsonl")
    chat, meta = open_model(args.model, tool="translate_carriers", seed=args.seed, temperature=0.0,
                            system_prompt=TRANSLATE_SYSTEM, host=args.host,
                            log_path=raw / "translation_run_log.jsonl")
    carriers = [c for c in read_jsonl(args.input) if c.get("length_bucket") in args.buckets]
    made = 0
    for carrier in sorted(carriers, key=lambda c: c["carrier_id"]):
        target_id = f"{TARGET}:{carrier['carrier_id'].split(':', 1)[1]}"
        if target_id in out.done:
            continue
        if args.limit is not None and made >= args.limit:
            break
        try:
            row = translate_carrier(chat, args.model, carrier, cache, seed=args.seed, meta=meta,
                                    target_registry_id=TARGET)
        except Exception as exc:
            print(f"error {carrier['carrier_id']}: {exc}", file=sys.stderr)
            continue
        out.append(row)
        made += 1
        print(f"[{made}] {target_id} words={row['measured_words']} "
              f"answer_in_text={row['lineage']['reference_answer_in_text']}")
    rows = sorted(read_jsonl(out.path), key=lambda r: r["carrier_id"]) if out.path.exists() else []
    payload = carriers_payload(rows)
    (raw / "carriers" / f"{TARGET}.jsonl").write_bytes(payload)
    print(f"done: {made} new, {len(rows)} total; {TARGET}.jsonl sha256={hashlib.sha256(payload).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
