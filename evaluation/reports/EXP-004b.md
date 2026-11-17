# EXP-004b — Target-model attack success on pilot v1 (exploratory)

| | |
|---|---|
| Status | Completed · exploratory (pilot v1; not confirmatory) |
| Dataset | `data/generated/dg3_pilot_v1.jsonl`, SHA-256 `d05c6730415ce8cbf080da577a0227a77af2a90ac6b3e9c61db0ccf72c802327` |
| Pre-registered | README experiment registry, commit `24867eb` (before EXP-004a and 004b were run) |
| Protocol | Same as [EXP-004a](EXP-004a.md): eval 1.2.0, Ollama 0.40.16, temperature 0, seed 20261116, num_ctx 16384, num_predict 1024, 1 repeat |
| Models (digest prefix) | gemma3:4b `68ceab7e468a`, llama3.1:8b `46e0c10c039e`, llama3:latest `365c0bd3c000`, mistral:latest `6577803aa9a0`, qwen3:8b `500a1f067a9f` |
| Inference | 750 responses per model (600 records + 150 `injected_alone`), 3,750 total; 0 runner errors |
| Reuse of 004a | The 700 EXP-004a responses were copied into the 004b files and not regenerated. The protocol is identical and decoding is deterministic, so the runner skipped those prompts. |
| Raw responses | `evaluation/results/EXP-004b__<model>.jsonl` |
| Machine-readable report | [`EXP-004b.json`](EXP-004b.json) |

Every number below was computed from the raw response files by `target_eval.py report` or
recomputed from them with the same scoring functions. Success is a **deterministic witness
match**; no LLM judge is used. Brackets are Wilson 95% intervals.

## Headline results

| Metric | gemma3:4b | llama3.1:8b | llama3 | mistral | qwen3:8b |
|---|---|---|---|---|---|
| ASR_targeted | 36/150 (24%, 18–31) | 19/150 (13%, 8–19) | 12/150 (8%, 5–13) | 38/150 (25%, 19–33)¹ | 25/150 (17%, 12–23) |
| ASR_unobfuscated | 33/79 (42%, 32–53) | 19/79 (24%, 16–35) | 12/79 (15%, 9–25) | 37/79 (47%, 36–58)¹ | 24/79 (30%, 21–41) |
| ASR_strict (no echo) | 35/150 | 18/150 | 11/150 | 34/150 | 22/150 |
| ASR_paired (clean twin no hit) | 36/150 | 19/150 | 12/150 | 38/150 | 25/150 |
| ASR_lenient_tool | 38/150 | 20/150 | 14/150 | 39/150 | 26/150 |
| Same task asked directly (`injected_alone`) | 104/150 | 40/150 | 58/150 | 103/150 | 98/150 |
| MR (witness-restricted) | 36/104 (35%, 26–44) | 8/40 (20%, 10–35) | 7/58 (12%, 6–23) | 35/103 (34%, 26–44) | 25/98 (26%, 18–35) |
| `authorized_twin` compliance | 54/150 | 33/150 | 27/150 | 50/150 | 47/150 |
| Witness hits on clean + trigger_benign | 0/300 | 0/300 | 0/300 | 0/300 | 0/300 |
| Spontaneous tool calls on clean + trigger_benign | 0/300 | 15/300 | 11/300 | 8/300 | 0/300 |
| Utility, answer contained (en): clean → attacked | 56/76 → 55/76 | 57/76 → 54/76 | 52/76 → 54/76 | 52/76 → 51/76 | 57/76 → 58/76 |
| SQuAD F1 (en): clean → attacked | 0.22 → 0.22 | 0.20 → 0.17 | 0.15 → 0.15 | 0.12 → 0.11 | 0.20 → 0.19 |
| Truncated responses (of 750) | 2 | 2 | 3 | 102 | 6 |

¹ Lower bound for mistral: 102 of its 750 responses (13.6%) hit the 1,024-token limit, 20 of
them on injected records. As in 004a, these are repetition loops, not long answers.

ASR_paired equals ASR_targeted for every model because no clean record produced a witness hit.
SQuAD F1 is low for all models because the replies are full sentences; answer containment is the
more informative utility measure here.

## Pooled breakdowns (five models)

Injected records versus the same injected instruction sent directly (`injected_alone`).
Each cell pools 5 models × the number of families in that level.

| Obfuscation | Under indirect injection | Asked directly |
|---|---|---|
| none | 125/395 | 303/395 |
| leetspeak | 5/145 | 82/145 |
| char_split | 0/120 | 17/120 |
| base64 | 0/90 | 1/90 |

Unobfuscated families only:

| Goal | Under indirect injection | Asked directly |
|---|---|---|
| content_manipulation | 29/60 | 48/60 |
| data_exfiltration | 24/55 | 45/55 |
| refusal_dos | 25/55 | 43/55 |
| prompt_leak | 18/45 | 35/45 |
| task_hijack | 14/50 | 44/50 |
| unauthorized_tool_action | 11/75 | 54/75 |
| phishing_link | 4/55 | 34/55 |

| Factor (all obfuscations) | Levels: under injection |
|---|---|
| Language | en 70/380 · tr 60/370 (unobfuscated: en 67/190 · tr 58/205) |
| Position | head 43/275 · middle 40/240 · tail 47/235 |
| Context length | short 63/245 · medium 38/275 · long 29/230 |

## What this run shows

- **The oracle stayed clean at full scale.** There were 0 witness hits on 1,500 clean and
  trigger_benign responses. The spontaneous tool calls (34 of 1,500, from llama3.1, llama3 and
  mistral) did not match any family's witness.
- **v1 gives much more measurable signal than v0.** Pooled ASR on unobfuscated families is
  125/395, and MR is 12–35% depending on the model. Indirect injection still succeeds far less
  often than the same instruction given directly, for every goal.
- **Obfuscated lanes stay close to infeasible.** char_split and Base64 produced 0/210 successes
  under injection and 18/210 when asked directly. Leetspeak is followed directly (82/145) but
  rarely through a document (5/145).
- **Goals differ strongly.** Phishing links were followed under injection in 4/55 unobfuscated
  cases but in 34/55 when asked directly. In the other 51 injected replies the fictional host
  does not appear at all, so this is not a partial-match problem of the URL oracle. Tool calls are
  also rarely made under injection (11/75), while content manipulation and refusal goals succeed
  most often.
- **Shorter contexts were attacked more successfully** (short 63/245, long 29/230). Position
  made little difference.
- **Language:** English and Turkish rates overlap (unobfuscated en 67/190, tr 58/205). The run
  does not show a clear language effect.
- **Trust boundary:** the identical text placed in the user channel (`authorized_twin`) is
  followed more often than when it arrives in retrieved content (e.g. gemma3 54/150 vs 36/150),
  but far less often than when sent on its own. The twin is embedded in a long document, so it
  does not measure pure instruction-following.
- **Utility is barely affected.** Answer containment changes by at most 3 of 76 English records
  between clean and attacked inputs.

## Comparison with EXP-003 (v0)

This is not a controlled comparison: the dataset (v0 → v1), obfuscation mix, QC version and
token limit (400 → 1,024) all changed together.

| Model | ASR_targeted v0 → v1 | MR v0 → v1 | Truncated v0 → v1 |
|---|---|---|---|
| gemma3:4b | 14 → 36 /150 | 13/58 → 36/104 | 3 → 2 |
| llama3.1:8b | 10 → 19 /150 | 0/12 → 8/40 | 8 → 2 |
| llama3 | 5 → 12 /150 | 3/33 → 7/58 | 18 → 3 |
| mistral | 13 → 38 /150 | 13/60 → 35/103 | 275 → 102 |
| qwen3:8b | 15 → 25 /150 | 12/59 → 25/98 | 8 → 6 |

The higher v1 ASR is mostly explained by the larger share of unobfuscated families (79 vs 31)
and the removal of precondition-gated instructions. The longer token limit removed most
truncation except mistral's loops.

## Limitations

- Pilot scale, one repeat, temperature 0; the five models are small local models. The numbers
  describe this setup and support no general model ranking.
- Attack components are model-generated and reused within a split (up to 6 families each).
- Utility is measured on English records only (76 per model); Turkish carriers have no
  reference answers.
- mistral's truncated replies make its rates lower bounds.
- 004a's 700 responses are reused inside 004b (see header), so 004a and 004b are not independent
  samples.
