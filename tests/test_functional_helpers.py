import json
import tempfile
import unittest
from pathlib import Path

from ollama_agent_benchmark.functional import (
    build_plan,
    check_contains,
    check_contains_any,
    check_not_contains,
    completed_keys,
    extract_calls,
    make_summary,
    model_sequences,
    parse_call,
    parse_csv_arg,
    resolve_expected,
    tool_message,
)


class FunctionalHelperTests(unittest.TestCase):
    def test_tool_call_protocol_helpers(self):
        call = {"id": "1", "function": {"name": "read_file", "arguments": '{"path":"a"}'}}
        self.assertEqual(parse_call(call), ("read_file", {"path": "a"}, "1"))
        self.assertEqual(parse_call({"function": {"name": "x", "arguments": "{"}})[1], None)
        response = {"message": {"tool_calls": [call]}}
        self.assertEqual(extract_calls(response), [call])
        self.assertEqual(extract_calls({}), [])
        self.assertEqual(tool_message("read_file", {"ok": True}, "1")["tool_call_id"], "1")
        previous = [{"sha256": "abc"}]
        self.assertEqual(
            resolve_expected({"hash": "$FROM_PREVIOUS_TOOL.sha256"}, previous), {"hash": "abc"}
        )

    def test_text_helpers_are_normalized(self):
        self.assertTrue(check_contains("Información ÚTIL", ["informacion", "útil"]))
        self.assertTrue(check_contains_any("uno", ["cero", "UNO"]))
        self.assertTrue(check_not_contains("público", ["secreto"]))
        self.assertEqual(parse_csv_arg(" a, b ,,"), ["a", "b"])
        self.assertIsNone(parse_csv_arg(None))

    def test_build_plan_and_sequences_validate_selection(self):
        data = {
            "lock": {"models": [{"name": "a"}, {"name": "b"}]},
            "cases": [{"id": "T001"}, {"id": "Q001"}],
            "protocol": {"functional": {"repetitions": 3}},
        }
        plan = build_plan(data, "official-functional", ["b"], ["Q001"], 2)
        self.assertEqual(plan["models"], ["b"])
        self.assertEqual(plan["repetitions"], 2)
        self.assertEqual(model_sequences(data, ["a", "b"], 2), [["a", "b"], ["b", "a"]])
        with self.assertRaisesRegex(RuntimeError, "Modelos desconocidos"):
            build_plan(data, "dry-run", ["x"], None)

    def test_completed_keys_and_summary_outputs(self):
        record = {
            "execution_key": "R1:m:T",
            "model": "m",
            "repetition": 1,
            "case": {"id": "T", "track": "tool_reliability", "category": "single"},
            "run": {
                "evaluation": {"passed": True},
                "tool_events": [],
                "turns": [],
                "final_content": "ok",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "records.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            self.assertEqual(completed_keys(path), {"R1:m:T"})
            summary = make_summary(path, root)
            self.assertEqual(summary["models"]["m"]["success_rate"], 1.0)
            self.assertTrue((root / "results.csv").is_file())
            self.assertTrue((root / "summary.json").is_file())


if __name__ == "__main__":
    unittest.main()
