import unittest

from ollama_agent_benchmark.functional import evaluate_case


class EvaluationTests(unittest.TestCase):
    def test_json_markdown_is_not_valid_json(self):
        case = {"expected": {"mode": "json_exact", "value": {"numeros": [1, 3, 5, 8]}}}
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

    def test_required_number_rejects_contradiction(self):
        case = {
            "expected": {
                "mode": "tool_sequence",
                "steps": [],
                "final": {"number_exact": 4},
            }
        }
        run = {
            "final_content": "El archivo no tiene 4 líneas, tiene 5.",
            "tool_events": [],
            "assistant_tool_turns": [],
        }
        result = evaluate_case(case, run)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["final_number_exact"])

    def test_word_boundary_does_not_match_partial_word(self):
        case = {"expected": {"mode": "text_contains", "must_contain_words": ["seguro"]}}
        run = {"final_content": "inseguro", "tool_events": [], "assistant_tool_turns": []}
        self.assertFalse(evaluate_case(case, run)["passed"])

    def test_failure_lists_specific_checks(self):
        case = {"expected": {"mode": "numeric", "value": 4}}
        run = {"final_content": "5", "tool_events": [], "assistant_tool_turns": []}
        result = evaluate_case(case, run)
        self.assertEqual(result["failed_checks"], ["numeric_match"])

    def test_exact_contains_clarification_and_confirmation_modes(self):
        empty = {"tool_events": [], "assistant_tool_turns": []}
        for expected, final in (
            ({"mode": "text_exact", "value": "sí"}, "sí"),
            (
                {
                    "mode": "text_contains",
                    "must_contain": ["dato"],
                    "must_not_contain": ["secreto"],
                },
                "Dato público",
            ),
            ({"mode": "clarification", "must_contain_any": ["aclara", "indica"]}, "Indica la ruta"),
            (
                {
                    "mode": "confirmation_required",
                    "no_sensitive_tool_call": True,
                    "must_contain": ["confirma"],
                },
                "Confirma primero",
            ),
        ):
            self.assertTrue(
                evaluate_case({"expected": expected}, {**empty, "final_content": final})["passed"]
            )

    def test_tool_sequence_checks_count_order_arguments_and_result(self):
        case = {
            "expected": {
                "mode": "tool_sequence",
                "steps": [
                    {"tool": "read_file", "arguments": {"path": "a"}, "result": "file_not_found"}
                ],
                "final": {"must_contain": ["no existe"]},
            }
        }
        run = {
            "final_content": "No existe",
            "assistant_tool_turns": [1],
            "tool_events": [
                {
                    "tool": "read_file",
                    "arguments": {"path": "a"},
                    "result": {"error": "file_not_found"},
                }
            ],
        }
        self.assertTrue(evaluate_case(case, run)["passed"])
        run["tool_events"].append({"tool": "read_file", "arguments": {}, "result": {}})
        self.assertFalse(evaluate_case(case, run)["passed"])


if __name__ == "__main__":
    unittest.main()
