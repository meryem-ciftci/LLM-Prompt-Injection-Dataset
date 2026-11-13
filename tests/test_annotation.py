import json
import tempfile
import unittest
from pathlib import Path

from src.dg2.annotation import cohen_kappa, export_blind, merge_annotations


ROOT = Path(__file__).resolve().parents[1]


class AnnotationTests(unittest.TestCase):
    def test_kappa_perfect(self):
        self.assertEqual(cohen_kappa(["benign", "injection"], ["benign", "injection"]), 1.0)

    def test_blind_export_hides_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "a.jsonl"
            count = export_blind(ROOT / "data" / "generated" / "dataset_v2.jsonl", output, "annotator-a")
            self.assertGreater(count, 0)
            row = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
            self.assertNotIn("label", {k: v for k, v in row.items() if k != "decision"})
            self.assertIsNone(row["decision"]["label"])

    def test_merge_creates_disagreement_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            record_a = {"record_id": "R1", "annotator_id_hash": "a", "decision": {"label": "benign", "injection_spans": [], "needs_adjudication": False}}
            record_b = {"record_id": "R1", "annotator_id_hash": "b", "decision": {"label": "injection", "injection_spans": [], "needs_adjudication": False}}
            (base / "a.jsonl").write_text(json.dumps(record_a) + "\n", encoding="utf-8")
            (base / "b.jsonl").write_text(json.dumps(record_b) + "\n", encoding="utf-8")
            summary = merge_annotations(base / "a.jsonl", base / "b.jsonl", base / "merged")
            self.assertEqual(summary["adjudication_count"], 1)
            self.assertTrue((base / "merged" / "adjudication_queue.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
