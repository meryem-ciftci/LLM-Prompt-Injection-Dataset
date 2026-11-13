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

Generate the default 100-record dataset:

```powershell
python main.py generate
```

Output:

```text
data/generated/dataset_v2.jsonl
data/generated/dataset_v2.manifest.json
```

Validate a release:

```powershell
python main.py validate data/generated/dataset_v2.jsonl
```

Show distributions:

```powershell
python main.py stats data/generated/dataset_v2.jsonl
```

Run all tests:

```powershell
python -m unittest discover -s tests -v
```

Rebuild the calibration exports:

```powershell
python tools/build_calibration_pack.py
```

## Default generation design

The default configuration creates:

| Component | Count |
|---|---:|
| Untrusted injection members | 40 |
| Authorized benign twins | 40 |
| Independent hard-benign records | 20 |
| **Total** | **100** |

The 40 matched families isolate the trust-boundary variable: the text remains identical while source authority changes. The additional hard-benign records test keyword-based overblocking.

Change `pair_families`, `hard_benign`, `seed`, or split ratios in `configs/generator2.json`. Generation does not call an LLM or download a mutable remote dataset.

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

## Current status

Generator 2 is a working deterministic baseline and calibration-driven candidate generator. Its generated records still require the dual-annotation and adjudication process described in the guide before publication as a gold benchmark.

