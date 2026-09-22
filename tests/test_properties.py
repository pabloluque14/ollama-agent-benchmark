from __future__ import annotations

import itertools
import unittest

try:
    from hypothesis import given
    from hypothesis import strategies as st
except ImportError:  # pragma: no cover - el entorno mínimo prueba el fallback sin extras
    given = None
    st = None

from ollama_agent_benchmark.run_plan import functional_calendar, performance_calendar


def identities(size: int) -> list[dict[str, str]]:
    return [
        {"name": f"model-{index}", "digest": f"sha256:{index:064x}"}
        for index in range(1, size + 1)
    ]


if given is None:

    @unittest.skip("Hypothesis solo pertenece al extra dev")
    class SchedulePropertyTests(unittest.TestCase):
        def test_hypothesis_extra(self) -> None:
            pass

else:

    class SchedulePropertyTests(unittest.TestCase):
        @given(
            size=st.integers(min_value=1, max_value=5),
            repetitions=st.integers(min_value=1, max_value=8),
            seed=st.integers(),
        )
        def test_functional_calendar_is_permutation_invariant_and_balanced(
            self, size: int, repetitions: int, seed: int
        ) -> None:
            models = identities(size)
            expected = functional_calendar(models, ["case"], repetitions, seed)
            for order in itertools.islice(itertools.permutations(models), 12):
                self.assertEqual(
                    functional_calendar(list(order), ["case"], repetitions, seed), expected
                )
            counts = {
                (model["name"], position): sum(
                    row["model"] == model["name"] and row["position"] == position
                    for row in expected
                )
                for model in models
                for position in range(1, size + 1)
            }
            self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

        @given(
            size=st.integers(min_value=1, max_value=6),
            cold=st.integers(min_value=1, max_value=6),
            hot=st.integers(min_value=1, max_value=6),
            ttft=st.integers(min_value=0, max_value=6),
            seed=st.integers(),
        )
        def test_performance_keys_are_unique_and_ttft_zero_plans_nothing(
            self, size: int, cold: int, hot: int, ttft: int, seed: int
        ) -> None:
            calendar = performance_calendar(
                identities(size), ["workload-a", "workload-b"], cold, hot, ttft, seed
            )
            keys = [row["execution_key"] for row in calendar]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertEqual(
                sum(row["measurement_type"] == "ttft" for row in calendar),
                size * 2 * ttft,
            )
