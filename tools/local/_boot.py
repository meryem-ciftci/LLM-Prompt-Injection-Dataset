"""Shared setup for tools/local scripts: repo import path, model pinning, run log."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dg3.local_models import OllamaChat, pinned_digest, run_meta  # noqa: E402


def model_slug(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def open_model(model: str, *, tool: str, seed: int, temperature: float, system_prompt: str,
               host: str | None, log_path: Path) -> tuple[OllamaChat, dict]:
    """Connect, verify the model digest against versions.lock.json, append a run-log line."""
    chat = OllamaChat(host)
    digest = pinned_digest(model, chat.digest(model))
    meta = run_meta(tool=tool, model=model, digest=digest, seed=seed, temperature=temperature,
                    system_prompt=system_prompt, ollama_version=chat.version())
    meta["num_ctx"] = chat.num_ctx
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, sort_keys=True) + "\n")
    return chat, meta
