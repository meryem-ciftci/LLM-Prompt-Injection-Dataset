# LLM Prompt Injection Dataset — Dataset Generator 2.2

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
- **Measured context construction:** deterministic 256/1,024/3,072 Unicode-word proxy buckets plus model-specific Ollama `prompt_eval_count` telemetry.
- **Robustness lanes:** plain, Base64, character-split, and leetspeak instructions with transformed-span lineage.
- **Paired evaluation views:** the same frozen record can be evaluated in `text_only` and `context_aware` modes.
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

Generate the default 200-record v2.2 candidate dataset:

```powershell
python main.py generate
```

Output:

```text
data/generated/dataset_v2_2.jsonl
data/generated/dataset_v2_2.manifest.json
```

Validate a release:

```powershell
python main.py validate data/generated/dataset_v2_2.jsonl
```

Show distributions:

```powershell
python main.py stats data/generated/dataset_v2_2.jsonl
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
python main.py evaluate --limit 20 --input-modes text_only context_aware --models mistral:latest llama3:latest llama3.1:8b qwen3:8b gemma3:4b
python main.py report evaluation/results/ollama_detection_v1.jsonl
```

Run the full generated dataset by omitting `--limit`. Evaluation is resumable: rerunning the same command skips completed model/record/repeat tuples.

Create publication-oriented statistical outputs:

```powershell
python main.py analyze evaluation/results/EXP-002.jsonl `
  --dataset data/generated/dataset_v2_2.jsonl `
  --output evaluation/reports/EXP-002
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

The 80 exact controlled families isolate the trust-boundary variable: carrier text is identical while source authority changes. The additional hard-benign records test keyword-based overblocking. Eight controlled carrier variants cover plain text, document head/tail, tool XML, email, JSON, and measured short/medium/long proxy contexts.

Change `pair_families`, `hard_benign`, `seed`, or split ratios in `configs/generator2.json`. Generation does not call an LLM or download a mutable remote dataset.

Generator 2.2 writes to `dataset_v2_2.jsonl`. Generator 2.0/2.1 datasets and exploratory outputs were removed from the active tree after being preserved in Git history; they are not active benchmark releases. The preregistered candidate hypotheses and the exploratory/confirmatory boundary are documented in `docs/research/Research_Questions_and_Hypotheses_v1.md`.

Context buckets are model-independent construction proxies, not claims of universal tokenizer counts:

| Bucket | Proxy target |
|---|---:|
| short | 256 Unicode words |
| medium | 1,024 Unicode words |
| long | 3,072 Unicode words |

Every Ollama result records the authoritative model-specific `prompt_eval_count`. The common panel is intentionally kept below the 8K context limit of the smallest model.

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

## Experiment registry

Every experiment must be registered here before its result is interpreted. Result JSONL files are generated artifacts and are not kept in the active source tree; the immutable dataset hash, run manifest, commit/tag, and published release artifact provide lineage.

| ID | Status | Purpose | Generator | Dataset SHA-256 | Models | Input views | Planned/completed inference | Result location |
|---|---|---|---|---|---|---|---:|---|
| EXP-001 | Completed · exploratory | Initial context-aware detector comparison | 2.0 | `6d99b4f8cd82ba190d1cb1bd57b8aa75a65a17abd7511c0fd1f17a780a12478f` | Mistral 7B, Llama 3 8B, Llama 3.1 8B, Qwen 3 8B, Gemma 3 4B | context-aware | 1,000 | Git history; removed from active tree |
| EXP-002 | Planned · confirmatory candidate | Text-only vs context-aware paired evaluation | 2.2 | `9678d92db6c1d98daba610cb87f03ce78725ba5a01c3995c69f9c148bd8dbe26` | Same pinned five-model panel | text-only + context-aware | 2,000 | Not run |

For every future row record: experiment ID, hypothesis, generator/schema version, dataset hash, Git commit or tag, model digests, Ollama version, input view, seed, temperature, repeats, planned sample count, run manifest, result hash, and analysis status.

## Current status

Generator 2.2 is the only active generator. Its 200 records are deterministic research candidates, not a gold benchmark. Confirmatory evaluation remains blocked on bilingual independent annotation, adjudication, and a frozen release/tag.

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

