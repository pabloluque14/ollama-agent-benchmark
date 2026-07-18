import json
import tempfile
import unittest
from pathlib import Path

from ollama_agent_benchmark.performance import summarize
from ollama_agent_benchmark.report import functional_analysis, performance_scores


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


if __name__ == "__main__":
    unittest.main()
