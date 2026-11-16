"""Near-duplicate detection with stdlib MinHash + LSH, verified by exact Jaccard.

Shingles are word n-grams over NFC-normalised, case-folded text. MinHash
candidates are confirmed with exact Jaccard similarity, so the report never
contains a false positive above the threshold (it can only miss pairs that LSH
did not bucket together, which is negligible at the default parameters).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from itertools import combinations

NUM_PERM = 64
BANDS = 16  # 16 bands x 4 rows: ~50% candidate probability at Jaccard ~0.5
_MASK = (1 << 64) - 1


def shingles(text: str, n: int = 3) -> frozenset[str]:
    words = re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold(), flags=re.UNICODE)
    if len(words) < n:
        return frozenset({" ".join(words)}) if words else frozenset()
    return frozenset(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def _hash(shingle: str, salt: int) -> int:
    digest = hashlib.blake2b(shingle.encode("utf-8"), digest_size=8, salt=salt.to_bytes(8, "big")).digest()
    return int.from_bytes(digest, "big") & _MASK


def minhash(sh: frozenset[str], num_perm: int = NUM_PERM) -> tuple[int, ...]:
    if not sh:
        return tuple([_MASK] * num_perm)
    return tuple(min(_hash(s, i) for s in sh) for i in range(num_perm))


def near_duplicates(records: list[dict], threshold: float = 0.8, *, text_key: str = "carrier_text") -> list[dict]:
    """Return record pairs whose shingle Jaccard >= threshold, sorted deterministically.

    Pairs inside the same family are skipped: authorized twins are identical by design.
    """
    shingle_sets = {r["record_id"]: shingles(r[text_key]) for r in records}
    by_id = {r["record_id"]: r for r in records}
    rows_per_band = NUM_PERM // BANDS
    buckets: dict[tuple[int, tuple[int, ...]], list[str]] = {}
    for rid in sorted(shingle_sets):
        sig = minhash(shingle_sets[rid])
        for band in range(BANDS):
            key = (band, sig[band * rows_per_band:(band + 1) * rows_per_band])
            buckets.setdefault(key, []).append(rid)
    candidates = set()
    for ids in buckets.values():
        for a, b in combinations(ids, 2):
            candidates.add((a, b) if a < b else (b, a))
    report = []
    for a, b in sorted(candidates):
        ra, rb = by_id[a], by_id[b]
        if ra.get("family_id") == rb.get("family_id"):
            continue
        score = jaccard(shingle_sets[a], shingle_sets[b])
        if score >= threshold:
            report.append({"record_a": a, "record_b": b, "jaccard": round(score, 4),
                           "cross_split": ra.get("split") != rb.get("split")})
    return report
