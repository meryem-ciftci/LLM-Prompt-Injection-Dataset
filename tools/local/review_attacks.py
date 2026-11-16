"""Human review of model-proposed attack components (CSV round trip).

    python tools/local/review_attacks.py export data/proposals/attacks_qwen3_8b.jsonl review.csv
    # Fill 'decision' with accept / reject and your initials in 'reviewer'.
    # You may edit instruction, trigger_benign_text and techniques (pipe-separated).
    python tools/local/review_attacks.py import data/proposals/attacks_qwen3_8b.jsonl review.csv data/attack_components/reviewed_qwen3_8b.jsonl

Accepted rows become annotation_status single_annotated (assemblable) and are
re-validated; a row that fails validation after edits is refused, not written.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import _boot  # noqa: F401  (sets import path)

from src.dg2.generator import canonical_json, read_jsonl
from src.dg3.attacks import validate_component
from src.dg3.local_models import safety_issues

COLUMNS = ["component_id", "language", "goal", "techniques", "witness_value", "instruction",
           "trigger_benign_text", "auto_check_errors", "decision", "reviewer", "note"]


def export(src: Path, dst: Path) -> int:
    with dst.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, COLUMNS)
        writer.writeheader()
        for r in read_jsonl(src):
            writer.writerow({"component_id": r["component_id"], "language": r["language"], "goal": r["goal"],
                             "techniques": "|".join(r["techniques"]), "witness_value": r["witness"]["value"],
                             "instruction": r["instruction"], "trigger_benign_text": r["trigger_benign_text"],
                             "auto_check_errors": "; ".join(r.get("auto_check", {}).get("errors", [])),
                             "decision": "", "reviewer": "", "note": ""})
    print(f"exported -> {dst}")
    return 0


def apply_review(proposals: dict[str, dict], rows: list[dict]) -> tuple[list[dict], list[tuple[str, object]]]:
    accepted, refused = [], []
    for row in rows:
        if row.get("decision", "").strip().lower() != "accept":
            continue
        cid = row["component_id"]
        if cid not in proposals:
            refused.append((cid, "unknown component_id"))
            continue
        if not row.get("reviewer", "").strip():
            refused.append((cid, "reviewer missing"))
            continue
        r = dict(proposals[cid])
        r["instruction"] = row["instruction"].strip()
        r["trigger_benign_text"] = row["trigger_benign_text"].strip()
        r["techniques"] = [t for t in row["techniques"].split("|") if t]
        r["annotation_status"] = "single_annotated"
        r["review"] = {"reviewer": row["reviewer"].strip(), "note": row.get("note", "").strip() or None}
        r.pop("auto_check", None)
        errors = validate_component(r) + safety_issues(r["instruction"] + " " + r["trigger_benign_text"], r["witness"])
        if errors:
            refused.append((cid, errors))
            continue
        accepted.append(r)
    return sorted(accepted, key=lambda r: r["component_id"]), refused


def import_(src: Path, review: Path, dst: Path) -> int:
    proposals = {r["component_id"]: r for r in read_jsonl(src)}
    with review.open(encoding="utf-8-sig", newline="") as fh:
        accepted, refused = apply_review(proposals, list(csv.DictReader(fh)))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("".join(canonical_json(r) + "\n" for r in accepted), encoding="utf-8", newline="\n")
    print(f"accepted {len(accepted)} -> {dst}")
    for cid, why in refused:
        print(f"refused {cid}: {why}", file=sys.stderr)
    return 1 if refused else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("src", type=Path)
    e.add_argument("dst", type=Path)
    i = sub.add_parser("import")
    i.add_argument("src", type=Path)
    i.add_argument("review", type=Path)
    i.add_argument("dst", type=Path)
    args = p.parse_args(argv)
    return export(args.src, args.dst) if args.cmd == "export" else import_(args.src, args.review, args.dst)


if __name__ == "__main__":
    raise SystemExit(main())
