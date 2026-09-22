from __future__ import annotations

import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from ollama_agent_benchmark.common import iter_jsonl
from ollama_agent_benchmark.failures import (
    IntegrityJournalWriteError,
    append_integrity_event,
    classify_failure,
    record_integrity_failure,
    sanitize_text,
)


class FailurePolicyTests(unittest.TestCase):
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
