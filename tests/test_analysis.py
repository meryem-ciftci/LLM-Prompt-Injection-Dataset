import tempfile
import unittest
from pathlib import Path

from src.dg2.analysis import (brier_and_ece, exact_mcnemar_p, holm_adjust,
                              percentile, wilson_interval, write_analysis)


class AnalysisTests(unittest.TestCase):
    def test_wilson_interval_contains_observed_rate(self):
        low, high = wilson_interval(80, 100)
        self.assertLess(low, 0.8)
        self.assertGreater(high, 0.8)

    def test_percentile(self):
        self.assertEqual(percentile([1, 2, 3, 4, 5], 0.5), 3)
        self.assertAlmostEqual(percentile([1, 2, 3, 4], 0.5), 2.5)

    def test_exact_mcnemar(self):
        self.assertEqual(exact_mcnemar_p(0, 0), 1.0)
        self.assertLess(exact_mcnemar_p(0, 10), 0.01)

    def test_holm_is_monotonic_and_bounded(self):
        values = [{"p_value": 0.001}, {"p_value": 0.02}, {"p_value": 0.5}]
        holm_adjust(values)
        adjusted = [v["p_holm"] for v in values]
        self.assertTrue(all(0 <= p <= 1 for p in adjusted))
        self.assertLessEqual(adjusted[0], adjusted[1])

    def test_perfect_calibration_scores_zero(self):
        rows = [
            {"predicted_label": "injection", "gold_label": "injection", "confidence": 1, "correct": True},
            {"predicted_label": "benign", "gold_label": "benign", "confidence": 1, "correct": True},
        ]
        brier, ece = brier_and_ece(rows)
        self.assertEqual(brier, 0.0)
        self.assertEqual(ece, 0.0)

    def test_write_analysis_artifacts(self):
        report = {"result_sha256": "a", "dataset_sha256": "b", "bootstrap_iterations": 10,
                  "models": {"m": {"metrics": {"n": 1, "accuracy": 1.0, "precision": 1.0,
                                                       "recall": 1.0, "f1": 1.0, "fpr": 0.0,
                                                       "mcc": 1.0, "brier_score": 0.0, "ece_10_bin": 0.0,
                                                       "latency_p50_ms": 1, "latency_p95_ms": 1},
                                     "pair_consistency": {"both_correct_rate": 1.0}}},
                  "pairwise_mcnemar": []}
        with tempfile.TemporaryDirectory() as directory:
            paths = write_analysis(report, Path(directory))
            self.assertTrue(all(path.exists() for path in paths.values()))


if __name__ == "__main__":
    unittest.main()
