from __future__ import annotations

import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from ollama_agent_benchmark.common import iter_jsonl, run_command, system_snapshot
from ollama_agent_benchmark.failures import (
    BenchmarkIntegrityFailure,
    IntegrityJournalWriteError,
    append_integrity_event,
    classify_failure,
    raise_on_integrity_failure,
    record_integrity_failure,
    sanitize_text,
)


class FailurePolicyTests(unittest.TestCase):
    def test_execution_failure_is_not_journaled_but_integrity_failure_is(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "integrity.jsonl"
            raise_on_integrity_failure(
                TimeoutError("modelo lento"),
                path,
                component="functional",
                operation="run_case",
                execution_key="key-1",
            )
            self.assertFalse(path.exists())
            with self.assertRaises(BenchmarkIntegrityFailure):
                raise_on_integrity_failure(
                    RuntimeError("defecto del harness"),
                    path,
                    component="functional",
                    operation="run_case",
                    execution_key="key-1",
                )
            self.assertEqual(len(list(iter_jsonl(path))), 1)

    def test_classification_is_conservative_and_network_failures_are_terminal(self) -> None:
        self.assertEqual(classify_failure(TimeoutError()), "execution_failure")
        self.assertEqual(classify_failure(urllib.error.URLError("offline")), "execution_failure")
        self.assertEqual(classify_failure(RuntimeError("bug")), "benchmark_integrity_failure")

    def test_sanitizer_removes_credentials_tokens_and_secret_urls(self) -> None:
        original = (
            "token=abc123 Authorization: Bearer deadbeef "
            "password=hunter2 https://user:pass@localhost:11434/api?token=abc123"
        )
        sanitized = sanitize_text(original)
        for secret in ("abc123", "deadbeef", "hunter2", "user:pass"):
            self.assertNotIn(secret, sanitized)

    def test_journal_is_validated_unique_append_only_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integrity.jsonl"
            event = record_integrity_failure(
                path,
                phase="execution",
                component="functional",
                operation="run_case",
                exc=RuntimeError("token=top-secret https://user:pass@localhost/?key=value"),
                execution_key="key",
            )
            self.assertEqual(list(iter_jsonl(path)), [event])
            self.assertNotIn("top-secret", path.read_text())
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "duplicado"):
                append_integrity_event(path, event)
            self.assertEqual(path.read_bytes(), original)
            unsafe = {**event, "event_id": "a" * 32, "execution_key": "https://user:pass@localhost"}
            with self.assertRaisesRegex(ValueError, "execution_key"):
                append_integrity_event(path, unsafe)
            self.assertEqual(path.read_bytes(), original)

    def test_journal_write_failure_is_explicit_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "integrity.jsonl"
            with (
                mock.patch(
                    "ollama_agent_benchmark.failures.append_jsonl",
                    side_effect=OSError("token=never-print"),
                ),
                self.assertRaises(IntegrityJournalWriteError) as error,
            ):
                record_integrity_failure(
                    path,
                    phase="persistence",
                    component="storage",
                    operation="append",
                    exc=RuntimeError("password=also-secret"),
                )
            self.assertNotIn("never-print", str(error.exception))
            self.assertFalse(path.exists())

    def test_system_snapshot_sanitizes_http_errors(self) -> None:
        with (
            mock.patch(
                "ollama_agent_benchmark.common.run_command",
                return_value={"stdout": "token=private", "stderr": ""},
            ),
            mock.patch(
                "ollama_agent_benchmark.common.get_json",
                side_effect=RuntimeError("https://user:pass@localhost/?token=private"),
            ),
            mock.patch("ollama_agent_benchmark.common.detect_power", return_value={}),
            mock.patch("ollama_agent_benchmark.common.parse_swap_used_bytes", return_value=0),
        ):
            snapshot = system_snapshot()
        self.assertNotIn("private", str(snapshot["ollama_ps_api_error"]))

    def test_command_output_is_sanitized_before_snapshot_storage(self) -> None:
        process = mock.Mock(returncode=0, stdout="token=private", stderr="Bearer hidden")
        with mock.patch("ollama_agent_benchmark.common.subprocess.run", return_value=process):
            result = run_command(["ps"])
        self.assertNotIn("private", result["stdout"])
        self.assertNotIn("hidden", result["stderr"])
