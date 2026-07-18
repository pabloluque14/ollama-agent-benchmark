import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((ROOT / "datasets/benchmark_cases_v1.json").read_text())["cases"]
        cls.tools = json.loads((ROOT / "datasets/tools_v1.json").read_text())["tools"]

    def test_counts(self):
        self.assertEqual(len(self.cases), 60)
        self.assertEqual(sum(c["track"] == "tool_reliability" for c in self.cases), 42)
        self.assertEqual(sum(c["track"] == "quality_reasoning" for c in self.cases), 18)

    def test_unique_ids(self):
        ids = [c["id"] for c in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_allowed_tools_exist(self):
        names = {t["function"]["name"] for t in self.tools}
        for case in self.cases:
            self.assertFalse(set(case.get("allowed_tools", [])) - names)


if __name__ == "__main__":
    unittest.main()
