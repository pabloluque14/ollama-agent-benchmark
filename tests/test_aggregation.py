from __future__ import annotations

import copy
import unittest

from ollama_agent_benchmark.aggregation import aggregate_performance_cells
from ollama_agent_benchmark.run_plan import performance_calendar


class PerformanceCellTests(unittest.TestCase):
    def setUp(self) -> None:
        identities = [{"name": "m", "digest": "a" * 64}]
        self.plan = {
            "effective": {
                "models": ["m"],
                "workload_ids": ["w"],
                "cold_runs": 1,
                "hot_runs": 2,
                "ttft_runs": 0,
            },
            "calendar": performance_calendar(identities, ["w"], 1, 2, 0, 42),
        }
        self.records = []
        for entry in self.plan["calendar"]:
            state = entry["measurement_type"]
            self.records.append(
                {
                    "execution_key": entry["execution_key"],
                    "status": "completed",
                    "model": "m",
                    "workload_id": "w",
                    "temperature_state": state,
                    "cold_unload_verified": state == "cold",
                    "workload_compliance": {"valid": True},
                    "metrics": {
                        "prompt_tokens_per_second": 10.0,
                        "generation_tokens_per_second": 20.0,
                        "total_seconds": 2.0,
                        "load_seconds": 3.0,
                    },
                    "model_ps": {"size_vram": 1024},
                    "swap_delta_bytes": 0,
                }
            )

    def test_complete_cells_score_and_ttft_zero_creates_no_cell(self) -> None:
        workload = aggregate_performance_cells(self.plan, self.records, [])["m"]["workloads"]["w"]
        self.assertEqual(workload["hot_generation_tps"]["median"], 20.0)
        self.assertTrue(workload["cells"]["cold_load_seconds"]["valid"])
        self.assertNotIn("ttft_seconds", workload)
        self.assertNotIn("ttft_seconds", workload["cells"])

    def test_missing_or_invalid_single_sample_makes_every_affected_metric_nd(self) -> None:
        for records in (self.records[:-1], copy.deepcopy(self.records)):
            with self.subTest(count=len(records)):
                if len(records) == len(self.records):
                    records[-1]["status"] = "execution_failure"
                workload = aggregate_performance_cells(self.plan, records, [])["m"]["workloads"][
                    "w"
                ]
                self.assertIsNone(workload["hot_generation_tps"]["median"])
                self.assertIsNone(workload["size_vram_bytes"]["median"])
                self.assertFalse(workload["cells"]["hot_generation_tps"]["valid"])
