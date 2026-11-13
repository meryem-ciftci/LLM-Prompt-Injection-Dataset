import unittest

from src.dg2.evaluator import binary_metrics, select_records, stable_run_id


class EvaluatorTests(unittest.TestCase):
    def test_binary_metrics(self):
        rows = [
            {"status": "ok", "gold_label": "injection", "predicted_label": "injection", "latency_ms": 10},
            {"status": "ok", "gold_label": "injection", "predicted_label": "benign", "latency_ms": 20},
            {"status": "ok", "gold_label": "benign", "predicted_label": "injection", "latency_ms": 30},
            {"status": "ok", "gold_label": "benign", "predicted_label": "benign", "latency_ms": 40},
        ]
        result = binary_metrics(rows)
        self.assertEqual((result["tp"], result["tn"], result["fp"], result["fn"]), (1, 1, 1, 1))
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["f1"], 0.5)
        self.assertEqual(result["mcc"], 0.0)

    def test_selection_is_stable_and_bounded(self):
        rows = [{"record_id": f"R{i}", "label": "injection" if i % 2 else "benign",
                 "language": "tr" if i % 3 else "en", "scenario": f"s{i % 4}"} for i in range(30)]
        first = select_records(rows, 11, 42)
        second = select_records(list(reversed(rows)), 11, 42)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 11)

    def test_selection_balances_label_and_language(self):
        rows = []
        for label in ("injection", "benign"):
            for language in ("tr", "en"):
                for i in range(10):
                    rows.append({"record_id": f"{label}-{language}-{i}", "label": label,
                                 "language": language, "scenario": f"s{i % 3}"})
        selected = select_records(rows, 20, 42)
        counts = {(label, language): sum(r["label"] == label and r["language"] == language for r in selected)
                  for label in ("injection", "benign") for language in ("tr", "en")}
        self.assertEqual(set(counts.values()), {5})

    def test_run_id_changes_with_input_mode(self):
        common = ("abc", {"m": "digest"}, 20, 1, 0, 42, 120, 2)
        text_only = stable_run_id(*common, ["text_only"])
        context_aware = stable_run_id(*common, ["context_aware"])
        self.assertNotEqual(text_only, context_aware)


if __name__ == "__main__":
    unittest.main()

