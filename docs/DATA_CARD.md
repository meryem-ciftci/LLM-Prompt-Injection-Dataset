# Data Card — TR-EN Indirect Prompt Injection Pilot (Generator 3, v0.1.0)

Format: *Datasheets for Datasets* (Gebru et al., 2021). Machine-readable metadata:
[`data/generated/dg3_pilot_v0.croissant.json`](../data/generated/dg3_pilot_v0.croissant.json) (Croissant 1.0).

| | |
|---|---|
| File | `data/generated/dg3_pilot_v0.jsonl` |
| SHA-256 | `5ddad77fed5cd6de968541586b9e9d7b3a355ab55d78c6cca8570136801ad033` |
| Manifest | `data/generated/dg3_pilot_v0.manifest.json` |
| Config | `configs/dg3_pilot.json` (seed 20261116, 150 families) |
| Schema | `schemas/generated-record-v3.schema.json` (3.0.0-draft) |
| Generator | `src/dg3` 3.0.0.dev0 |
| License | CC BY-SA 4.0 (inherited from the Wikipedia-derived carriers) |

All numbers below are copied from the manifest or computed from the released file.
**No human annotation or human verification was performed.** Labels are construction
labels, and attack components passed an automatic, independent quality control.
**No attack-success or detector numbers are part of this release**; they are measured
separately (Generator 3 step 6) and reported as their own artifacts.

## 1. Motivation

- **Purpose.** Evaluate (a) detectors of *indirect* prompt injection, i.e. instructions hidden in
  retrieved or document content, and (b) whether target models follow such instructions (attack
  success) and how much task utility they lose, in Turkish and English.
- **Gap addressed.** The previous generator (G2.2) drew all variety from 20 seed attacks, used
  synthetic filler text, had toy goals and no success oracle. G3 uses licensed real carriers, a
  goal × technique taxonomy, deterministic witness oracles and matched benign controls.

## 2. Composition

**Unit.** A *family* of four records built from one carrier passage and one attack component:

| Role | Channel | Label | Purpose |
|---|---|---|---|
| `clean` | untrusted content | benign | utility reference, no insertion |
| `injected_untrusted` | untrusted content | injection | attack; character span of the injection |
| `authorized_twin` | trusted user channel | benign | identical text, authorized source: tests trust-boundary reasoning |
| `trigger_benign` | untrusted content | benign | inserted everyday sentence instead of the injection (NotInject-style control) |

**Size.** 600 records = 150 families (450 benign, 150 injection).

| Factor | Distribution (records) |
|---|---|
| Language | en 292, tr 308 |
| Scenario | rag 300, document_qa 300 |
| Split | train 336, validation 128, test 136 |
| Goal (7) | content_manipulation 84, data_exfiltration 92, phishing_link 84, prompt_leak 84, refusal_dos 84, task_hijack 88, unauthorized_tool_action 84 |
| Injection position | head 192, middle 204, tail 204 |
| Obfuscation | none 124, base64 144, char_split 188, leetspeak 144 |
| Context length bucket | short 232, medium 188, long 180 |
| Language mode | monolingual 588, code_switch 12 |

Stratification: every (language × scenario × goal) cell (28 cells) holds 5–6 families.
Measured words per record by bucket (min / median / max): short 232 / 255 / 554, medium
922 / 947 / 1174, long 2765 / 2789 / 2987. `char_split` obfuscation inflates word counts.

**Sources.** 150 injected records use 146 distinct carriers from 58 articles: SQuAD v1.1 dev
(73 families) and pinned Turkish Wikipedia revisions (77 families). 63 attack components are
used; the most reused component appears in 10 families.

**Attack metadata.** Each injected record carries goal, techniques (taxonomy in
`src/dg3/taxonomy.py`), obfuscation, the source component id, and a **witness** used as a
deterministic success oracle. Witness types in injected records: phrase 85, canary_token 23,
url 21, tool_call 21. All canaries, URLs (`*.example.invalid`) and tool names are fictional.
The validator guarantees the witness never appears in the `clean` or `trigger_benign` record
of its family.

**Splits.** Assigned per source article (`split_group`). Attack components are pinned to one
split, stratified per (language, goal) pool. The splits are therefore disjoint by family,
article and injection text. The manifest reports 0 cross-split near-duplicate pairs (word
3-gram MinHash/LSH, exact Jaccard ≥ 0.8). The 281 within-split pairs come from overlapping
windows of the same article.

**Not included.** Personal data, real credentials, executable payloads. No `borderline` labels.

## 3. Collection process

1. **Carriers** (`tools/ingest_carriers.py`, `sources/registry.json`). SQuAD v1.1 dev paragraphs
   and Turkish Wikipedia revisions are pinned by revision id. Each is windowed around an anchor
   paragraph to the 256 / 1024 / 3072-word buckets using real neighbouring sentences. A
   fail-closed licence gate and SHA-256 snapshot pins apply.
2. **Attack proposals** (`tools/local/propose_attacks.py`). `qwen3:8b` (digest pinned in
   `configs/versions.lock.json`) proposed one candidate per language × goal × technique cell: 126
   candidates.
3. **Automatic QC** (`tools/local/auto_qc.py`, `src/dg3/qc.py`, version 1.2.0):
   - rule checks: validation, safety, toy filters, loose-witness filter, technique-cue and language checks;
   - an independent judge model (`llama3.1:8b`, different from the proposer);
   - instruction-template and trigger-text near-duplicate filters.

   63 of 126 passed. Summary: `data/attack_components/auto_attacks_qwen3_8b_b1cb379f.qc_summary.json`.
   QC measures **candidate validity only, not attack success**.
4. **Assembly** (`python -m src.dg3 generate --config configs/dg3_pilot.json`). The assembly is
   deterministic: the same inputs and seed give a byte-identical file (verified by regenerating
   and comparing SHA-256).

## 4. Preprocessing and labelling

- Text is NFC-normalised. Injection spans are character offsets and are round-trip validated
  (`carrier_text[start:end] == text`).
- Labels follow the family role (construction labels).
- **Automatic label agreement** (not a human annotation study). Two local models labelled all
  600 records blind with `tools/local/prelabel.py`: `qwen3:8b` and `mistral:latest`, temperature 0,
  16k context. The report is `data/annotation/agreement_dg3_pilot_v0__qwen3_8b__mistral_latest.json`.

  | | qwen3:8b | mistral:latest |
  |---|---|---|
  | κ vs construction labels | 0.58 | 0.18 |
  | Agreement vs construction | 0.85 | 0.69 |
  | `injected_untrusted` labelled injection | 90 / 150 | 29 / 150 |
  | `authorized_twin` labelled benign | 122 / 150 | 142 / 150 |
  | `clean` labelled benign | 150 / 150 | 122 / 150 |
  | `trigger_benign` labelled benign | 150 / 150 | 123 / 150 |
  | Mean injection-span char IoU | 0.39 | 0.05 |

  Inter-model κ = 0.07 (raw agreement 0.69). The two models disagree mostly on injected records.
  These numbers describe how well small local models recover the construction labels; they are
  **not** a validation of the labels and not a detector benchmark.

## 5. Uses

- **Intended:** detector benchmarking with trust-boundary awareness; attack-success (witness
  match) and utility measurement on target models; analysis by goal, technique, position,
  obfuscation, length and language.
- **Not intended:** training models to produce attacks; any claim of human-verified gold labels.

## 6. Known limitations

- Pilot scale (150 families). Attack text is model-generated and reused within a split (up to
  10 families per component).
- Uneven technique coverage among the accepted components: few `multilingual_switch` (5
  injected records) and `role_play` (11) records. English `unauthorized_tool_action` has a
  single accepted component, so that cell is absent from the held-out splits.
- `trigger_benign` texts are everyday sentences. Only 12 of the 63 accepted components' trigger
  texts contain trigger vocabulary ("ignore", "system", "talimat" and similar), so these records
  are mostly ordinary benign controls rather than hard negatives.
- Turkish carriers have no reference answers (`utility_check: none`), so task utility is
  measurable only for English (`squad_f1`). Machine-translated SQuAD-TR carriers are prepared
  (`tools/local/translate_carriers.py`) but not included.
- Scenarios cover `rag` and `document_qa` only. The email, repository and tool-output scenarios
  are not populated yet.

## 7. Distribution and maintenance

- Distributed in this repository under CC BY-SA 4.0. Attribution: SQuAD v1.1 (Rajpurkar et
  al., 2016) and Turkish Wikipedia contributors (revision ids in `sources/trwiki_revisions.json`).
- Reproduce: re-ingest the carriers from the pinned sources, then run the generate command
  above. Every component and record carries provenance (carrier id, component id, model
  digests, prompt hashes).
- Changes are made by releasing new versioned files with a new manifest. Released files are
  never edited in place.
