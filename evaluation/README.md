# Evaluation

| Path | Contents |
|---|---|
| `results/EXP-xxx__<model>.jsonl` | Raw, unscored model responses with model digest, prompt hashes, seed and dataset SHA-256 |
| `results/run_log.jsonl` | One line per run start (model, digest, Ollama version, settings) |
| `reports/EXP-xxx.json` | Scored, aggregated report (machine-readable) |
| `reports/EXP-xxx.md` | Human-readable summary with limitations |

Responses are stored unscored. Re-applying the oracle (`target_eval.py report`) never
requires re-running a model, and reports skip responses whose dataset hash differs from the
dataset given.

Before running an experiment:

1. Register it in the README experiment registry and commit the registration.
2. Freeze the dataset (SHA-256 in its manifest) and check model digests against
   `configs/versions.lock.json`.
3. Use a unique experiment ID, for example `--exp EXP-005`.
4. Commit the results and report of completed, registered experiments. Results of
   unregistered or abandoned runs stay out of git (see `.gitignore`).

Generator 2 detector evaluation (`python main.py evaluate / report / analyze`) writes to the
same folders.
