# LLM Prompt Injection Dataset — Dataset Generator 2

Dataset Generator 2 creates reproducible, context-aware prompt-injection detection records. It is designed to test whether a detector understands **instruction authority and trust boundaries**, rather than merely memorizing words such as “ignore” or “system prompt.”

The previous SQuAD injection prototype has been removed. Generator 2 is the only active generator in this repository.

## Main features

- **Operational trust-boundary labels:** decisions use the authorized task, source role, trust level, and execution context.
- **Matched boundary pairs:** the exact same carrier text is emitted once as untrusted external content (`injection`) and once through an authorized instruction channel (`benign`).
- **Hard benign examples:** quoted, analytical, human-directed, and security-education language remains benign.
- **Turkish and English:** the calibration source contains 30 Turkish and 30 English examples.
- **Exact injection spans:** zero-based Unicode code-point offsets with an exclusive end; every span is round-trip validated.
- **Deterministic generation:** identical calibration data, configuration, and seed produce byte-identical canonical JSONL.
- **Stable lineage:** every record has `record_id`, `family_id`, `pair_id`, `parent_id`, transformation metadata, and source provenance.
- **Family-disjoint splits:** paired and related records cannot leak across train, validation, and test.
- **Safety metadata:** calibration inputs are fictional and contain no live secrets, real personal data, or executable payloads.
- **Fail-closed validation:** duplicate IDs, corrupt spans, hash mismatches, missing fields, and family split leakage are rejected.
- **Release manifest:** generation writes label/language/split counts and a SHA-256 digest next to the dataset.
- **Experimental-factor matrix:** carrier format, injection position, context-length bucket, language, scenario, and authority are explicit fields.
- **Ollama evaluation harness:** resumable multi-model runs, structured JSON decisions, immutable model digests, retries, latency/token telemetry, and subgroup reports.
- **Pinned environment:** Docker Compose pins Ollama/Python versions; `versions.lock.json` verifies exact local model digests.
- **No runtime dependencies:** Generator 2 uses the Python standard library.

## Repository layout

```text
configs/generator2.json                 Generation seed, size and split ratios
data/calibration/                       Human-authored 20/20/20 calibration pack
data/generated/                         Generated releases (created by the CLI)
docs/annotation/Annotation_Guide_v1.md  Operational annotation rules
docs/design/                            Architecture and integration assessment
schemas/                                Calibration JSON Schema
src/dg2/                                Generator 2 implementation
tests/                                  Calibration and generator test suites
tools/build_calibration_pack.py         Deterministic calibration-pack builder
main.py                                 CLI entry point
```

## Quick start

Python 3.10 or newer is recommended.

Generate the default 200-record v2.1 candidate dataset:

```powershell
python main.py generate
```

Output:

```text
data/generated/dataset_v2_1.jsonl
data/generated/dataset_v2_1.manifest.json
```

Validate a release:

```powershell
python main.py validate data/generated/dataset_v2_1.jsonl
```

Show distributions:

```powershell
python main.py stats data/generated/dataset_v2_1.jsonl
```

Run all tests:

```powershell
python -m unittest discover -s tests -v
```

List locally installed Ollama models and digests:

```powershell
python main.py models
python tools/verify_environment.py
```

Run a balanced 20-record smoke test across all pinned models:

```powershell
python main.py evaluate --limit 20 --models mistral:latest llama3:latest llama3.1:8b qwen3:8b gemma3:4b
python main.py report evaluation/results/ollama_detection_v1.jsonl
```

Run the full generated dataset by omitting `--limit`. Evaluation is resumable: rerunning the same command skips completed model/record/repeat tuples.

Create publication-oriented statistical outputs:

```powershell
python main.py analyze evaluation/results/ollama_full_200x5_v1.jsonl `
  --dataset data/generated/dataset_v2.jsonl `
  --output evaluation/reports/full_200x5
```

This writes `analysis.json`, `model_summary.csv`, and `report.md` with bootstrap/Wilson 95% intervals, exact paired McNemar tests with Holm correction, Brier/ECE calibration, latency quantiles, matched-pair accuracy, and factor/language/scenario breakdowns.

Rebuild the calibration exports:

```powershell
python tools/build_calibration_pack.py
```

## Default generation design

The default configuration creates:

| Component | Count |
|---|---:|
| Untrusted injection members | 80 |
| Authorized benign twins | 80 |
| Independent hard-benign records | 40 |
| **Total** | **200** |

The 80 matched families isolate the trust-boundary variable: the text remains identical while source authority changes. The additional hard-benign records test keyword-based overblocking. Eight controlled carrier variants cover plain text, document head/tail, tool XML, email, JSON, and longer middle/tail contexts.

Change `pair_families`, `hard_benign`, `seed`, or split ratios in `configs/generator2.json`. Generation does not call an LLM or download a mutable remote dataset.

`dataset_v2.jsonl` is retained as the immutable input used by the completed 1,000-inference Ollama experiment. Generator 2.1 writes to `dataset_v2_1.jsonl` so published experiment lineage is not overwritten.

## Record concepts

- `label`: intended detection ground truth (`injection` or `benign`).
- `annotation_status`: generated outputs are `generated_candidate` until reviewed by humans.
- `injection_spans`: present only when untrusted content attempts to direct the model.
- `pair_id`: connects the authorized and unauthorized versions of identical text.
- `family_id`: controls lineage and split isolation.
- `split`: assigned deterministically by hashing the family and seed.
- `content_sha256`: detects accidental carrier-text changes.

Attack success is deliberately not used as the detection label. Model behavior evaluation should be stored as a separate artifact keyed by record and model version.

## Annotation policy

Read [Annotation Guide v1](docs/annotation/Annotation_Guide_v1.md) before adding or reviewing data. `borderline` calibration records are adjudication exercises and are not exported into binary generated datasets.

Create blinded assignments for two annotators:

```powershell
python main.py annotation-export --annotator annotator-a --output annotation/a.jsonl
python main.py annotation-export --annotator annotator-b --output annotation/b.jsonl
```

After annotators fill the `decision` objects independently, measure agreement and create an adjudication queue:

```powershell
python main.py annotation-merge annotation/a.jsonl annotation/b.jsonl --output annotation/merged
```

The merge reports raw label agreement, Cohen's kappa, exact span agreement, and unresolved cases.

## Current status

Generator 2 is a working deterministic baseline and calibration-driven candidate generator. Its generated records still require the dual-annotation and adjudication process described in the guide before publication as a gold benchmark.

## Reproducible Docker environment

Docker is useful for pinning the generator, evaluator, Python, and Ollama server. Model weights are stored in a named volume; model tags are not assumed immutable, so every experiment records and verifies the model digest.

The pinned versions are in `configs/versions.lock.json`:

- Python image: `python:3.12.12-slim-bookworm`
- Ollama image/server: `0.40.16`
- Exact digests for the five evaluation models

On Windows, Docker Desktop must be running with the WSL 2 backend and NVIDIA GPU support. Then:

```powershell
docker compose up -d ollama
docker compose run --rm evaluator models
docker compose run --rm evaluator generate
docker compose run --rm evaluator evaluate --limit 20 --models mistral:latest llama3:latest llama3.1:8b qwen3:8b gemma3:4b
```

Models must first be pulled into the container volume with `docker compose exec ollama ollama pull <model>`. The native Windows Ollama model store and the Docker volume are separate; this duplication is intentional for reproducible container experiments.

