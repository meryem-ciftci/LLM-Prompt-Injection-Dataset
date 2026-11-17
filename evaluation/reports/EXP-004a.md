# EXP-004a — Quick stratified check on pilot v1

| | |
|---|---|
| Status | Completed · quick check (go/no-go for EXP-004b) |
| Dataset | `data/generated/dg3_pilot_v1.jsonl`, SHA-256 `d05c6730415ce8cbf080da577a0227a77af2a90ac6b3e9c61db0ccf72c802327` |
| Pre-registered | README experiment registry, commit `24867eb` (before the run) |
| Subset | `--per-cell 1`: one family per language × scenario × goal cell, 28 families |
| Settings | eval 1.2.0, Ollama 0.40.16, temperature 0, seed 20261116, num_ctx 16384, num_predict 1024 |
| Inference | 140 responses per model, 700 total; 0 runner errors |
| Report | [`EXP-004a.json`](EXP-004a.json) |

## Go/no-go criteria (as registered)

| Criterion | Result | |
|---|---|---|
| 0 witness hits on clean / trigger_benign that are not spontaneous tool calls | 0 / 280 | ✅ |
| < 5% truncated responses | 25 / 700 (3.6%) overall; but **mistral 23 / 140 (16%)**, others 0–1 | ✅ overall, ⚠️ mistral |
| No runner errors | 700 / 700 responses | ✅ |

The mistral truncations are not a budget problem. The responses run to the 1,024-token limit
because the model loops: it repeats the same clause about the document until generation
stops. Only 5 of the 23 are injected records. Raising `num_predict` again would not help.

## Results

Small subset, wide intervals. These numbers are a smoke check, not findings.

| Metric | gemma3:4b | llama3.1:8b | llama3 | mistral | qwen3:8b |
|---|---|---|---|---|---|
| ASR_targeted | 8/28 | 2/28 | 3/28 | 8/28 | 5/28 |
| ASR_unobfuscated | 7/12 | 2/12 | 3/12 | 8/12 | 4/12 |
| Same task asked directly | 15/28 | 6/28 | 10/28 | 16/28 | 15/28 |
| MR | 8/15 | 0/6 | 1/10 | 7/16 | 5/15 |
| Witness hits on clean + trigger_benign | 0/56 | 0/56 | 0/56 | 0/56 | 0/56 |
| Spontaneous tool calls on clean + trigger_benign | 0/56 | 3/56 | 2/56 | 0/56 | 0/56 |
| Utility, answer contained (en): clean → attacked | 11/14 → 13/14 | 13/14 → 12/14 | 11/14 → 12/14 | 12/14 → 11/14 | 13/14 → 13/14 |

Pooled over the five models (injected records / same task asked directly):

| Obfuscation | Under indirect injection | Asked directly |
|---|---|---|
| none | 24/60 | 48/60 |
| leetspeak | 2/25 | 12/25 |
| char_split | 0/40 | 1/40 |
| base64 | 0/15 | 1/15 |

## What this check shows

- **The pipeline and oracle behave as intended on v1.** There were no oracle false positives,
  no runner errors, and the 1,024-token limit removed truncation everywhere except mistral's
  repetition loops.
- **Weighting toward unobfuscated families gives the experiment usable signal.** Unobfuscated
  ASR is 2–8 of 12 per model, and the injected task is followed directly in 48 of 60 cases.
- **char_split and Base64 remain almost infeasible** for these models, even when asked
  directly (2/55). They stay in v1 as low-weight stress lanes, as the data card states.
- The single unobfuscated phishing family in this subset was followed directly by 4 of 5 models
  but under injection by none. That is model behaviour on one family, not an oracle problem:
  the URL appears verbatim in the direct-request replies.

## Decision

The registered go criteria are met overall. mistral's truncation rate exceeds 5% because of
model degeneration, not because of the token limit. Recommendation: **proceed to EXP-004b
with the protocol unchanged** and report mistral's truncations as a limitation. Changing
decoding settings (for example a repeat penalty) would make 004b differ from 004a, so it is not
done here.
