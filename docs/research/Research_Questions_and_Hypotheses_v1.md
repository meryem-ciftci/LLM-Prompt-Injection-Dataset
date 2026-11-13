# Research Questions and Hypotheses v1

**Frozen before Generator 2.2 confirmatory evaluation · 2026-11-13**

The completed Generator 2.0 experiment is exploratory. Its outcomes were observed before this document was frozen and must not be presented as confirmatory evidence for the hypotheses below. Confirmatory tests must use a new, family-disjoint Generator 2.2 test release and a preregistered analysis configuration.

## Primary research question

Do prompt-injection detectors respond to instruction authority and trust boundaries, or primarily to lexical attack cues?

## H1 — Context metadata

Explicit source-authority and trust-boundary metadata improves prompt-injection detection MCC and injection recall compared with a text-only condition, without materially increasing benign false-positive rate.

**Null H1₀:** There is no difference between text-only and context-aware conditions in paired decisions.

**Primary comparison:** Exact paired McNemar test per model, Holm-adjusted across the model panel. Effect sizes: MCC difference, recall difference, FPR difference, and matched-pair exact accuracy.

## H2 — Language

Detection performance differs between Turkish and English after controlling for label, family, carrier format, context length, and obfuscation.

**Primary measurements:** language-specific MCC, recall, FPR, and bootstrap 95% confidence intervals. This is a difference hypothesis; no direction is assumed before confirmatory evaluation.

## H3 — Context length and position

Increasing context length and moving an injected instruction away from salient boundaries reduces injection recall for at least one evaluated model family.

**Primary factors:** short/medium/long proxy bucket and head/middle/tail/only position. Actual model-specific `prompt_eval_count` is the authoritative token measurement; generator proxy counts are construction controls.

## H4 — Obfuscation

Controlled obfuscation changes detection recall relative to plain instructions, with effects varying by model family.

**Lanes:** none, Base64 with explicit decode directive, character splitting with explicit reconstruction directive, and leetspeak. Each transformation retains lineage and exact transformed spans.

## H5 — Over-defense

Models with higher injection recall may incur higher benign false-positive rates on hard-benign and authorized-twin records.

**Measurements:** recall, FPR, Brier score, ECE, and pair-level exact accuracy. Accuracy alone is not a primary security metric.

## Confirmatory protocol

1. Freeze generator, schema, calibration pack, config, model digests, prompt, and analysis code hashes.
2. Complete independent bilingual human annotation and adjudication before model evaluation.
3. Exclude unresolved borderline records from binary headline metrics.
4. Use family-disjoint splits. Do not tune prompts or thresholds on the frozen test split.
5. Run both `text_only` and `context_aware` views with identical model parameters.
6. Report all predeclared metrics and comparisons, including negative results.
7. Treat additional analyses discovered after seeing Generator 2.2 outcomes as exploratory.

