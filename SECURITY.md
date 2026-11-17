# Security and responsible use

## What this repository contains

The dataset contains prompt-injection text **for defensive research**: evaluating detectors and
measuring how often language models follow injected instructions. It is designed to be
low-risk:

- every URL uses the reserved `.example.invalid` domain;
- canary tokens, phrases and tool names are fictional;
- there are no real credentials, no personal data and no executable payloads. Automatic QC
  rejects candidates containing code-like payloads or non-fictional URLs.

Please use the material only on systems you own or are authorized to test.

## Reporting a vulnerability or a harmful record

If you find a record that contains a real URL, a real secret, personal data or an executable
payload, or a vulnerability in the tooling, **do not open a public issue**. Report it
privately through GitHub's *Report a vulnerability* button (Security tab → Advisories). If
that button is not available, contact a maintainer directly through their GitHub profile.

Please include:

- the file, the `record_id` or `component_id`, and the dataset SHA-256;
- what is wrong and why it is harmful.

We aim to acknowledge reports within 7 days. Confirmed problems are fixed in a new versioned
release, and the affected version is noted in the data card.

## Supported versions

| Version | Supported |
|---|---|
| Generator 3 pilot `dg3_pilot_v1` (current) | Yes |
| Generator 3 pilot `dg3_pilot_v0` | Kept for reproducibility; fixes go into a new release |
| Generator 2.2 (`dataset_v2_2`) | Security fixes only |
