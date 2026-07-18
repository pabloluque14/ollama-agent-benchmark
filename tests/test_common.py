import unittest

from ollama_agent_benchmark.common import rotate_models
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


if __name__ == "__main__":
    unittest.main()
