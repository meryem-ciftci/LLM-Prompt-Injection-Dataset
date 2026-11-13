from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "configs" / "versions.lock.json").read_text(encoding="utf-8"))
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def get(path: str):
    with urllib.request.urlopen(HOST + path, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    errors = []
    version = get("/api/version").get("version")
    if version != LOCK["ollama_version"]:
        errors.append(f'Ollama version: expected {LOCK["ollama_version"]}, got {version}')
    installed = {m["name"]: m["digest"] for m in get("/api/tags").get("models", [])}
    for name, digest in LOCK["models"].items():
        if installed.get(name) != digest:
            errors.append(f'Model {name}: expected {digest}, got {installed.get(name)}')
    print(json.dumps({"host": HOST, "ollama_version": version, "models": installed,
                      "lock_valid": not errors, "errors": errors}, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
