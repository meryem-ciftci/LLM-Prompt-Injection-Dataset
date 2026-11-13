# Evaluation workspace

This directory is intentionally empty in the active source tree except for documentation and placeholder files. Evaluator JSONL, run manifests, and statistical reports are generated artifacts and are ignored by Git.

Before running an experiment:

1. Add or update its row in the root README experiment registry.
2. Freeze the generator/schema/config commit and dataset SHA-256.
3. Verify Ollama and model digests with `python tools/verify_environment.py`.
4. Use a unique experiment ID in result paths, for example `evaluation/results/EXP-002.jsonl`.
5. Preserve final result/run/analysis artifacts in a tagged GitHub Release or other immutable research archive; record their hashes in the experiment registry.

Historical Generator 2.0/2.1 files remain available through Git history. They are not active benchmark inputs.
