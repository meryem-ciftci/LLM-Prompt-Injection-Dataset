# Dataset Generator 2 — Technical Architecture and Test Plan

**Version:** 1.0.0 · **Date:** 2026-11-13

## Goals and invariants

Generator 2 produces reproducible, provenance-preserving, context-aware detection records. It must not decide labels from attack keywords alone. The trust contract and human annotation remain authoritative; model generation is a proposal mechanism, never the final judge.

Core invariants:

- canonical UTF-8 JSONL; NFC normalization before offset calculation;
- deterministic output for identical inputs/config/seed/tool versions;
- stable IDs and immutable lineage (`family_id`, `parent_id`, transformations);
- injection span round-trip correctness;
- no unresolved license/privacy records in publishable output;
- family-disjoint and source-disjoint evaluation partitions;
- `borderline` excluded from binary training until adjudicated;
- generation, detection, and attack-success results are separate tables/artifacts.

## Pipeline

```text
Source registry -> quarantine ingest -> normalize -> safety/license gate
     -> scenario + trust-contract assembly -> candidate generation
     -> deterministic transformations -> duplicate/leakage checks
     -> annotation queue -> dual annotation + adjudication
     -> split assignment -> frozen JSONL/CSV + data card + manifest
```

### Components

1. **Source registry:** source URI/snapshot, license, consent, checksum, language, collection method, allowed transformations.
2. **Quarantine ingest:** never mixes unreviewed external text with release data. Redacts/flags personal data; preserves raw hash.
3. **Normalizer:** UTF-8, line-ending and NFC policy; emits a character map when transformation changes offsets.
4. **Scenario assembler:** joins an authorized task, source role, trust level, carrier text, and capability policy. Trust is metadata from the host workflow, not self-asserted text.
5. **Candidate factory:** human-authored seeds, controlled templates, or approved model-assisted proposals. Saves prompt/model/config/seed when a model is used.
6. **Transformation engine:** translation, position, carrier, and paraphrase variants with explicit lineage. No unconstrained mutation in benchmark test families.
7. **Validator:** schema/enums, span round-trip, safety/provenance, duplicates, label/status compatibility.
8. **Annotation service/export:** blinded independent assignments, disagreement capture, adjudication audit trail.
9. **Splitter:** group-based assignment by family/source/scenario; creates ID, OOD-language, OOD-family, and long-context evaluation lanes.
10. **Publisher:** canonical JSONL, convenience CSV/Parquet, manifest/checksums, data card, changelog, and reproducibility command.

## Suggested repository layout

```text
configs/                 # versioned YAML; seed and policy
schemas/record-v1.json   # JSON Schema
sources/registry.*       # metadata only; raw licensed data stays quarantined
src/dg2/                 # ingest, normalize, assemble, transform, validate, split
annotation/              # guide, forms, adjudication log schema
data/calibration/        # this 60-record pack
data/releases/vX.Y.Z/    # immutable release artifacts
tests/unit/              # pure deterministic tests
tests/integration/       # fixture-to-release pipeline
tests/property/          # Unicode/offset and determinism properties
```

## Record model

Required core: `record_id`, `schema_version`, `language`, `scenario`, `user_task`, `source`, `carrier_text`, `label`, `injection_spans`, `trust_boundary_decision`, `decision_rationale`, `annotation_status`, `provenance`, `safety`. The production schema should additionally require `family_id`, `split`, content hash, annotator decision references, and a transformation array. Model outcomes belong in a separate evaluation artifact keyed by record/version.

## Test matrix

| ID | Level | Assertion |
|---|---|---|
| U01 | Unit | Same config/input/seed produces byte-identical canonical JSONL. |
| U02 | Unit | NFC text and every span round-trip exactly. |
| U03 | Unit | Negative, reversed, out-of-range, overlapping, or UTF-16-derived offsets fail. |
| U04 | Unit | Injection requires ≥1 injection span; benign/borderline v1 require none. |
| U05 | Unit | Label/status combinations follow the annotation state machine. |
| U06 | Unit | Self-claimed authority never changes source trust metadata. |
| U07 | Unit | Unknown enums, duplicate IDs, and missing provenance fail closed. |
| U08 | Unit | CSV JSON fields deserialize to canonical JSONL equivalents. |
| P01 | Property | Random Turkish/English Unicode prefixes preserve calculated offsets. |
| P02 | Property | Serialize/deserialize is idempotent. |
| I01 | Integration | A clean fixture runs end-to-end and emits manifest/checksum/data card. |
| I02 | Integration | Unlicensed or privacy-flagged source remains quarantined. |
| I03 | Integration | Family/source groups never cross configured split boundaries. |
| I04 | Integration | Borderline samples cannot enter binary training export. |
| I05 | Integration | Near-duplicate report is produced before split freeze. |
| R01 | Regression | The 60 calibration records retain IDs, labels, counts, and checksum. |
| R02 | Regression | Keyword hard negatives stay benign; paired authority changes produce expected labels. |
| S01 | Security | Template variables cannot escape schema or write outside the output directory. |
| S02 | Security | Logs redact credentials and do not contain raw quarantined text. |

## Release acceptance

CI must run schema validation, unit/integration tests, checksum verification, exact/near-duplicate audit, group-leakage audit, and distribution report. A release is blocked on any invalid span, unresolved provenance/license status, missing adjudication for binary labels, or split leakage. Human sign-off records the schema, guide, source-registry and generator commit hashes.

## Calibration-pack executable tests

This package includes `tools/build_calibration_pack.py` and `tests/test_calibration_records.py`. Run:

```powershell
python tools/build_calibration_pack.py
python -m unittest discover -s tests -v
```

These tests validate the 20/20/20 balance, unique IDs, safe provenance, status policy, span round-trip, and CSV/JSONL equivalence. They are a seed suite, not a complete production generator implementation.

## Compatibility and evidence note

The architecture follows the project decisions captured in the referenced research conversation: indirect injection focus, Turkish/English data, document/RAG-email-repository scenarios, trust boundaries, matched contexts, spans, provenance, independent human review, and a later 600-record pilot. Generator 1's former `p/d/a/x/y` implementation has been replaced by the working Generator 2 baseline described here. The current 100-record generated release is a deterministic engineering smoke test and candidate set—not the human-adjudicated 600-record research pilot.

