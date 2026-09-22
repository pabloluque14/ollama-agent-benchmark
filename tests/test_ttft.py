from __future__ import annotations

import json
import unittest
from unittest import mock

from ollama_agent_benchmark.failures import ExecutionFailureError
from ollama_agent_benchmark.performance import streaming_ttft


class _Response:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self):
        return iter(self.chunks)


def line(value: object) -> bytes:
    return json.dumps(value).encode() + b"\n"


class TtftStreamTests(unittest.TestCase):
    def test_ignores_empty_metadata_and_final_until_significant_payload(self) -> None:
        chunks = [
            b"\n",
            line({"model": "m", "done": False}),
            line({"message": {"content": "", "thinking": ""}, "done": False}),
            line({"message": {"thinking": "razón"}, "done": False}),
            line({"message": {"content": "respuesta"}, "done": True, "eval_count": 2}),
        ]
        with (
            mock.patch("urllib.request.urlopen", return_value=_Response(chunks)),
            mock.patch("time.monotonic", side_effect=[10.0, 10.25, 10.5]),
        ):
            result = streaming_ttft("http://127.0.0.1:1", {"model": "m"})
        self.assertEqual(result["ttft_seconds"], 0.25)
        self.assertEqual(result["reconstructed_response"]["message"]["thinking"], "razón")
        self.assertEqual(result["reconstructed_response"]["message"]["content"], "respuesta")

    def test_rejects_malformed_truncated_or_root_not_object(self) -> None:
        for chunks in (
            [b"{bad}\n"],
            [line({"message": {"content": "rápido"}, "done": False})],
            [line([])],
        ):
            with (
                self.subTest(chunks=chunks),
                mock.patch("urllib.request.urlopen", return_value=_Response(chunks)),
                mock.patch("time.monotonic", side_effect=[10.0, 10.1, 10.2]),
                self.assertRaises(ExecutionFailureError),
            ):
                streaming_ttft("http://127.0.0.1:1", {"model": "m"})

    def test_fast_noncompliant_stream_keeps_only_diagnostic_ttft(self) -> None:
        chunks = [
            line({"message": {"content": "breve"}, "done": False}),
            line({"message": {"content": ""}, "done": True, "eval_count": 1}),
        ]
        workload = {"compliance": {"min_output_tokens": 5, "required_regex": ["cuatro"]}}
        with (
            mock.patch("urllib.request.urlopen", return_value=_Response(chunks)),
            mock.patch("time.monotonic", side_effect=[10.0, 10.01, 10.2]),
        ):
            result = streaming_ttft("http://127.0.0.1:1", {"model": "m"}, workload)
        self.assertIsNone(result["ttft_seconds"])
        self.assertAlmostEqual(result["observed_ttft_seconds"], 0.01)
        self.assertFalse(result["workload_compliance"]["valid"])
