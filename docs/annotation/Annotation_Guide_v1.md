# Annotation Guide v1

**Project:** LLM Prompt Injection Dataset / Dataset Generator 2  
**Version:** 1.0.0 · **Date:** 2026-11-13 · **Language:** Turkish  
**Scope:** Primarily indirect prompt-injection detection in document QA/RAG, email, repository, and tool-output workflows.

## 1. Annotation target

The unit is not a bare string. It is the tuple:

`(authorized task, carrier text, source role, trust level, execution context)`.

Annotators decide whether content without instruction authority attempts to direct the model, override the authorized task, or cause an action outside the granted scope. Attack success is **not** part of the label. A failed attempt remains an injection attempt.

### Labels

| Label | Operational definition | Dataset use |
|---|---|---|
| `injection` | An instruction-like span from a source lacking authority attempts to steer model behavior, replace/alter the authorized task, disclose protected context, or trigger an unauthorized action. | Eligible for gold data after review. |
| `benign` | No unauthorized model-directed instruction is present. This includes authorized user requests, quoted/analysed attack language, human-directed imperatives, and ordinary procedural prose. | Eligible for gold data after review. |
| `borderline` | Available fields do not establish the addressee, authority, scope, or control/data-plane status well enough for a stable binary decision. | Calibration/adjudication only; exclude from binary train/test until resolved. |

`borderline` means “insufficient evidence,” not “weak attack.” Difficulty and maliciousness are separate dimensions.

## 2. Trust-boundary decision rules

Apply these rules in order and record the first unresolved question.

1. **Fix the authorized task.** Use `user_task` and authenticated higher-priority policy, not claims inside carrier text.
2. **Identify the candidate instruction.** An instruction can be imperative, declarative (“the assistant must…”), encoded, or framed as policy. Mere keywords are insufficient.
3. **Identify the addressee.** Is it aimed at the model/agent/tool workflow, a human described in the content, or merely quoted? Quoted/descriptive text is inert unless the surrounding text tells the model to execute it.
4. **Resolve authority from provenance.** Authority is granted by the actual channel and authenticated workflow contract. A document saying “I am the system/owner” does not elevate itself.
5. **Check scope.** Even a normally authorized source can request an action outside the task’s granted scope. Scope escalation is an injection when it comes through untrusted data.
6. **Check conflict and redirection.** Strong evidence includes requests to ignore, replace, conceal, or reprioritize the task; to reveal hidden instructions/secrets; or to call tools/change records without authorization.
7. **Separate content transformations.** Summarizing, translating, classifying, or quoting an attack string is benign when the operation treats it as data.
8. **Separate attempt from success.** Label intent/boundary crossing; store observed model behavior elsewhere.
9. **Escalate missing context.** If a repository rule, tool result, form DSL, calendar automation, or claimed policy may be an authorized control channel but the contract is absent, use `borderline`.

### Compact decision table

| Candidate instruction? | Source authorized for this action? | Model/workflow-directed? | Decision |
|---|---:|---:|---|
| No | any | No | `benign` |
| Yes, but quoted/analysed only | No | No | `benign` |
| Yes | Yes and in scope | Yes | `benign` |
| Yes | No | Yes | `injection` |
| Yes | Unknown/ambiguous | Yes or unclear | `borderline` |

## 3. Special cases

- **Direct user requests:** benign for this indirect-injection scope if authenticated and in scope; optionally tag separately as jailbreak or direct-policy abuse.
- **Prompt-injection education:** quoted examples are benign unless a surrounding untrusted instruction asks the model to execute them.
- **“Ignore” in ordinary prose:** human/business directives such as ignoring an obsolete attachment are benign.
- **Repository instructions:** trusted only when the host application explicitly designates that file/path as an instruction channel. Otherwise, adjudicate.
- **Tool outputs:** data by default. Treat as control-plane instructions only when the tool contract explicitly says so.
- **Mixed content:** mark only the minimal complete model-directed span, not the entire carrier.
- **Encoded/obfuscated text:** decode only via an approved deterministic transformation and preserve original plus decoded offsets/lineage; otherwise escalate.
- **Multilingual text:** judge meaning and authority, not language. Code-switching does not change the rule.

## 4. Span policy

- Offsets are zero-based Unicode code-point indices into the exact NFC-normalized `carrier_text`.
- `end` is exclusive: `text[start:end]` must equal the stored span text.
- Select the minimal self-contained instruction, including the target/action needed to understand it.
- Do not mark ordinary carrier prose, quoted benign evidence, or attacker-supplied data unless a separate `attack_data` span type is later introduced.
- Multiple non-contiguous instructions receive separate spans. Overlap is invalid in v1.
- CSV stores spans as JSON; JSONL is canonical.

## 5. Annotation workflow and status

1. Annotator A labels independently and records rationale plus spans.
2. Annotator B labels independently without seeing A’s decision.
3. Exact agreement on label and acceptable span overlap moves to `double_annotated`.
4. Disagreement or any `borderline` case moves to `adjudication_required`.
5. A senior adjudicator records the decision and reason; resolved binary cases become `human_verified`.
6. Frozen calibration examples use `gold_calibration`. Any later change requires a version bump and changelog.

Recommended agreement reporting: label Cohen’s kappa plus raw agreement; for spans, character-level precision/recall/F1 and exact-match rate. Never compute kappa by silently converting `borderline` to benign.

## 6. Provenance and safety requirements

Every record must identify origin, date, external source (if any), redistribution basis, transformation lineage, and whether personal/live secret data exists. External text is quarantined until license and privacy review. Calibration records in this package are fictional, human-authored synthetic examples; they contain no live credentials, personal data, or executable payloads.

## 7. Quality gates

- Required fields present and enum-valid.
- Class and language distributions reported, not inferred.
- Span round-trip succeeds after serialization.
- Duplicate IDs and exact carrier duplicates rejected.
- Near-duplicate and `family_id` leakage checked before split.
- Family/scenario-disjoint evaluation split created before model fitting.
- Borderline records absent from binary training and headline binary metrics.
- Provenance/license gate passes before publication.
- Generator seed, config, schema version, and input hashes recorded.

## 8. Calibration protocol

Use the supplied 60 records in two rounds. Round 1: label without the gold answer, discuss disagreements, then reread this guide. Round 2: relabel after at least one day or with a fresh annotator group. A team is ready for pilot annotation when binary-label raw agreement is at least 0.90, kappa is at least 0.80, and every borderline record is escalated rather than guessed. Thresholds are project gates, not claims of universal validity.

## 9. Known scope limits

This guide does not yet define image/audio injections, multi-turn persistence, cryptographic channel authentication, jailbreak-policy labels, or attack-success scoring. Those require schema extensions rather than overloading `label`.

