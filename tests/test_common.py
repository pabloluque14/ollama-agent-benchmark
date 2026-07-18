import tempfile
import unittest
from pathlib import Path

from ollama_agent_benchmark.common import (
    config_fingerprint,
    load_config,
    rotate_models,
    validate_manifest_compatibility,
)
from ollama_agent_benchmark.report import exact_mcnemar, wilson


class CommonTests(unittest.TestCase):
    def test_rotate_models(self):
        self.assertEqual(
            rotate_models(["a", "b", "c"], 3),
            [["a", "b", "c"], ["b", "c", "a"], ["c", "a", "b"]],
        )

    def test_wilson_bounds(self):
        low, high = wilson(8, 10)
        self.assertIsNotNone(low)
        self.assertIsNotNone(high)
        self.assertLess(low, 0.8)
        self.assertGreater(high, 0.8)

    def test_mcnemar_symmetry(self):
        self.assertEqual(exact_mcnemar(0, 0), 1.0)
        self.assertAlmostEqual(exact_mcnemar(2, 5), exact_mcnemar(5, 2))

    def test_example_config_is_complete_v2(self):
        config = load_config(Path(__file__).parents[1] / "config" / "benchmark.example.json")
        self.assertEqual(config["schema_version"], 2)
        self.assertIsInstance(config["order_control"]["seed"], int)
        self.assertEqual(sum(config["speed_weights"].values()), 1.0)

    def test_missing_order_seed_has_context(self):
        source = Path(__file__).parents[1] / "config" / "benchmark.example.json"
        document = __import__("json").loads(source.read_text(encoding="utf-8"))
        del document["order_control"]["seed"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "benchmark.json"
            path.write_text(__import__("json").dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "order_control.seed"):
                load_config(path)

    def test_manifest_compatibility_reports_fields(self):
        existing = {"schema_version": 2, "models": ["a"], "generation": {"seed": 1}}
        requested = {"schema_version": 2, "models": ["b"], "generation": {"seed": 1}}
        with self.assertRaisesRegex(ValueError, "models"):
            validate_manifest_compatibility(existing, requested, ("schema_version", "models", "generation"))

    def test_config_fingerprint_is_order_stable(self):
        self.assertEqual(config_fingerprint({"a": 1, "b": 2}), config_fingerprint({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
