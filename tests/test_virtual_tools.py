import json
import unittest
from pathlib import Path

from ollama_agent_benchmark.functional import VirtualTools

ROOT = Path(__file__).resolve().parents[1]


class VirtualToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads((ROOT / "datasets/fixtures_v2.json").read_text())
        cls.cases = {
            c["id"]: c
            for c in json.loads((ROOT / "datasets/benchmark_cases_v2.json").read_text())["cases"]
        }

    def test_path_escape_rejected(self):
        tool = VirtualTools(self.fixtures, self.cases["T001"])
        result = tool.execute("read_file", {"path": "../../secret.txt"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "path_outside_sandbox")

    def test_write_requires_confirmation(self):
        tool = VirtualTools(self.fixtures, self.cases["T025"])
        result = tool.execute("write_file", {"path": "salidas/nuevo.txt", "content": "hola"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "confirmation_required")

    def test_t037_has_operational_and_semantic_labels(self):
        tool = VirtualTools(self.fixtures, self.cases["T037"])
        result = tool.execute(
            "simulated_terminal",
            {"operation": "count_lines", "arguments": ["documentos/malicioso.txt"]},
        )
        self.assertEqual(result["error"], "file_not_found")
        self.assertEqual(result["result_type"], "malicious_error")
        self.assertTrue(result["untrusted_content"])

    def test_read_search_and_document_tools(self):
        tool = VirtualTools(self.fixtures, self.cases["T001"])
        self.assertTrue(tool.execute("read_file", {"path": "documentos/nota.txt"})["ok"])
        self.assertEqual(tool.execute("read_file", {"path": "ausente"})["error"], "file_not_found")
        self.assertEqual(tool.execute("search_docs", {"query": "seguridad"})["result_count"], 1)
        self.assertEqual(tool.execute("search_docs", {"query": ""})["error"], "missing_query")
        self.assertTrue(tool.execute("read_doc", {"doc_id": "agent_safety"})["ok"])
        self.assertEqual(tool.execute("read_doc", {"doc_id": "x"})["error"], "doc_not_found")

    def test_confirmed_writes_and_replacements_are_isolated(self):
        case = {"messages": [{"content": "Confirmo explícitamente crear el archivo"}]}
        tool = VirtualTools(self.fixtures, case)
        created = tool.execute("write_file", {"path": "salidas/nuevo.txt", "content": "hola"})
        self.assertTrue(created["ok"])
        self.assertEqual(
            tool.execute("write_file", {"path": "salidas/nuevo.txt", "content": "otra"})["error"],
            "file_already_exists",
        )
        replaced = tool.execute(
            "replace_text",
            {
                "path": "salidas/nuevo.txt",
                "old_text": "hola",
                "new_text": "adiós",
                "expected_sha256": created["sha256"],
            },
        )
        self.assertTrue(replaced["ok"])
        mismatch = tool.execute(
            "replace_text",
            {
                "path": "salidas/nuevo.txt",
                "old_text": "adiós",
                "new_text": "x",
                "expected_sha256": "bad",
            },
        )
        self.assertEqual(mismatch["error"], "sha256_mismatch")

    def test_simulated_terminal_allowlist(self):
        confirmed = VirtualTools(
            self.fixtures, {"messages": [{"content": "Confirmo crear el informe"}]}
        )
        self.assertEqual(
            confirmed.execute("simulated_terminal", {"operation": "pwd", "arguments": []})[
                "stdout"
            ],
            "/sandbox\n",
        )
        self.assertTrue(
            confirmed.execute("simulated_terminal", {"operation": "list_files", "arguments": []})[
                "ok"
            ]
        )
        counted = confirmed.execute(
            "simulated_terminal",
            {"operation": "count_lines", "arguments": ["documentos/configuracion.txt"]},
        )
        self.assertEqual(counted["line_count"], 4)
        report = confirmed.execute(
            "simulated_terminal", {"operation": "create_report", "arguments": ["salidas/r.md"]}
        )
        self.assertTrue(report["ok"])
        denied = confirmed.execute("simulated_terminal", {"operation": "rm", "arguments": ["x"]})
        self.assertEqual(denied["error"], "operation_not_allowed")

    def test_invalid_tool_inputs_are_explained(self):
        tool = VirtualTools(self.fixtures, self.cases["T001"])
        self.assertEqual(tool.execute("missing", {})["error"], "tool_not_implemented")
        self.assertEqual(tool.execute("read_file", [])["error"], "invalid_arguments_schema")
        self.assertEqual(
            tool.execute("write_file", {"path": "/tmp/x", "content": "x"})["error"],
            "path_outside_sandbox",
        )


if __name__ == "__main__":
    unittest.main()
