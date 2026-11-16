import json
import tempfile
import unittest
from pathlib import Path

from src.dg3.agreement import REPORT_SCOPE, agreement_report, cohen_kappa, span_iou
from src.dg3.assembler import component_splits


def record(rid, role, label, spans=()):
    return {"record_id": rid, "family_role": role, "label": label, "injection_spans": list(spans)}


def labels(model, mapping):
    return [{"record_id": rid, "model": model, "suggested_label": lab, "suggested_span": span}
            for rid, (lab, span) in mapping.items()]


def write(path: Path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


class KappaTests(unittest.TestCase):
    def test_kappa_values(self):
        self.assertEqual(cohen_kappa(["a", "b"], ["a", "b"]), 1.0)
        self.assertAlmostEqual(cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]), 0.0)
        self.assertIsNone(cohen_kappa([], []))
        self.assertEqual(cohen_kappa(["a", "a"], ["a", "a"]), 1.0)

    def test_span_iou(self):
        self.assertEqual(span_iou({"start": 0, "end": 10}, [{"start": 0, "end": 10}]), 1.0)
        self.assertAlmostEqual(span_iou({"start": 5, "end": 15}, [{"start": 0, "end": 10}]), 5 / 15)
        self.assertEqual(span_iou(None, [{"start": 0, "end": 10}]), 0.0)


class ReportTests(unittest.TestCase):
    def test_report_against_construction_and_between_models(self):
        recs = [record("R1", "injected_untrusted", "injection", [{"start": 0, "end": 10}]),
                record("R2", "authorized_twin", "benign"), record("R3", "clean", "benign"),
                record("R4", "trigger_benign", "benign")]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ds = write(d / "ds.jsonl", recs)
            a = write(d / "a.jsonl", labels("m:a", {"R1": ("injection", {"start": 0, "end": 10}),
                                                    "R2": ("injection", None), "R3": ("benign", None),
                                                    "R4": ("benign", None)}))
            b = write(d / "b.jsonl", labels("m:b", {"R1": ("injection", {"start": 0, "end": 5}),
                                                    "R2": ("benign", None), "R3": ("benign", None),
                                                    "R4": ("borderline", None)}))
            rep = agreement_report(ds, a, b)
        self.assertEqual(rep["scope"], REPORT_SCOPE)
        self.assertEqual(rep["inter_model"]["n"], 4)
        self.assertEqual(rep["vs_construction"]["a"]["by_family_role"]["authorized_twin"]["agreement"], 0.0)
        self.assertEqual(rep["vs_construction"]["b"]["injection_span_char_iou_mean"], 0.5)
        self.assertNotIn("human", json.dumps(rep).lower().replace(REPORT_SCOPE, ""))

    def test_same_model_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ds = write(d / "ds.jsonl", [record("R1", "clean", "benign")])
            a = write(d / "a.jsonl", labels("m:a", {"R1": ("benign", None)}))
            with self.assertRaises(ValueError):
                agreement_report(ds, a, a)


class ComponentSplitTests(unittest.TestCase):
    def test_stratified_and_deterministic(self):
        comps = [{"component_id": f"C{i}", "language": "en", "goal": "task_hijack"} for i in range(5)]
        ratios = {"train": 0.6, "validation": 0.2, "test": 0.2}
        out = component_splits(comps, ratios, 1)
        self.assertEqual(out, component_splits(comps, ratios, 1))
        self.assertEqual(sorted(out.values()), ["test", "train", "train", "train", "validation"])
        three = component_splits(comps[:3], ratios, 1)
        self.assertEqual(sorted(three.values()), ["test", "train", "validation"])


if __name__ == "__main__":
    unittest.main()
