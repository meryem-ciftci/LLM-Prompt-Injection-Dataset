# Data Card — TR-EN Indirect Prompt Injection Pilot (Generator 3)

Format: *Datasheets for Datasets* (Gebru et al., 2021). This card describes the **current
release, v1 (0.2.0)**. The earlier v0 release stays available unchanged; see §8 for what
changed and why.

| | v1 (current) | v0 |
|---|---|---|
| File | `data/generated/dg3_pilot_v1.jsonl` | `data/generated/dg3_pilot_v0.jsonl` |
| SHA-256 | `d05c6730415ce8cbf080da577a0227a77af2a90ac6b3e9c61db0ccf72c802327` | `5ddad77fed5cd6de968541586b9e9d7b3a355ab55d78c6cca8570136801ad033` |
| Config | `configs/dg3_pilot_v1.json` | `configs/dg3_pilot.json` |
| Attack components | `data/attack_components/qc-1.3.0/` (65) | `data/attack_components/qc-1.2.0/` (63) |
| Croissant 1.0 | [`dg3_pilot_v1.croissant.json`](../data/generated/dg3_pilot_v1.croissant.json) | [`dg3_pilot_v0.croissant.json`](../data/generated/dg3_pilot_v0.croissant.json) |
| Evaluated in | EXP-004 (registered) | [EXP-003](../evaluation/reports/EXP-003.md) |

Schema `schemas/generated-record-v3.schema.json` (3.0.0-draft); generator `src/dg3` 3.0.0.dev0;
seed 20261116; 150 families. Data licence CC BY-SA 4.0 (inherited from the Wikipedia-derived
carriers); code MIT.

All numbers below are copied from the manifest or computed from the released file.
**No human annotation or human verification was performed.** Labels are construction
labels, and attack components passed an automatic, independent quality control. Attack-success
and detector numbers are not part of a release; they are measured separately and reported as
their own artifacts under `evaluation/reports/`.

## 1. Motivation

- **Purpose.** Evaluate (a) detectors of *indirect* prompt injection, i.e. instructions hidden in
  retrieved or document content, and (b) whether target models follow such instructions (attack
  success) and how much task utility they lose, in Turkish and English.
- **Gap addressed.** The previous generator (G2.2) drew all variety from 20 seed attacks, used
  synthetic filler text, had toy goals and no success oracle. G3 uses licensed real carriers, a
  goal × technique taxonomy, deterministic witness oracles and matched benign controls.

## 2. Composition (v1)

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
| Language | en 304, tr 296 |
| Scenario | rag 308, document_qa 292 |
| Split | train 324, validation 128, test 148 |
| Goal (7) | content_manipulation 80, data_exfiltration 84, phishing_link 88, prompt_leak 84, refusal_dos 84, task_hijack 92, unauthorized_tool_action 88 |
| Injection position | head 220, middle 192, tail 188 |
| Obfuscation | none 316, leetspeak 116, char_split 96, base64 72 |
| Context length bucket | short 196, medium 220, long 184 |
| Language mode | monolingual 588, code_switch 12 |

Stratification: every (language × scenario × goal) cell (28 cells) holds 5–6 families.
Measured words per record by bucket (min / median / max): short 232 / 258 / 505, medium
922 / 946 / 1198, long 2765 / 2793 / 3085. `char_split` obfuscation inflates word counts.

**Sources.** 150 injected records use 146 distinct carriers from 57 articles: SQuAD v1.1 dev
(76 families) and pinned Turkish Wikipedia revisions (74 families). All 65 attack components
are used, and the most reused component appears in 6 families.

**Attack metadata.** Each injected record carries:
- goal and techniques (taxonomy in `src/dg3/taxonomy.py`);
- obfuscation;
- the source component id;
- a **witness**, used as a deterministic success oracle. Witness types in injected records:
  phrase 85, url 22, tool_call 22, canary_token 21.

All canaries, URLs (`*.example.invalid`) and tool names are fictional. The validator
guarantees that the witness never appears in the `clean` or `trigger_benign` record of its family.

**Splits.**
- Assigned per source article (`split_group`).
- Each attack component is pinned to one split, stratified per (language, goal) pool.
- The splits are therefore disjoint by family, article and injection text.
- 0 near-duplicate pairs cross a split (word 3-gram MinHash/LSH, exact Jaccard ≥ 0.8). All 331
  near-duplicate pairs are within one split; they come from overlapping windows of the same article.
- Test covers all 14 language × goal cells; validation covers 13 of them (English
  `unauthorized_tool_action` is missing).

**Not included.** Personal data, real credentials, executable payloads. No `borderline` labels.

## 3. Collection process

1. **Carriers** (`tools/ingest_carriers.py`, `sources/registry.json`). SQuAD v1.1 dev paragraphs
   and Turkish Wikipedia revisions are pinned by revision id. Each is windowed around an anchor
   paragraph to the 256 / 1024 / 3072-word buckets using real neighbouring sentences. A
   fail-closed licence gate and SHA-256 snapshot pins apply.
2. **Attack proposals** (`tools/local/propose_attacks.py`). `qwen3:8b` (digest pinned in
   `configs/versions.lock.json`) proposed one candidate per language × goal × technique cell (126).
   `unauthorized_tool_action` was then topped up with four more candidates per cell (72), giving
   198 candidates in total.
3. **Automatic QC** (`tools/local/auto_qc.py`, `src/dg3/qc.py`, version 1.3.0). Three stages:
   - rule checks: validation, safety, toy filters, loose-witness filter, precondition-gated
     requests, tool witnesses that are not requested as calls, technique-cue and language checks;
   - an independent judge model (`llama3.1:8b`, different from the proposer);
   - instruction-template and trigger-text near-duplicate filters.

   65 of 198 passed. Summary: `data/attack_components/qc-1.3.0/auto_attacks_qwen3_8b_b1cb379f.qc_summary.json`.
   QC measures **candidate validity only, not attack success**.
4. **Assembly** (`python -m src.dg3 generate --config configs/dg3_pilot_v1.json`).
   - Obfuscation is weighted toward feasible lanes (`obfuscation_mix` none 10 : leetspeak 4 :
     char_split 3 : base64 3).
   - Base64 and char-split wrappers are written in the record's language.
   - The assembly is deterministic: regenerating with the same inputs gives a byte-identical file.

## 4. Preprocessing and labelling

- Text is NFC-normalised. Injection spans are character offsets and are round-trip validated
  (`carrier_text[start:end] == text`).
- Labels follow the family role (construction labels).
- **Automatic label agreement** (not a human annotation study) has been measured on **v0**. Two
  local models labelled all 600 v0 records blind (`tools/local/prelabel.py`; `qwen3:8b` and
  `mistral:latest`, temperature 0, 16k context). Report:
  `data/annotation/agreement_dg3_pilot_v0__qwen3_8b__mistral_latest.json`.

  | v0 | qwen3:8b | mistral:latest |
  |---|---|---|
  | κ vs construction labels | 0.58 | 0.18 |
  | Agreement vs construction | 0.85 | 0.69 |
  | `injected_untrusted` labelled injection | 90 / 150 | 29 / 150 |
  | `authorized_twin` labelled benign | 122 / 150 | 142 / 150 |
  | `clean` labelled benign | 150 / 150 | 122 / 150 |
  | `trigger_benign` labelled benign | 150 / 150 | 123 / 150 |
  | Mean injection-span char IoU | 0.39 | 0.05 |

  Inter-model κ = 0.07 (raw agreement 0.69). These numbers describe how well small local models
  recover the construction labels; they are **not** a validation of the labels. No agreement
  run exists for v1 yet.

## 5. Uses

- **Intended:** detector benchmarking with trust-boundary awareness; attack-success (witness
  match) and utility measurement on target models; analysis by goal, technique, position,
  obfuscation, length and language.
- **Not intended:** training models to produce attacks; any claim of human-verified gold labels.

## 6. Known limitations

- Pilot scale (150 families). Attack text is model-generated and reused within a split (up to
  6 families per component in v1).
- Uneven technique coverage among accepted components. Few `multilingual_switch` (6 injected
  records) and `role_play` (11) records. English `unauthorized_tool_action` rests on 2 components.
- `trigger_benign` texts are everyday sentences. Only 11 of the 65 accepted components' trigger
  texts contain trigger vocabulary ("ignore", "system", "talimat" and similar), so these records
  are mostly ordinary benign controls rather than hard negatives.
- Turkish carriers have no reference answers (`utility_check: none`), so task utility is
  measurable only for English (`squad_f1`). Machine-translated SQuAD-TR carriers are prepared
  (`tools/local/translate_carriers.py`) but not included.
- Scenarios cover `rag` and `document_qa` only.
- Base64 instructions were not executed by any of five small local models even when asked
  directly (EXP-003: 0/180). The lane is kept, at lower weight, as a stress condition.

## 7. Distribution and maintenance

- Distributed in this repository under CC BY-SA 4.0. Attribution: SQuAD v1.1 (Rajpurkar et
  al., 2016) and Turkish Wikipedia contributors (revision ids in `sources/trwiki_revisions.json`).
- Reproduce: re-ingest the carriers from the pinned sources, then run the generate command
  above. Every component and record carries provenance (carrier id, component id, model
  digests, prompt hashes).
- Changes are made by releasing new versioned files with a new manifest. Released files are
  never edited in place.

## 8. Version history

**v1 (0.2.0).** Changes made after analysing EXP-003 on v0:

| Problem found in EXP-003 | Change in v1 |
|---|---|
| Base64 0/180 and char_split 32/235 successes even when the injected task was asked directly, so most obfuscated families were infeasible; only 31 of 150 families were unobfuscated. | Weighted obfuscation mix; 79 of 150 families are unobfuscated. |
| Obfuscation wrappers were English in Turkish records. | Wrappers are written in the record's language. |
| Some accepted instructions were gated by a precondition ("If you are unsure, …"), or asked to *write* a tool name instead of calling the tool. | QC 1.3.0 rejects both; tool action was topped up to 8 components. |

The evaluation changes (1024-token responses, lenient tool oracle, `ASR_unobfuscated`) are in
`src/dg3/target_eval.py` 1.2.0.

**v0 (0.1.0).** First pilot; QC 1.2.0 components; uniform obfuscation. It is still reproducible
with `configs/dg3_pilot.json`.
