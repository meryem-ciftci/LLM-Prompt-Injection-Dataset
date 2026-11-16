import json
import unittest
from pathlib import Path

from src.dg3.croissant import croissant

ROOT = Path(__file__).resolve().parents[1]


class CroissantTests(unittest.TestCase):
    def test_metadata_copies_manifest_and_makes_no_human_claim(self):
        manifest = {"canonical_file": "x.jsonl", "sha256": "a" * 64, "record_count": 8, "family_count": 2,
                    "labels": {"benign": 6, "injection": 2}, "family_roles": {}, "languages": {"en": 4, "tr": 4},
                    "scenarios": {"rag": 8}, "splits": {"train": 8}}
        meta = croissant(manifest, name="n", description="d", version="0", file_url="u")
        self.assertEqual(meta["conformsTo"], "http://mlcommons.org/croissant/1.0")
        self.assertEqual(meta["distribution"][0]["sha256"], "a" * 64)
        self.assertEqual(meta["cr:dataStatistics"]["record_count"], 8)
        self.assertIn("no human annotation", meta["rai:dataAnnotationProtocol"])

    def test_released_pilot_metadata_matches_manifest(self):
        base = ROOT / "data" / "generated"
        meta_path, manifest_path = base / "dg3_pilot_v0.croissant.json", base / "dg3_pilot_v0.manifest.json"
        if not meta_path.exists():
            self.skipTest("pilot not generated")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(meta["distribution"][0]["sha256"], manifest["sha256"])


if __name__ == "__main__":
    unittest.main()
