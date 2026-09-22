from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ollama_agent_benchmark.common import append_jsonl, iter_jsonl, read_json


class StorageV3Tests(unittest.TestCase):
    def test_rejects_every_corrupt_jsonl_without_exposing_prefix_or_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            prefix = b'{"key":1}\n'
            for suffix, cause in (
                (b"\n", "línea vacía"),
                (b"{", "línea truncada"),
                (b"{}\n{bad}\n", "JSON inválido"),
                (b"[]\n", "objeto JSON"),
                (b"\xff\n", "UTF-8"),
                (b'{"x":1,"x":2}\n', "JSON inválido"),
            ):
                with self.subTest(suffix=suffix):
                    original = prefix + suffix
                    path.write_bytes(original)
                    with self.assertRaisesRegex(ValueError, cause) as error:
                        list(iter_jsonl(path))
                    self.assertIn(str(path), str(error.exception))
                    self.assertEqual(path.read_bytes(), original)

    def test_append_serializes_fully_before_opening_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            with self.assertRaises((TypeError, ValueError)):
                append_jsonl(path, {"bad": object()})
            self.assertFalse(path.exists())
            append_jsonl(path, {"key": 1})
            self.assertEqual(list(iter_jsonl(path)), [{"key": 1}])

    def test_json_document_rejects_duplicate_keys_with_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(ValueError, "plan.json: línea 1"):
                read_json(path)
