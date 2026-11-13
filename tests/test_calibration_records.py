import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_calibration_pack import build, validate


class CalibrationPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = build()

    def test_builder_validation(self):
        self.assertTrue(validate(self.records))

    def test_balance_and_unique_ids(self):
        self.assertEqual(len(self.records), 60)
        self.assertEqual(len({r["record_id"] for r in self.records}), 60)
        self.assertEqual({x: sum(r["label"] == x for r in self.records)
                          for x in ("injection", "benign", "borderline")},
                         {"injection": 20, "benign": 20, "borderline": 20})

    def test_span_round_trip(self):
        for r in self.records:
            for s in r["injection_spans"]:
                self.assertEqual(r["carrier_text"][s["start"]:s["end"]], s["text"])

    def test_status_and_safety_policy(self):
        for r in self.records:
            if r["label"] == "borderline":
                self.assertEqual(r["annotation_status"], "adjudication_required")
                self.assertTrue(r["ambiguity_reason"])
            else:
                self.assertEqual(r["annotation_status"], "gold_calibration")
            self.assertTrue(r["safety"]["fictional"])
            self.assertFalse(r["safety"]["live_secret"])
            self.assertFalse(r["provenance"]["contains_real_personal_data"])

    def test_serialized_jsonl_if_present(self):
        path = ROOT / "data" / "calibration" / "Calibration_Records_v1.jsonl"
        if path.exists():
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows, self.records)

    def test_csv_if_present(self):
        path = ROOT / "data" / "calibration" / "Calibration_Records_v1.csv"
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 60)
            by_id = {r["record_id"]: r for r in self.records}
            for row in rows:
                src = by_id[row["record_id"]]
                self.assertEqual(row["carrier_text"], src["carrier_text"])
                self.assertEqual(json.loads(row["injection_spans_json"]), src["injection_spans"])


if __name__ == "__main__":
    unittest.main()

