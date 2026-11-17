# Contributing

Thanks for helping improve the dataset. This project is research infrastructure, so the bar
is **reproducibility and honest reporting** rather than feature count.

## Ground rules

1. **No unmeasured numbers.** Never write ASR, F1, FPR, κ or similar figures into docs, PRs
   or commit messages unless they come from a committed result or report file.
2. **No claims of human verification.** Labels are construction labels and attack components
   pass automatic quality control. Do not describe data as human-verified or gold unless a
   documented human study backs it.
3. **Keep the invariants.**
   - Character-offset spans must round-trip.
   - Families keep four members.
   - Splits stay disjoint by article, family and attack component.
   - Provenance and licence checks stay fail-closed.
   - The same seed must give byte-identical output.
4. **Released files are immutable.** Change the generator, then publish a new versioned file
   and manifest. Never edit a released JSONL in place.
5. **Safety.** Attack text must stay fictional:
   - only `*.example.invalid` URLs;
   - canaries and tool names from the generator, no real ones;
   - no real credentials, personal data or executable payloads.

## Development

The core is pure Python (3.10+) with no third-party runtime dependencies.

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m src.dg3 validate data/generated/dg3_pilot_v1.jsonl
```

Scripts that call local models live in `tools/local/` and need [Ollama](https://ollama.com).
Every run pins model digests from `configs/versions.lock.json` and fails closed on a mismatch.
Long runs are resumable; rerunning the same command continues where it stopped.

## Pull requests

- Branch from `main` (`feature/<topic>`) and open a PR. Do not push to `main` directly.
- Add or update tests for any change to generation, QC, scoring or validation.
- If a change alters generated data, regenerate the release, its manifest and the Croissant
  file in the same PR, and say so in the description.
- New experiments must be registered in the README experiment registry **before** they are run.

## Reporting data problems

Use the *Data issue* template for wrong spans, label inconsistencies, licence questions or
leakage between splits. Include the `record_id` and the dataset SHA-256.
