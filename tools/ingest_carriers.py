"""Build G3 carrier files from licensed corpora.

Usage (from the repository root):

    python tools/ingest_carriers.py squad
    python tools/ingest_carriers.py wiki-resolve     # pin current revision IDs (run once)
    python tools/ingest_carriers.py wiki-fetch       # fetch pinned revisions, build carriers

Raw inputs and carrier JSONL go to data/raw/ (git-ignored). Committed outputs:
sources/manifests/<registry_id>.manifest.json (IDs + hashes) and the pins in
sources/trwiki_revisions.json. After a run, copy the printed carriers_sha256
into sources/registry.json so loading fails closed if the text ever changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dg3.ingest import (carriers_manifest, carriers_payload, html_paragraphs,  # noqa: E402
                            squad_carriers, wiki_carriers)

CONFIG = json.loads((ROOT / "sources" / "ingest.json").read_text(encoding="utf-8"))
RAW = ROOT / "data" / "raw"
MANIFESTS = ROOT / "sources" / "manifests"
USER_AGENT = "dataset-ingest/0.1 (python-urllib; research corpus builder)"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_outputs(carriers: list[dict], registry_id: str) -> None:
    payload = carriers_payload(carriers)
    digest = sha256_bytes(payload)
    out = RAW / "carriers" / f"{registry_id}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    manifest = carriers_manifest(carriers, registry_id=registry_id, payload_sha256=digest)
    (MANIFESTS / f"{registry_id}.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"registry_id": registry_id, "carriers_file": str(out.relative_to(ROOT)),
                      "carriers_sha256": digest, "carrier_count": manifest["carrier_count"],
                      "length_buckets": manifest["length_buckets"], "split_groups": manifest["split_groups"]},
                     ensure_ascii=False, indent=2))


def command_squad(args) -> int:
    cfg = CONFIG["squad11_dev"]
    raw_path = ROOT / cfg["raw_path"]
    raw = raw_path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != cfg["raw_sha256"]:
        raise SystemExit(f"{raw_path}: sha256 {digest} != pinned {cfg['raw_sha256']}")
    carriers = squad_carriers(json.loads(raw.decode("utf-8")), registry_id="squad11_dev", raw_sha256=digest,
                              seed=CONFIG["seed"], anchors_per_article=cfg["anchors_per_article"],
                              buckets=tuple(CONFIG["length_buckets"]))
    write_outputs(carriers, "squad11_dev")
    return 0


def api_get(params: dict) -> dict:
    url = CONFIG["trwiki"]["api"] + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 5:
                raise
            wait = int(exc.headers.get("Retry-After") or 0) or 10 * 2 ** attempt
            print(f"rate limited; retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def command_wiki_resolve(args) -> int:
    cfg = CONFIG["trwiki"]
    pins_path = ROOT / cfg["pins_path"]
    titles = cfg["titles"]
    pins = []
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        data = api_get({"action": "query", "prop": "revisions", "rvprop": "ids", "redirects": 1,
                        "titles": "|".join(batch)})
        for page in data["query"]["pages"]:
            if page.get("missing"):
                print(f"missing page: {page['title']}", file=sys.stderr)
                continue
            pins.append({"title": page["title"], "revid": page["revisions"][0]["revid"]})
        time.sleep(1)
    pins.sort(key=lambda p: p["revid"])
    pins_path.write_text(json.dumps({"api": cfg["api"], "revisions": pins}, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    print(f"pinned {len(pins)} revisions -> {pins_path.relative_to(ROOT)}")
    return 0


def command_wiki_fetch(args) -> int:
    cfg = CONFIG["trwiki"]
    pins = json.loads((ROOT / cfg["pins_path"]).read_text(encoding="utf-8"))["revisions"]
    cache = RAW / "trwiki"
    cache.mkdir(parents=True, exist_ok=True)
    articles = []
    for pin in pins:
        path = cache / f"{pin['revid']}.html"
        if not path.exists():
            data = api_get({"action": "parse", "oldid": pin["revid"], "prop": "text", "disableeditsection": 1})
            path.write_text(data["parse"]["text"], encoding="utf-8", newline="\n")
            time.sleep(3)
        html = path.read_text(encoding="utf-8")
        articles.append({"title": pin["title"], "revid": pin["revid"],
                         "html_sha256": sha256_bytes(html.encode("utf-8")), "paragraphs": html_paragraphs(html)})
    carriers = wiki_carriers(articles, registry_id="trwiki", language="tr", seed=CONFIG["seed"],
                             anchors_per_article=cfg["anchors_per_article"], buckets=tuple(CONFIG["length_buckets"]))
    write_outputs(carriers, "trwiki")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("squad").set_defaults(func=command_squad)
    sub.add_parser("wiki-resolve").set_defaults(func=command_wiki_resolve)
    sub.add_parser("wiki-fetch").set_defaults(func=command_wiki_fetch)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
