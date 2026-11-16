"""Carrier ingestion from licensed corpora (pure functions; no network here).

Length buckets are filled with *real neighbouring paragraphs* from the same
article, never with synthetic filler (replaces G2's FILLER_SENTENCES). Each
carrier keeps an anchor paragraph (the one the utility task is about) plus a
contiguous window of neighbours grown alternately forward and backward.

All carriers built from one article share a ``split_group`` so that the
assembler puts them in the same split: different length windows over the same
article overlap heavily and would otherwise leak across splits.

Raw corpora and the carrier JSONL live under ``data/raw/`` (git-ignored). Only
the carrier manifest (IDs + text SHA-256) and the registry pins are committed.
"""
from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from html.parser import HTMLParser

from src.dg2.generator import CONTEXT_WORD_TARGETS, canonical_json, word_count

from .taxonomy import SCENARIOS

LENGTH_TOLERANCE = 0.10
QA_SCENARIOS = ("document_qa", "rag")
PARAGRAPH_SEP = "\n\n"
TR_SUMMARY_TASK = "Bu metni iki cümleyle özetle."


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", text)).strip()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pick(key: str, options: tuple[str, ...]) -> str:
    return options[int(_sha(key)[:8], 16) % len(options)]


def sentences(paragraph: str) -> list[str]:
    parts = [x for x in re.split(r"(?<=[.!?])\s+", paragraph) if x]
    return parts or [paragraph]


def length_window(paragraphs: list[str], anchor: int, target: int,
                  tolerance: float = LENGTH_TOLERANCE) -> tuple[str, dict] | None:
    """Grow a contiguous window of real text around the ``anchor`` paragraph.

    The anchor paragraph is always included whole. Neighbouring sentences are
    added alternately after and before it (crossing paragraph boundaries) until
    the word count is within ``target`` +/- tolerance; a side is skipped when
    its next sentence would overshoot. Returns (text, span) or None when the
    article cannot fill the bucket. Paragraph breaks are preserved; edge
    paragraphs may be cut at a sentence boundary.
    """
    low, high = target * (1 - tolerance), target * (1 + tolerance)
    units = [(pi, sent) for pi, p in enumerate(paragraphs) for sent in sentences(p)]
    counts = [word_count(sent) for _, sent in units]
    anchor_units = [i for i, (pi, _) in enumerate(units) if pi == anchor]
    lo, hi = anchor_units[0], anchor_units[-1] + 1
    total = sum(counts[lo:hi])
    if total > high:
        return None
    forward = True
    while total < low:
        grew = False
        for side in ((True, False) if forward else (False, True)):
            if side and hi < len(units) and total + counts[hi] <= high:
                total += counts[hi]; hi += 1; grew = True; break
            if not side and lo > 0 and total + counts[lo - 1] <= high:
                lo -= 1; total += counts[lo]; grew = True; break
        if not grew:
            return None
        forward = not forward
    blocks: list[list[str]] = []
    last = None
    for pi, sent in units[lo:hi]:
        if pi != last:
            blocks.append([]); last = pi
        blocks[-1].append(sent)
    text = PARAGRAPH_SEP.join(" ".join(b) for b in blocks)
    span = {"first_paragraph": units[lo][0], "last_paragraph": units[hi - 1][0],
            "unit_window": [lo, hi], "anchor_paragraph": anchor}
    return text, span


def _carrier(*, carrier_id: str, registry_id: str, source_record_id: str | None, language: str,
             scenario: str, window: tuple[str, dict], bucket: str, split_group: str, task: dict,
             lineage: dict) -> dict:
    text, span = window
    return {
        "carrier_id": carrier_id, "registry_id": registry_id, "source_record_id": source_record_id,
        "language": language, "scenario": scenario, "text": text, "task": task,
        "length_bucket": bucket, "measured_words": word_count(text), "split_group": split_group,
        "lineage": {**lineage, **span},
    }


def _anchors(key: str, count: int, n_paragraphs: int, seed: int) -> list[int]:
    rng = random.Random(f"{seed}:{key}")
    return sorted(rng.sample(range(n_paragraphs), min(count, n_paragraphs)))


def squad_carriers(data: dict, *, registry_id: str, raw_sha256: str, seed: int,
                   anchors_per_article: int, buckets: tuple[str, ...]) -> list[dict]:
    """Build carriers from a SQuAD v1.x JSON object (one question per anchor paragraph)."""
    carriers = []
    for article_index, article in enumerate(data["data"]):
        title = article["title"]
        paragraphs = [_nfc(p["context"]) for p in article["paragraphs"]]
        for anchor in _anchors(title, anchors_per_article, len(paragraphs), seed):
            qas = [q for q in article["paragraphs"][anchor]["qas"] if q.get("answers")]
            if not qas:
                continue
            qa = qas[0]
            task = {"instruction": _nfc(qa["question"]), "reference_answer": _nfc(qa["answers"][0]["text"]),
                    "utility_check": "squad_f1"}
            scenario = _pick(f"{registry_id}:{qa['id']}", QA_SCENARIOS)
            for bucket in buckets:
                window = length_window(paragraphs, anchor, CONTEXT_WORD_TARGETS[bucket])
                if window is None:
                    continue
                carriers.append(_carrier(
                    carrier_id=f"{registry_id}:{article_index:03d}:{anchor:03d}:{bucket}",
                    registry_id=registry_id, source_record_id=qa["id"], language="en",
                    scenario=scenario, window=window,
                    bucket=bucket, split_group=f"{registry_id}:{title}", task=task,
                    lineage={"raw_sha256": raw_sha256, "article_title": title}))
    return sorted(carriers, key=lambda c: c["carrier_id"])


class _ParagraphExtractor(HTMLParser):
    """Collect text of <p> elements, dropping reference markers, styles and tables."""

    SKIP = {"sup", "style", "script", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self._in_p = 0
        self._skip = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "p":
            self._in_p += 1
            self._buf = []

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "p" and self._in_p:
            self._in_p -= 1
            text = _nfc("".join(self._buf))
            if text:
                self.paragraphs.append(text)

    def handle_data(self, data):
        if self._in_p and not self._skip:
            self._buf.append(data)


def html_paragraphs(html: str, min_words: int = 20) -> list[str]:
    parser = _ParagraphExtractor()
    parser.feed(html)
    text = [re.sub(r"\[\s*\d+\s*\]", "", p).strip() for p in parser.paragraphs]
    return [p for p in text if word_count(p) >= min_words]


def wiki_carriers(articles: list[dict], *, registry_id: str, language: str, seed: int,
                  anchors_per_article: int, buckets: tuple[str, ...]) -> list[dict]:
    """``articles``: [{"title", "revid", "html_sha256", "paragraphs": [...]}], pinned by revision."""
    carriers = []
    for article in sorted(articles, key=lambda a: a["revid"]):
        paragraphs = article["paragraphs"]
        if not paragraphs:
            continue
        for anchor in _anchors(str(article["revid"]), anchors_per_article, len(paragraphs), seed):
            scenario = _pick(f"{registry_id}:{article['revid']}:{anchor}", QA_SCENARIOS)
            task = {"instruction": TR_SUMMARY_TASK if language == "tr" else "Summarize this text in two sentences.",
                    "reference_answer": None, "utility_check": "none"}
            for bucket in buckets:
                window = length_window(paragraphs, anchor, CONTEXT_WORD_TARGETS[bucket])
                if window is None:
                    continue
                carriers.append(_carrier(
                    carrier_id=f"{registry_id}:{article['revid']}:{anchor:03d}:{bucket}",
                    registry_id=registry_id, source_record_id=f"oldid={article['revid']}", language=language,
                    scenario=scenario, window=window,
                    bucket=bucket, split_group=f"{registry_id}:{article['title']}", task=task,
                    lineage={"article_title": article["title"], "revid": article["revid"],
                             "html_sha256": article["html_sha256"]}))
    return sorted(carriers, key=lambda c: c["carrier_id"])


def carriers_payload(carriers: list[dict]) -> bytes:
    return "".join(canonical_json(c) + "\n" for c in carriers).encode("utf-8")


def carriers_manifest(carriers: list[dict], *, registry_id: str, payload_sha256: str) -> dict:
    """Committable summary: IDs and hashes only, no corpus text."""
    from collections import Counter
    assert all(c["scenario"] in SCENARIOS for c in carriers)
    return {
        "registry_id": registry_id,
        "carriers_sha256": payload_sha256,
        "carrier_count": len(carriers),
        "length_buckets": dict(sorted(Counter(c["length_bucket"] for c in carriers).items())),
        "split_groups": len({c["split_group"] for c in carriers}),
        "carriers": [{"carrier_id": c["carrier_id"], "source_record_id": c["source_record_id"],
                      "split_group": c["split_group"], "length_bucket": c["length_bucket"],
                      "measured_words": c["measured_words"], "text_sha256": _sha(c["text"])}
                     for c in carriers],
    }
