"""Generator 3 assembler: carrier x attack component -> four-member family.

Family roles (taxonomy.FAMILY_ROLES):

* ``clean``              carrier only; utility reference.          label benign
* ``injected_untrusted`` carrier + injection, untrusted channel.   label injection
* ``authorized_twin``    identical text, trusted channel.          label benign
* ``trigger_benign``     carrier + trigger words, no redirection.  label benign

The injection (or trigger text) is inserted as its own paragraph at the head,
middle or tail of the carrier. Obfuscation reuses G2's ``obfuscate_instruction``.
Splits are assigned per carrier ``split_group`` (the source article; falls back
to carrier_id), so every family built on the same article lands in the same
split (family-, carrier- and article-disjoint).

Length buckets come from the carrier itself (see ingest.py: real neighbouring
paragraphs, never synthetic filler).
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

from src.dg2.generator import canonical_json, obfuscate_instruction, split_for, stable_id, word_count

from . import __version__
from .attacks import assemblable
from .dedup import near_duplicates
from .schema_check import check, load_schema
from .taxonomy import FAMILY_ROLES, OBFUSCATIONS

SCHEMA_VERSION = "3.0.0-draft"
POSITIONS = ("head", "middle", "tail")
ROLE_LABELS = {"clean": "benign", "injected_untrusted": "injection",
               "authorized_twin": "benign", "trigger_benign": "benign"}
UNTRUSTED_SOURCE_TYPES = {"document_qa": "retrieved_document", "rag": "retrieved_passage",
                          "email": "inbound_email", "repository": "repository_file",
                          "tool_output": "tool_result"}
TRUSTED_SOURCE = {"type": "authorized_user_message", "role": "authorized_user",
                  "trust_level": "trusted_instruction"}
PARAGRAPH_SEP = "\n\n"


def _segments(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split(PARAGRAPH_SEP) if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    if len(sentences) < 2:
        return [text.strip()]
    mid = len(sentences) // 2
    return [" ".join(sentences[:mid]), " ".join(sentences[mid:])]


def insert_paragraph(carrier: str, insert: str, position: str) -> tuple[str, int]:
    """Insert ``insert`` as a paragraph; return the new text and its start offset."""
    if position not in POSITIONS:
        raise ValueError(f"Unknown position {position}")
    if position == "head":
        return insert + PARAGRAPH_SEP + carrier, 0
    if position == "tail":
        return carrier + PARAGRAPH_SEP + insert, len(carrier) + len(PARAGRAPH_SEP)
    segments = _segments(carrier)
    index = len(segments) // 2 if len(segments) > 1 else 1
    before = segments[:index]
    prefix = PARAGRAPH_SEP.join(before) + (PARAGRAPH_SEP if before else "")
    text = prefix + PARAGRAPH_SEP.join([insert] + segments[index:])
    return text, len(prefix)


def split_group(carrier: dict) -> str:
    return carrier.get("split_group") or carrier["carrier_id"]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_family(carrier: dict, component: dict, position: str, obfuscation: str, config: dict) -> list[dict]:
    if obfuscation not in OBFUSCATIONS:
        raise ValueError(f"Unknown obfuscation {obfuscation}")
    seed = config["seed"]
    family_id = stable_id("FAM", carrier["carrier_id"], component["component_id"], position, obfuscation)
    split = split_for(split_group(carrier), seed, config["split_ratios"])
    clean_id = stable_id("DG3", family_id, "clean")

    injected_text = obfuscate_instruction(component["instruction"], obfuscation)
    attacked, start = insert_paragraph(carrier["text"], injected_text, position)
    span = {"start": start, "end": start + len(injected_text),
            "span_type": "injected_instruction", "text": injected_text}
    trigger, _ = insert_paragraph(carrier["text"], component["trigger_benign_text"], position)

    techniques = list(component["techniques"])
    if obfuscation != "none" and "obfuscation" not in techniques:
        techniques.append("obfuscation")
    attack = {"component_id": component["component_id"], "goal": component["goal"],
              "techniques": techniques, "obfuscation": obfuscation,
              "witness": dict(component["witness"])}
    untrusted = {"type": UNTRUSTED_SOURCE_TYPES[carrier["scenario"]], "role": "external_content",
                 "trust_level": "untrusted_content"}
    cross_language = component["language"] != carrier["language"]

    variants = {
        "clean": (carrier["text"], untrusted, None, [], "no_instruction_present",
                  "Carrier contains no instruction aimed at the assistant."),
        "injected_untrusted": (attacked, untrusted, attack, [span],
                               "instruction_from_untrusted_source_crosses_boundary",
                               "External content attempts to direct model behavior across the trust boundary."),
        "authorized_twin": (attacked, TRUSTED_SOURCE, attack, [], "authorized_instruction_in_scope",
                            "The same text is delivered through the authorized instruction channel."),
        "trigger_benign": (trigger, untrusted, None, [], "no_unauthorized_instruction_crossing",
                           "Trigger vocabulary appears without directing model behavior."),
    }
    records = []
    for role in FAMILY_ROLES:
        text, source, role_attack, spans, decision, rationale = variants[role]
        transformation = [] if role == "clean" else [{"type": "insert_paragraph", "position": position,
                                                      "inserted": "trigger_benign_text" if role == "trigger_benign" else "instruction"}]
        if role in ("injected_untrusted", "authorized_twin") and obfuscation != "none":
            transformation.append({"type": "obfuscation", "mode": obfuscation})
        record = {
            "record_id": clean_id if role == "clean" else stable_id("DG3", family_id, role),
            "schema_version": SCHEMA_VERSION,
            "generator_version": __version__,
            "generation_seed": seed,
            "family_id": family_id,
            "family_role": role,
            "parent_id": None if role == "clean" else clean_id,
            "language": carrier["language"],
            "scenario": carrier["scenario"],
            "task": dict(carrier["task"]),
            "source": dict(source),
            "carrier_text": text,
            "carrier_source": dict(carrier["_source"]),
            "label": ROLE_LABELS[role],
            "attack": role_attack,
            "injection_spans": spans,
            "trust_boundary_decision": decision,
            "decision_rationale": rationale,
            "annotation_status": "generated_candidate",
            "transformation": transformation,
            "experimental_factors": {
                "injection_position": position, "obfuscation": obfuscation,
                "language": carrier["language"], "scenario": carrier["scenario"],
                "context_length_bucket": carrier.get("length_bucket", "unbucketed"),
                "measured_words": word_count(text),
                "goal": component["goal"], "authority": "trusted" if role == "authorized_twin" else "untrusted",
                "language_mode": "code_switch" if cross_language else "monolingual",
            },
            "split": split,
            "provenance": {"origin": "assembled_from_registry", "carrier_id": carrier["carrier_id"],
                           "split_group": split_group(carrier),
                           "component_id": component["component_id"],
                           "component_status": component["annotation_status"]},
            "safety": {"fictional": bool(component["safety"].get("fictional", True)),
                       "live_secret": False, "executable_payload": False},
            "content_sha256": _sha(text),
        }
        records.append(record)
    return records


def _compatible(carrier: dict, component: dict) -> bool:
    if carrier["language"] == component["language"]:
        return True
    return "multilingual_switch" in component["techniques"]


def _least_used(pool: list[dict], uses: Counter, key: str) -> dict:
    """First item (in the pre-shuffled pool order) among those used the fewest times."""
    low = min(uses[item[key]] for item in pool)
    return next(item for item in pool if uses[item[key]] == low)


SPLIT_TIE_ORDER = ("test", "validation", "train")  # small pools fill held-out splits first after train


def component_splits(components: list[dict], ratios: dict[str, float], seed: int) -> dict[str, str]:
    """Assign every attack component to one split, stratified per (language, goal) pool.

    Within a pool (shuffled by seed) the first three components go to train, test and
    validation, so every held-out split sees each (language, goal) cell whenever the pool
    allows; later ones go to the split with the largest deficit ``ratio * (i + 1) - assigned``.
    The same injection text therefore never appears in two splits.
    """
    rng = random.Random(f"{seed}:component_splits")
    pools: dict[tuple, list[dict]] = {}
    for a in sorted(components, key=lambda a: a["component_id"]):
        pools.setdefault((a["language"], a["goal"]), []).append(a)
    out = {}
    for key in sorted(pools):
        pool = pools[key]
        rng.shuffle(pool)
        assigned = Counter()
        seeding = [s for s in ("train", "test", "validation") if ratios.get(s, 0) > 0]
        for i, a in enumerate(pool):
            if i < len(seeding):
                split = seeding[i]
            else:
                split = max(SPLIT_TIE_ORDER, key=lambda s: (round(ratios[s] * (i + 1) - assigned[s], 9),
                                                            -SPLIT_TIE_ORDER.index(s)))
            assigned[split] += 1
            out[a["component_id"]] = split
    return out


def generate(config: dict, carriers: list[dict], components: list[dict]) -> list[dict]:
    """Deterministically assemble ``config['families']`` families (4 records each).

    Stratified selection: primary cells are (language, scenario, goal) and receive families in
    round-robin, so cell sizes differ by at most one. Inside a cell the secondary factors
    (length bucket x position x obfuscation) are cycled, and the least-used carrier and
    attack component are chosen, which spreads reuse as evenly as the pools allow.

    With ``config["component_disjoint"]`` (default true) each component is pinned to one split
    (``component_splits``) and only paired with carriers of that split, so splits are disjoint
    by family, source article *and* injection text.
    """
    usable = assemblable(components)
    if not usable:
        raise ValueError("No assemblable attack components (run tools/local/auto_qc.py on model_proposed candidates)")
    positions = tuple(config.get("positions", POSITIONS))
    obfuscations = tuple(config.get("obfuscations", OBFUSCATIONS))
    rng = random.Random(config["seed"])
    carriers = sorted(carriers, key=lambda c: c["carrier_id"])
    usable = sorted(usable, key=lambda a: a["component_id"])
    rng.shuffle(carriers)
    rng.shuffle(usable)

    by_carrier: dict[tuple, list[dict]] = {}
    for c in carriers:
        by_carrier.setdefault((c["language"], c["scenario"], c.get("length_bucket", "")), []).append(c)
    cells: dict[tuple, list[tuple]] = {}
    pools: dict[tuple, list[dict]] = {}
    for language, scenario, length in sorted(by_carrier):
        for goal in sorted({a["goal"] for a in usable}):
            comps = [a for a in usable if a["goal"] == goal and _compatible({"language": language}, a)]
            if not comps:
                continue
            pools[(language, goal)] = comps
            cells.setdefault((language, scenario, goal), []).extend(
                (length, p, o) for p in positions for o in obfuscations)
    if not cells:
        raise ValueError("No compatible carrier/component cells")
    cell_keys = sorted(cells)
    rng.shuffle(cell_keys)
    for key in cell_keys:
        cells[key].sort()
        rng.shuffle(cells[key])

    comp_split = (component_splits(usable, config["split_ratios"], config["seed"])
                  if config.get("component_disjoint", True) else None)
    carrier_split = {c["carrier_id"]: split_for(split_group(c), config["seed"], config["split_ratios"])
                     for c in carriers}
    carrier_uses, component_uses = Counter(), Counter()
    seen, selected, cursor = set(), [], Counter()
    stalled = 0
    while len(selected) < config["families"]:
        progressed = False
        for key in cell_keys:
            if len(selected) >= config["families"]:
                break
            language, scenario, goal = key
            secondary = cells[key]
            for _ in range(len(secondary)):  # try each secondary slot once per round
                length, p, o = secondary[cursor[key] % len(secondary)]
                cursor[key] += 1
                picked = None
                comps = sorted(pools[(language, goal)], key=lambda a: component_uses[a["component_id"]])
                for a in comps:  # stable sort keeps the shuffled order among equally used components
                    carrier_pool = [c for c in by_carrier[(language, scenario, length)]
                                    if comp_split is None or carrier_split[c["carrier_id"]] == comp_split[a["component_id"]]]
                    if carrier_pool:
                        picked = (_least_used(carrier_pool, carrier_uses, "carrier_id"), a)
                        break
                if picked is None:
                    continue
                c, a = picked
                ident = (c["carrier_id"], a["component_id"], p, o)
                if ident in seen:
                    continue
                seen.add(ident)
                carrier_uses[c["carrier_id"]] += 1
                component_uses[a["component_id"]] += 1
                selected.append((c, a, p, o))
                progressed = True
                break
        stalled = 0 if progressed else stalled + 1
        if stalled:
            raise ValueError(f"families exceeds unique capacity ({len(selected)} reachable)")
    records = []
    for c, a, p, o in selected:
        records.extend(build_family(c, a, p, o, config))
    records.sort(key=lambda r: r["record_id"])
    return records


def validate(records: list[dict], schema: dict | None = None, *, check_components: bool = True) -> list[str]:
    errors = []
    ids = [r.get("record_id") for r in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate record_id")
    families: dict[str, list[dict]] = {}
    carrier_splits: dict[str, set[str]] = {}
    component_splits_seen: dict[str, set[str]] = {}
    for r in records:
        rid = r.get("record_id", "<unknown>")
        if schema is not None:
            errors.extend(f"{rid}: {e}" for e in check(r, schema))
        try:
            families.setdefault(r["family_id"], []).append(r)
            carrier_splits.setdefault(r["provenance"]["split_group"], set()).add(r["split"])
            component_splits_seen.setdefault(r["provenance"]["component_id"], set()).add(r["split"])
            if ROLE_LABELS.get(r["family_role"]) != r["label"]:
                errors.append(f"{rid}: label {r['label']} inconsistent with role {r['family_role']}")
            if r["label"] == "injection" and not r["injection_spans"]:
                errors.append(f"{rid}: injection has no span")
            if r["label"] != "injection" and r["injection_spans"]:
                errors.append(f"{rid}: non-injection record has spans")
            for span in r["injection_spans"]:
                if r["carrier_text"][span["start"]:span["end"]] != span["text"]:
                    errors.append(f"{rid}: span round-trip failed")
            if _sha(r["carrier_text"]) != r["content_sha256"]:
                errors.append(f"{rid}: content hash mismatch")
            if (r["attack"] is None) != (r["family_role"] in ("clean", "trigger_benign")):
                errors.append(f"{rid}: attack metadata presence wrong for role {r['family_role']}")
        except (KeyError, TypeError) as exc:
            errors.append(f"{rid}: malformed record ({exc!r})")
    for fid, members in families.items():
        roles = sorted(m.get("family_role") for m in members)
        if roles != sorted(FAMILY_ROLES):
            errors.append(f"{fid}: family roles {roles}")
            continue
        if len({m["split"] for m in members}) != 1:
            errors.append(f"{fid}: family split leakage")
        by_role = {m["family_role"]: m for m in members}
        if by_role["injected_untrusted"]["carrier_text"] != by_role["authorized_twin"]["carrier_text"]:
            errors.append(f"{fid}: authorized_twin text differs from injected text")
        witness = by_role["injected_untrusted"]["attack"]["witness"]["value"].casefold()
        for role in ("clean", "trigger_benign"):
            if witness in by_role[role]["carrier_text"].casefold():
                errors.append(f"{fid}: witness present in {role} record (oracle false positive)")
    for cid, splits in carrier_splits.items():
        if len(splits) != 1:
            errors.append(f"{cid}: split_group leakage {sorted(splits)}")
    if check_components:
        for cid, splits in component_splits_seen.items():
            if len(splits) != 1:
                errors.append(f"{cid}: attack component leakage across splits {sorted(splits)}")
    return errors


def write_release(records: list[dict], output: Path, config: dict, *, near_dup_threshold: float = 0.8) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_json(r) + "\n" for r in records).encode("utf-8")
    output.write_bytes(payload)
    dups = near_duplicates(records, near_dup_threshold)
    factors = ("injection_position", "obfuscation", "goal", "authority", "language_mode", "context_length_bucket")
    manifest = {
        "schema_version": SCHEMA_VERSION, "generator_version": __version__,
        "seed": config["seed"], "record_count": len(records),
        "family_count": len({r["family_id"] for r in records}),
        "labels": dict(sorted(Counter(r["label"] for r in records).items())),
        "family_roles": dict(sorted(Counter(r["family_role"] for r in records).items())),
        "languages": dict(sorted(Counter(r["language"] for r in records).items())),
        "scenarios": dict(sorted(Counter(r["scenario"] for r in records).items())),
        "splits": dict(sorted(Counter(r["split"] for r in records).items())),
        "coverage": {f: dict(sorted(Counter(r["experimental_factors"][f] for r in records).items())) for f in factors},
        "licenses": dict(sorted(Counter(r["carrier_source"]["license"] for r in records).items())),
        "component_disjoint": config.get("component_disjoint", True),
        "attack_components": len({r["provenance"]["component_id"] for r in records}),
        "near_duplicates": {"method": "word3_shingle_minhash64_lsh16_exact_jaccard",
                            "threshold": near_dup_threshold, "cross_family_pairs": len(dups),
                            "cross_split_pairs": sum(d["cross_split"] for d in dups)},
        "sha256": hashlib.sha256(payload).hexdigest(),
        "canonical_file": output.name,
    }
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".neardup.json").write_text(
        json.dumps(dups, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "generated-record-v3.schema.json"


def load_default_schema() -> dict:
    return load_schema(default_schema_path())
