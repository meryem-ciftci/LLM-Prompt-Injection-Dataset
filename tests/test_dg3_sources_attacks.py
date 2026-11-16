import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.dg3.attacks import assemblable, load_components, validate_component
from src.dg3.sources import LicenseError, check_license, load_carriers, load_registry

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dg3"


class LicenseGateTests(unittest.TestCase):
    def test_allowed_license_passes(self):
        self.assertEqual(check_license({"registry_id": "x", "license": "CC-BY-SA-4.0"}), "CC-BY-SA-4.0")

    def test_missing_unknown_or_restrictive_license_fails_closed(self):
        for license_id in (None, "", "unknown", "CC-BY-NC-4.0", "proprietary", "cc-by-sa-4.0"):
            entry = {"registry_id": "x", "carriers_path": "c.jsonl"}
            if license_id is not None:
                entry["license"] = license_id
            with self.subTest(license=license_id), self.assertRaises(LicenseError):
                check_license(entry)

    def _registry_copy(self, directory: Path, **overrides) -> Path:
        shutil.copy(FIXTURES / "carriers.jsonl", directory / "carriers.jsonl")
        registry = json.loads((FIXTURES / "registry.json").read_text(encoding="utf-8"))
        registry["sources"][0].update(overrides)
        path = directory / "registry.json"
        path.write_text(json.dumps(registry), encoding="utf-8")
        return path

    def test_registry_with_unlicensed_source_loads_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._registry_copy(Path(d), license="unknown")
            with self.assertRaises(LicenseError):
                load_registry(path)
            with self.assertRaises(LicenseError):
                load_carriers(path)

    def test_snapshot_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._registry_copy(Path(d), snapshot_sha256="0" * 64)
            with self.assertRaisesRegex(ValueError, "snapshot sha256 mismatch"):
                load_carriers(path)

    def test_carriers_load_with_source_metadata(self):
        carriers = load_carriers(FIXTURES / "registry.json")
        self.assertEqual([c["carrier_id"] for c in carriers], sorted(c["carrier_id"] for c in carriers))
        for c in carriers:
            self.assertEqual(c["_source"]["license"], "CC0-1.0")
            self.assertRegex(c["_source"]["snapshot_sha256"], "^[a-f0-9]{64}$")


class AttackComponentTests(unittest.TestCase):
    def setUp(self):
        self.components = load_components(FIXTURES / "attack_components")
        self.base = dict(self.components[0])

    def test_fixture_components_load(self):
        self.assertEqual(len(self.components), 5)

    def test_model_proposed_is_never_assemblable(self):
        ids = {c["component_id"] for c in assemblable(self.components)}
        self.assertNotIn("ATK-EN-003", ids)
        self.assertEqual(len(ids), 4)

    def test_taxonomy_violations_are_reported(self):
        cases = {
            "goal": {"goal": "world_domination"},
            "techniques": {"techniques": ["telepathy"]},
            "witness type": {"witness": {"type": "smoke_signal", "value": "ABCDE"}},
            "witness value not present": {"witness": {"type": "phrase", "value": "NOT-IN-TEXT"}},
            "leaks into trigger": {"trigger_benign_text": "mentions canary-7f3a-91qx casually"},
            "safety": {"safety": {"fictional": True, "live_secret": True, "executable_payload": False}},
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                self.assertTrue(validate_component({**self.base, **change}))

    def test_valid_component_has_no_errors(self):
        self.assertEqual(validate_component(self.base), [])


if __name__ == "__main__":
    unittest.main()
