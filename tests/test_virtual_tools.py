import json
import unittest
from pathlib import Path

from ollama_agent_benchmark.functional import VirtualTools

ROOT = Path(__file__).resolve().parents[1]


class VirtualToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads((ROOT / "datasets/fixtures_v1.json").read_text())
        cls.cases = {
            c["id"]: c
            for c in json.loads((ROOT / "datasets/benchmark_cases_v1.json").read_text())["cases"]
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


if __name__ == "__main__":
    unittest.main()
