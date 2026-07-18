import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from ollama_agent_benchmark.cli import main as cli_main
from ollama_agent_benchmark.common import (
    append_jsonl,
    config_fingerprint,
    detect_power,
    iter_jsonl,
    load_config,
    metric_rates,
    parse_swap_used_bytes,
    rotate_models,
    safe_slug,
    validate_manifest_compatibility,
    write_json_atomic,
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
            validate_manifest_compatibility(
                existing, requested, ("schema_version", "models", "generation")
            )

    def test_config_fingerprint_is_order_stable(self):
        self.assertEqual(config_fingerprint({"a": 1, "b": 2}), config_fingerprint({"b": 2, "a": 1}))

    def test_atomic_json_and_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json_atomic(root / "value.json", {"á": 1})
            append_jsonl(root / "values.jsonl", {"n": 1})
            append_jsonl(root / "values.jsonl", {"n": 2})
            self.assertEqual(list(iter_jsonl(root / "values.jsonl")), [{"n": 1}, {"n": 2}])

    def test_metric_rates_preserve_missing_values(self):
        rates = metric_rates(
            {
                "prompt_eval_count": 10,
                "prompt_eval_duration": 1_000_000_000,
                "eval_count": 5,
                "eval_duration": 500_000_000,
            }
        )
        self.assertEqual(rates["prompt_tokens_per_second"], 10)
        self.assertEqual(rates["generation_tokens_per_second"], 10)
        self.assertIsNone(metric_rates({})["generation_tokens_per_second"])

    def test_platform_power_and_swap_policies(self):
        with mock.patch("ollama_agent_benchmark.common.platform.system", return_value="Linux"):
            self.assertEqual(detect_power()["condition"], "not_applicable")
            self.assertIsNone(parse_swap_used_bytes())
        with (
            mock.patch("ollama_agent_benchmark.common.platform.system", return_value="Darwin"),
            mock.patch(
                "ollama_agent_benchmark.common.run_command",
                return_value={"stdout": "Now drawing from 'AC Power'"},
            ),
        ):
            self.assertEqual(detect_power()["condition"], "ac_power")
        self.assertEqual(safe_slug("modelo con / espacios"), "modelo_con_espacios")

    def test_subcommand_help_lists_its_real_options(self):
        output = StringIO()
        with self.assertRaisesRegex(SystemExit, "0"), redirect_stdout(output):
            cli_main(["functional", "--help"])
        self.assertIn("--case-ids", output.getvalue())
        self.assertIn("--resume", output.getvalue())


if __name__ == "__main__":
    unittest.main()
