import json
import tempfile
import unittest
from pathlib import Path

from ollama_agent_benchmark.performance import summarize
from ollama_agent_benchmark.report import (
    exact_mcnemar,
    functional_analysis,
    performance_scores,
    wilson,
)


def functional_record(model: str, case_id: str, repetition: int, passed: bool) -> dict:
    return {
        "schema_version": 2,
        "model": model,
        "repetition": repetition,
        "case": {"id": case_id, "track": "tool_reliability"},
        "run": {"evaluation": {"passed": passed}},
        "runner_error": None,
    }


class StatisticsTests(unittest.TestCase):
    def test_wilson_and_mcnemar_golden_cases_and_properties(self):
        golden_wilson = {
            (0, 1): (0.0, 0.7934506856227626),
            (1, 1): (0.20654931437723745, 1.0),
            (5, 10): (0.236593090512564, 0.7634069094874361),
        }
        for inputs, expected in golden_wilson.items():
            with self.subTest(inputs=inputs):
                actual = wilson(*inputs)
                self.assertAlmostEqual(actual[0] or 0.0, expected[0], places=12)
                self.assertAlmostEqual(actual[1] or 0.0, expected[1], places=12)
        self.assertEqual(exact_mcnemar(0, 0), 1.0)
        self.assertEqual(exact_mcnemar(2, 0), 0.5)
        self.assertEqual(exact_mcnemar(5, 1), 0.21875)
        for first in range(8):
            for second in range(8):
                self.assertEqual(exact_mcnemar(first, second), exact_mcnemar(second, first))

    def test_wilson_uses_majority_per_unique_case(self):
        records = [
            functional_record("a", "C1", 1, True),
            functional_record("a", "C1", 2, True),
            functional_record("a", "C1", 3, False),
            functional_record("a", "C2", 1, False),
            functional_record("a", "C2", 2, False),
            functional_record("a", "C2", 3, True),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "records.jsonl").write_text(
                "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
            )
            result = functional_analysis(root, ["a"])["models"]["a"]["tracks"]["tool_reliability"]
        self.assertEqual(result["executions"], 6)
        self.assertEqual(result["unique_cases"], 2)
        self.assertEqual(result["majority_cases_passed"], 1)
        self.assertEqual(result["majority_success_rate"], 0.5)

    def test_duplicate_ttft_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = root / "performance_records.jsonl"
            ttft = root / "ttft_records.jsonl"
            records.write_text("", encoding="utf-8")
            row = {
                "execution_key": "ttft:m:w:1",
                "model": "m",
                "workload_id": "w",
                "ttft_seconds": 0.1,
            }
            ttft.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "TTFT duplicada"):
                summarize(records, ttft, root)

    def test_missing_swap_is_not_perfect(self):
        summary = {
            "models": {
                "m": {
                    "runner_errors": 0,
                    "records": 1,
                    "workloads": {},
                    "aggregate": {
                        "hot_generation_tps": {"median": 10},
                        "hot_prompt_tps": {"median": 10},
                        "hot_total_seconds": {"median": 1},
                        "cold_load_seconds": {"median": 1},
                        "ttft_seconds": {"median": 0.1},
                        "size_vram_bytes": {"median": 100},
                        "swap_delta_bytes": {"median": None},
                    },
                }
            }
        }
        score = performance_scores(
            summary,
            ["m"],
            {
                "generation": 0.35,
                "prompt": 0.20,
                "hot_latency": 0.15,
                "ttft": 0.15,
                "cold_load": 0.15,
            },
        )["m"]
        self.assertIsNone(score["memory_components"]["swap"])
        self.assertIsNone(score["memory_stability_score"])

    def test_unplanned_ttft_does_not_make_speed_unavailable_or_renormalize(self):
        summary = {
            "models": {
                "m": {
                    "runner_errors": 0,
                    "records": 1,
                    "workloads": {},
                    "aggregate": {
                        "hot_generation_tps": {"median": 10},
                        "hot_prompt_tps": {"median": 10},
                        "hot_total_seconds": {"median": 1},
                        "cold_load_seconds": {"median": 1},
                        "size_vram_bytes": {"median": 100},
                        "swap_delta_bytes": {"median": 0},
                    },
                }
            }
        }
        score = performance_scores(
            summary,
            ["m"],
            {
                "generation": 0.35,
                "prompt": 0.20,
                "hot_latency": 0.15,
                "ttft": 0.15,
                "cold_load": 0.15,
            },
            ttft_planned=False,
        )["m"]
        self.assertEqual(score["speed_score"], 85.0)
        self.assertNotIn("ttft", score["speed_components"])
        self.assertNotIn("ttft_seconds_median", score["raw"])

    def test_performance_summary_groups_before_weighting(self):
        records = []
        ttft_rows = []
        for workload, generation in (("w1", 10.0), ("w2", 30.0)):
            for state in ("cold", "hot"):
                records.append(
                    {
                        "execution_key": f"m:{workload}:{state}:1",
                        "model": "m",
                        "workload_id": workload,
                        "temperature_state": state,
                        "run_index": 1,
                        "runner_error": None,
                        "cold_unload_verified": state == "cold",
                        "workload_compliance": {"valid": True},
                        "metrics": {
                            "prompt_tokens_per_second": 20.0,
                            "generation_tokens_per_second": generation,
                            "total_seconds": 1.0,
                            "load_seconds": 2.0,
                        },
                        "model_ps": {"size_vram": 1024},
                        "swap_delta_bytes": 0,
                    }
                )
            ttft_rows.append(
                {
                    "execution_key": f"ttft:m:{workload}:1",
                    "model": "m",
                    "workload_id": workload,
                    "ttft_seconds": 0.1,
                }
            )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_path = root / "records.jsonl"
            ttft_path = root / "ttft.jsonl"
            record_path.write_text("".join(json.dumps(row) + "\n" for row in records))
            ttft_path.write_text("".join(json.dumps(row) + "\n" for row in ttft_rows))
            result = summarize(record_path, ttft_path, root, {"w1": 0.25, "w2": 0.75})
        model = result["models"]["m"]
        self.assertEqual(set(model["workloads"]), {"w1", "w2"})
        self.assertEqual(model["aggregate"]["hot_generation_tps"]["median"], 25.0)


try:
    from statsmodels.stats.contingency_tables import mcnemar as oracle_mcnemar
    from statsmodels.stats.proportion import proportion_confint
except ImportError:  # El entorno mínimo conserva los casos dorados sin el oráculo pesado.
    oracle_mcnemar = None
    proportion_confint = None


@unittest.skipUnless(proportion_confint is not None, "statsmodels solo pertenece al extra dev")
class StatisticsOracleTests(unittest.TestCase):
    def test_wilson_matches_statsmodels_grid(self) -> None:
        assert proportion_confint is not None
        for total in range(1, 41):
            for successes in range(total + 1):
                expected = proportion_confint(successes, total, alpha=0.05, method="wilson")
                actual = wilson(successes, total)
                with self.subTest(successes=successes, total=total):
                    self.assertAlmostEqual(actual[0] or 0.0, float(expected[0]), places=12)
                    self.assertAlmostEqual(actual[1] or 0.0, float(expected[1]), places=12)

    def test_exact_mcnemar_matches_statsmodels_discordances(self) -> None:
        assert oracle_mcnemar is not None
        for first in range(11):
            for second in range(11):
                expected = float(oracle_mcnemar([[0, first], [second, 0]], exact=True).pvalue)
                with self.subTest(first=first, second=second):
                    self.assertAlmostEqual(exact_mcnemar(first, second), expected, places=12)


if __name__ == "__main__":
    unittest.main()
