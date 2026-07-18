import unittest

from ollama_agent_benchmark.functional import evaluate_case


class EvaluationTests(unittest.TestCase):
    def test_json_markdown_is_not_valid_json(self):
        case = {
            "expected": {"mode": "json_exact", "value": {"numeros": [1, 3, 5, 8]}}
        }
        run = {
            "final_content": '```json\n{"numeros":[1,3,5,8]}\n```',
            "tool_events": [],
            "assistant_tool_turns": [],
        }
        result = evaluate_case(case, run)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["valid_json"])

    def test_numeric_exact(self):
        case = {"expected": {"mode": "numeric", "value": 74.5, "tolerance": 1e-9}}
        run = {"final_content": "74.5", "tool_events": [], "assistant_tool_turns": []}
        self.assertTrue(evaluate_case(case, run)["passed"])


if __name__ == "__main__":
    unittest.main()
