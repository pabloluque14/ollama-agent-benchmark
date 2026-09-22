from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ollama_agent_benchmark.common import sha256_file
from ollama_agent_benchmark.input_contracts import validate_dataset
from ollama_agent_benchmark.run_plan import _schema, _validate

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "src/ollama_agent_benchmark/contracts"
DATASETS = {
    "cases": ("benchmark-cases-v2", ROOT / "datasets/benchmark_cases_v2.json"),
    "fixtures": ("fixtures-v2", ROOT / "datasets/fixtures_v2.json"),
    "tools": ("tools-v2", ROOT / "datasets/tools_v2.json"),
    "workloads": (
        "performance-workloads-v2",
        ROOT / "datasets/performance_workloads_v2.json",
    ),
}


class ContractCorpusTests(unittest.TestCase):
    def test_contract_inventory_is_local_and_complete(self) -> None:
        expected = {
            "config-v3.schema.json",
            "model-lock-v3.schema.json",
            "benchmark-cases-v2.schema.json",
            "fixtures-v2.schema.json",
            "tools-v2.schema.json",
            "performance-workloads-v2.schema.json",
            "run-plan-v3.schema.json",
            "functional-record-v3.schema.json",
            "performance-record-v3.schema.json",
            "ttft-record-v3.schema.json",
            "integrity-event-v3.schema.json",
            "report-v3.schema.json",
        }
        self.assertLessEqual(expected, {path.name for path in CONTRACTS.glob("*.schema.json")})
        for path in CONTRACTS.glob("*.schema.json"):
            document = json.loads(path.read_text())
            self.assertTrue(document.get("$id"))
            self.assertNotIn('"$ref": "http', path.read_text())

    def test_frozen_inputs_keep_exact_content_and_validate_without_mutation(self) -> None:
        hashes = {
            "cases": "d91c633d7555fa8faa04f5589c230202c59dbe9b8696d8adccb45adfdcc98804",
            "fixtures": "e9be7b50bc9af085d2916f75e3c5f5c5d14a9f1fbae6e80ebe4186866a35ff0a",
            "tools": "deb2fd26be4e1ba3d200b277dbc1d3efb1bebcee432895a2dc780b77b5b609e0",
            "workloads": "807d749067c0206cd071d6e1dbd0f6b8d7bbeeb2b5fe6f6ea82a49bd0fdbc0da",
        }
        for kind, (_schema_name, path) in DATASETS.items():
            with self.subTest(kind=kind):
                document = json.loads(path.read_text())
                original = copy.deepcopy(document)
                self.assertIs(validate_dataset(kind, document), document)
                self.assertEqual(document, original)
                self.assertEqual(sha256_file(path), hashes[kind])

    def test_structural_corpus_rejects_missing_extra_types_and_versions(self) -> None:
        for kind, (schema_name, path) in DATASETS.items():
            document = json.loads(path.read_text())
            schema = _schema(schema_name)
            for mutation in ("missing", "extra", "type", "version"):
                with self.subTest(kind=kind, mutation=mutation):
                    invalid = copy.deepcopy(document)
                    if mutation == "missing":
                        del invalid["schema_version"]
                    elif mutation == "extra":
                        invalid["unknown"] = True
                    elif mutation == "type":
                        invalid["schema_version"] = True
                    else:
                        invalid["schema_version"] = 999
                    with self.assertRaises(ValueError):
                        _validate(invalid, schema, "input", schema)

    def test_semantic_corpus_rejects_formally_valid_incoherence(self) -> None:
        cases = json.loads(DATASETS["cases"][1].read_text())
        cases["cases"][1]["id"] = cases["cases"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicados"):
            validate_dataset("cases", cases)
        fixtures = json.loads(DATASETS["fixtures"][1].read_text())
        next(iter(fixtures["virtual_files"].values()))["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "incoherente"):
            validate_dataset("fixtures", fixtures)


try:
    import jsonschema
except ImportError:  # El entorno mínimo no instala el oráculo de desarrollo.
    jsonschema = None


@unittest.skipUnless(jsonschema is not None, "jsonschema solo pertenece al extra dev")
class JsonSchemaOracleTests(unittest.TestCase):
    def test_runtime_structural_decisions_match_jsonschema(self) -> None:
        assert jsonschema is not None
        for _kind, (schema_name, path) in DATASETS.items():
            schema = _schema(schema_name)
            valid = json.loads(path.read_text())
            invalid = {**valid, "unknown": True}
            for document, expected in ((valid, True), (invalid, False)):
                with self.subTest(schema=schema_name, expected=expected):
                    oracle = not list(jsonschema.Draft202012Validator(schema).iter_errors(document))
                    try:
                        _validate(document, schema, "input", schema)
                        runtime = True
                    except ValueError:
                        runtime = False
                    self.assertEqual(runtime, oracle)
