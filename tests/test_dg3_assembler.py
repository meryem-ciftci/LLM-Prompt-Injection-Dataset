import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.dg2.generator import read_jsonl
from src.dg3.assembler import generate, insert_paragraph, load_default_schema, validate, write_release
from src.dg3.attacks import load_components
from src.dg3.dedup import jaccard, near_duplicates, shingles
from src.dg3.schema_check import check
from src.dg3.sources import load_carriers
from src.dg3.taxonomy import FAMILY_ROLES

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dg3"
CONFIG = json.loads((FIXTURES / "config.json").read_text(encoding="utf-8"))


def build(config=CONFIG):
    return generate(config, load_carriers(FIXTURES / "registry.json"),
                    load_components(FIXTURES / "attack_components"))


class AssemblerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = build()
        cls.schema = load_default_schema()

    def test_size_and_family_structure(self):
        self.assertEqual(len(self.records), CONFIG["families"] * 4)
        families = {}
        for r in self.records:
            families.setdefault(r["family_id"], []).append(r["family_role"])
        self.assertEqual(len(families), CONFIG["families"])
        for roles in families.values():
            self.assertEqual(sorted(roles), sorted(FAMILY_ROLES))

    def test_validation_and_schema_pass(self):
        self.assertEqual(validate(self.records, self.schema), [])

    def test_every_record_matches_v3_schema(self):
        for r in self.records:
            self.assertEqual(check(r, self.schema), [], r["record_id"])

    def test_span_round_trip(self):
        injected = [r for r in self.records if r["label"] == "injection"]
        self.assertTrue(injected)
        for r in injected:
            for span in r["injection_spans"]:
                self.assertEqual(r["carrier_text"][span["start"]:span["end"]], span["text"])

    def test_insert_positions(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        for position, expected_start in (("head", 0), ("tail", len(text) + 2)):
            out, start = insert_paragraph(text, "INSERTED", position)
            self.assertEqual(out[start:start + 8], "INSERTED")
            self.assertEqual(start, expected_start)
        out, start = insert_paragraph(text, "INSERTED", "middle")
        self.assertEqual(out, "First paragraph.\n\nINSERTED\n\nSecond paragraph.\n\nThird paragraph.")
        single, start = insert_paragraph("One sentence. Two sentence. Three.", "X", "middle")
        self.assertEqual(single[start], "X")
        self.assertTrue(single.startswith("One sentence."))
        # head/tail never restructure the carrier: removing the insertion restores it exactly
        for position in ("head", "tail"):
            out, start = insert_paragraph("One sentence. Two sentence.", "X", position)
            self.assertEqual((out[:start] + out[start + 1:]).strip(), "One sentence. Two sentence.")

    def test_twin_identical_text_and_witness_absent_from_controls(self):
        families = {}
        for r in self.records:
            families.setdefault(r["family_id"], {})[r["family_role"]] = r
        for fam in families.values():
            self.assertEqual(fam["injected_untrusted"]["carrier_text"], fam["authorized_twin"]["carrier_text"])
            self.assertEqual(fam["authorized_twin"]["source"]["trust_level"], "trusted_instruction")
            witness = fam["injected_untrusted"]["attack"]["witness"]["value"].casefold()
            self.assertNotIn(witness, fam["clean"]["carrier_text"].casefold())
            self.assertNotIn(witness, fam["trigger_benign"]["carrier_text"].casefold())

    def test_model_proposed_components_excluded(self):
        self.assertNotIn("ATK-EN-003", {r["provenance"]["component_id"] for r in self.records})

    def test_carrier_and_family_disjoint_splits(self):
        by_carrier, by_family = {}, {}
        for r in self.records:
            by_carrier.setdefault(r["provenance"]["carrier_id"], set()).add(r["split"])
            by_family.setdefault(r["family_id"], set()).add(r["split"])
        self.assertTrue(all(len(s) == 1 for s in by_carrier.values()))
        self.assertTrue(all(len(s) == 1 for s in by_family.values()))

    def test_validation_rejects_corruption(self):
        cases = {
            "span round-trip": lambda rs: next(r for r in rs if r["label"] == "injection")["injection_spans"][0].__setitem__("start", 1),
            "twin text differs": lambda rs: next(r for r in rs if r["family_role"] == "authorized_twin").__setitem__("carrier_text", "x"),
            "family roles": lambda rs: rs.pop(),
            "oracle false positive": lambda rs: self._leak_witness(rs),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                rows = copy.deepcopy(self.records)
                mutate(rows)
                self.assertTrue(validate(rows), name)

    @staticmethod
    def _leak_witness(rows):
        injected = next(r for r in rows if r["family_role"] == "injected_untrusted")
        clean = next(r for r in rows if r["family_id"] == injected["family_id"] and r["family_role"] == "clean")
        clean["carrier_text"] += " " + injected["attack"]["witness"]["value"]
        clean["content_sha256"] = hashlib.sha256(clean["carrier_text"].encode("utf-8")).hexdigest()


class DeterminismTests(unittest.TestCase):
    def test_same_seed_byte_identical_release(self):
        with tempfile.TemporaryDirectory() as d:
            a = write_release(build(), Path(d) / "a.jsonl", CONFIG)
            b = write_release(build(), Path(d) / "b.jsonl", CONFIG)
            self.assertEqual(a["sha256"], b["sha256"])
            self.assertEqual((Path(d) / "a.jsonl").read_bytes(), (Path(d) / "b.jsonl").read_bytes())
            self.assertEqual(read_jsonl(Path(d) / "a.jsonl"), build())
            self.assertTrue((Path(d) / "a.neardup.json").exists())

    def test_different_seed_changes_selection(self):
        other = {**CONFIG, "seed": CONFIG["seed"] + 1}
        self.assertNotEqual([r["record_id"] for r in build()], [r["record_id"] for r in build(other)])

    def test_capacity_guard(self):
        with self.assertRaisesRegex(ValueError, "capacity"):
            build({**CONFIG, "families": 10_000})


class NearDuplicateTests(unittest.TestCase):
    def test_jaccard_basics(self):
        a = shingles("the quick brown fox jumps over the lazy dog")
        self.assertEqual(jaccard(a, a), 1.0)
        self.assertLess(jaccard(a, shingles("completely different words appear in this sentence")), 0.1)

    def test_detects_cross_family_near_duplicate_and_skips_same_family(self):
        text = " ".join(f"word{i}" for i in range(200))
        records = [
            {"record_id": "A", "family_id": "F1", "split": "train", "carrier_text": text},
            {"record_id": "B", "family_id": "F1", "split": "train", "carrier_text": text},
            {"record_id": "C", "family_id": "F2", "split": "test", "carrier_text": text + " extra tail"},
            {"record_id": "D", "family_id": "F3", "split": "train", "carrier_text": "unrelated short text here"},
        ]
        pairs = {(p["record_a"], p["record_b"]): p for p in near_duplicates(records, 0.8)}
        self.assertNotIn(("A", "B"), pairs)
        self.assertIn(("A", "C"), pairs)
        self.assertTrue(pairs[("A", "C")]["cross_split"])
        self.assertFalse(any("D" in key for key in pairs))


if __name__ == "__main__":
    unittest.main()
