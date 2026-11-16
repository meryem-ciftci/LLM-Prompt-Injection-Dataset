"""Controlled vocabularies for Generator 3.

Each enum value cites the literature it is derived from (see
docs/research/Literature_Map_v2.md). These are design-stage labels; they do not
imply that any attack succeeds against a model. Success is measured separately
by the target-model evaluation artifact.
"""
from __future__ import annotations

# What the injected instruction tries to achieve.
# Basis: Greshake et al. 2023 (threat taxonomy), Zhan et al. 2024 InjecAgent
# (direct harm vs. data stealing), Liu et al. 2024 (target task hijack).
ATTACK_GOALS = (
    "task_hijack",              # replace the authorized task with another
    "content_manipulation",     # bias/alter the answer (e.g. false claim, wrong summary)
    "data_exfiltration",        # leak a fictional canary from context/tools
    "unauthorized_tool_action", # call a tool the user did not request
    "phishing_link",            # insert an attacker URL into the output
    "refusal_dos",              # make the assistant refuse or stall
    "prompt_leak",              # reveal system / hidden instructions
)

# How the injected instruction is constructed.
# Basis: Liu et al. 2024 (naive, escape characters, context ignoring,
# fake completion, combined); Duarte et al. 2026 review (role-play,
# authority claim, obfuscation, multilingual); LLMail-Inject (social engineering).
ATTACK_TECHNIQUES = (
    "naive",
    "escape_separator",
    "context_ignoring",
    "fake_completion",
    "combined",
    "authority_claim",
    "role_play",
    "social_engineering",
    "obfuscation",
    "multilingual_switch",
)

# Obfuscation lanes kept from Generator 2.2 (src/dg2/generator.py OBFUSCATIONS).
OBFUSCATIONS = ("none", "base64", "char_split", "leetspeak")

# Where the untrusted text enters the application.
# Basis: Yi et al. 2023 BIPIA, Zhan et al. 2024 InjecAgent, Debenedetti et al. 2024 AgentDojo.
SCENARIOS = ("document_qa", "rag", "email", "repository", "tool_output")

# Four-member family design (plan section 4).
FAMILY_ROLES = (
    "clean",               # carrier without injection: utility reference
    "injected_untrusted",  # injection in untrusted source -> label injection
    "authorized_twin",     # identical text via trusted channel -> label benign
    "trigger_benign",      # trigger words without redirection -> label benign (NotInject-style)
)

LABELS = ("injection", "benign", "borderline")

# Deterministic success oracle types (Zverev et al. 2024 SEP witness; AgentDojo checks).
WITNESS_TYPES = ("canary_token", "url", "tool_call", "phrase")

ANNOTATION_STATUSES = (
    "model_proposed",       # produced by a local model; never gold
    "generated_candidate",  # deterministic assembly, not yet reviewed
    "single_annotated",
    "adjudicated",
    "gold_calibration",
)
