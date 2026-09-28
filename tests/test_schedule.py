from __future__ import annotations

import unittest
from collections import Counter

from ollama_agent_benchmark.run_plan import functional_calendar, performance_calendar


def identities(count: int) -> list[dict[str, str]]:
    return [{"name": f"model-{i}", "digest": f"{i:064x}"} for i in range(count)]


class ScheduleTests(unittest.TestCase):
    def test_functional_positions_are_balanced_and_ignore_configuration_order(self) -> None:
        for model_count in range(1, 6):
            for repetitions in range(1, 8):
                models = identities(model_count)
                calendar = functional_calendar(models, ["T001", "T002"], repetitions, 17)
                self.assertEqual(
                    calendar,
                    functional_calendar(list(reversed(models)), ["T001", "T002"], repetitions, 17),
                )
                self.assertEqual(len(calendar), model_count * repetitions * 2)
                self.assertEqual(len({item["execution_key"] for item in calendar}), len(calendar))
                for case_id in ("T001", "T002"):
                    self.assertEqual(
                        {item["block"] for item in calendar if item["target_id"] == case_id},
                        {case_id},
                    )
                    for model in models:
                        counts = Counter(
                            item["position"]
                            for item in calendar
                            if item["target_id"] == case_id and item["model"] == model["name"]
                        )
                        values = [counts[position] for position in range(1, model_count + 1)]
                        self.assertLessEqual(max(values) - min(values), 1)

    def test_performance_balances_each_workload_and_type_without_unplanned_ttft(self) -> None:
        models = identities(3)
        calendar = performance_calendar(models, ["short", "long"], 2, 4, 0, 29)
        self.assertEqual(
            calendar, performance_calendar(list(reversed(models)), ["short", "long"], 2, 4, 0, 29)
        )
        self.assertEqual(len(calendar), 3 * 2 * (2 + 4))
        self.assertFalse(any(item["measurement_type"] == "ttft" for item in calendar))
        for workload in ("short", "long"):
            for state in ("cold", "hot"):
                self.assertEqual(
                    {
                        item["block"]
                        for item in calendar
                        if item["target_id"] == workload and item["measurement_type"] == state
                    },
                    {f"{workload}:{state}"},
                )
                for model in models:
                    counts = Counter(
                        item["position"]
                        for item in calendar
                        if item["target_id"] == workload
                        and item["measurement_type"] == state
                        and item["model"] == model["name"]
                    )
                    values = [counts[position] for position in range(1, 4)]
                    self.assertLessEqual(max(values) - min(values), 1)
