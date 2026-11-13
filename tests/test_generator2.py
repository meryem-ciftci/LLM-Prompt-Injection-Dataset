import json
import tempfile
import unittest
from pathlib import Path

from src.dg2.generator import generate, read_jsonl, split_for, validate, write_release


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "data" / "calibration" / "Calibration_Records_v1.jsonl"
CONFIG = {"seed": 20261113, "pair_families": 40, "hard_benign": 20,
          "split_ratios": {"train": 0.7, "validation": 0.15, "test": 0.15}}


class Generator2Tests(unittest.TestCase):
    def test_expected_size_and_labels(self):
        rows = generate(CONFIG, CALIBRATION)
        self.assertEqual(len(rows), 100)
        self.assertEqual(sum(r["label"] == "injection" for r in rows), 40)
        self.assertEqual(sum(r["label"] == "benign" for r in rows), 60)
        self.assertEqual(sum(r["language"] == "tr" for r in rows), 50)
        self.assertEqual(sum(r["language"] == "en" for r in rows), 50)

    def test_deterministic_generation(self):
        self.assertEqual(generate(CONFIG, CALIBRATION), generate(CONFIG, CALIBRATION))

    def test_unique_ids(self):
        rows = generate(CONFIG, CALIBRATION)
        self.assertEqual(len(rows), len({r["record_id"] for r in rows}))

    def test_trust_boundary_pairs_share_family_and_text(self):
        rows = generate(CONFIG, CALIBRATION)
        pairs = {}
        for row in rows:
            if row["pair_id"]:
                pairs.setdefault(row["pair_id"], []).append(row)
        self.assertEqual(len(pairs), 40)
        for members in pairs.values():
            self.assertEqual({r["label"] for r in members}, {"injection", "benign"})
            self.assertEqual(len({r["carrier_text"] for r in members}), 1)
            self.assertEqual(len({r["family_id"] for r in members}), 1)

    def test_span_round_trip(self):
        for row in generate(CONFIG, CALIBRATION):
            for span in row["injection_spans"]:
                self.assertEqual(row["carrier_text"][span["start"]:span["end"]], span["text"])

    def test_family_disjoint_splits(self):
        rows = generate(CONFIG, CALIBRATION)
        family_splits = {}
        for row in rows:
            family_splits.setdefault(row["family_id"], set()).add(row["split"])
        self.assertTrue(all(len(v) == 1 for v in family_splits.values()))

    def test_validation_accepts_generated_data(self):
        self.assertEqual(validate(generate(CONFIG, CALIBRATION)), [])

    def test_validation_rejects_corrupt_span(self):
        rows = generate(CONFIG, CALIBRATION)
        attack = next(r for r in rows if r["label"] == "injection")
        attack["injection_spans"][0]["start"] += 1
        self.assertTrue(any("span round-trip" in e for e in validate(rows)))

    def test_validation_rejects_broken_pair(self):
        rows = generate(CONFIG, CALIBRATION)
        paired = next(r for r in rows if r["pair_id"])
        paired["carrier_text"] += " changed"
        self.assertTrue(any("carrier_text differs" in e for e in validate(rows)))

    def test_stable_split_function(self):
        ratios = CONFIG["split_ratios"]
        self.assertEqual(split_for("FAM-X", 42, ratios), split_for("FAM-X", 42, ratios))

    def test_release_round_trip_and_manifest(self):
        rows = generate(CONFIG, CALIBRATION)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dataset.jsonl"
            manifest = write_release(rows, output, CONFIG)
            self.assertEqual(read_jsonl(output), rows)
            self.assertEqual(manifest["record_count"], 100)
            saved = json.loads(output.with_suffix(".manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["sha256"], manifest["sha256"])


if __name__ == "__main__":
    unittest.main()

