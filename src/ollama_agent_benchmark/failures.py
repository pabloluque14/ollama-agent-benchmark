"""Clasificación final de fallos y diario canónico de integridad v3."""

from __future__ import annotations

import json
import pathlib
import urllib.error
import uuid
from datetime import datetime
from typing import Any

from .common import append_jsonl, iter_jsonl, sanitize_text, utc_now
from .run_plan import _schema, _validate


class BenchmarkIntegrityFailure(RuntimeError):
    """Detiene el run sin atribuir el defecto al modelo."""


class IntegrityJournalWriteError(BenchmarkIntegrityFailure):
    """El evento no pudo entregarse al almacenamiento."""


class ExecutionFailureError(RuntimeError):
    """Respuesta terminal inválida atribuible al sistema evaluado."""


def classify_failure(exc: BaseException) -> str:
    """Solo atribuye al sistema evaluado fallos observables de su protocolo HTTP."""
    if isinstance(
        exc,
        (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            json.JSONDecodeError,
            ExecutionFailureError,
        ),
    ):
        return "execution_failure"
    return "benchmark_integrity_failure"


def validate_integrity_event(event: Any) -> dict[str, Any]:
    schema = _schema("integrity-event-v3")
    _validate(event, schema, "evento", schema)
    try:
        timestamp = datetime.fromisoformat(event["timestamp_utc"])
    except ValueError as exc:
        raise ValueError("evento.timestamp_utc: timestamp inválido") from exc
    if timestamp.utcoffset() is None:
        raise ValueError("evento.timestamp_utc: falta zona horaria")
    for field in ("description", "operation", "execution_key"):
        value = event[field]
        if value is not None and sanitize_text(value) != value:
            raise ValueError(f"evento.{field}: contiene datos sensibles o no saneados")
    return event


def append_integrity_event(path: pathlib.Path, event: dict[str, Any]) -> None:
    validate_integrity_event(event)
    existing = list(iter_jsonl(path)) if path.exists() else []
    for item in existing:
        validate_integrity_event(item)
    if event["event_id"] in {item["event_id"] for item in existing}:
        raise ValueError("evento.event_id: duplicado")
    append_jsonl(path, event)


def record_integrity_failure(
    path: pathlib.Path,
    *,
    phase: str,
    component: str,
    operation: str,
    exc: BaseException,
    execution_key: str | None = None,
) -> dict[str, Any]:
    event = {
        "schema_version": 3,
        "event_id": uuid.uuid4().hex,
        "timestamp_utc": utc_now().isoformat(),
        "category": "benchmark_integrity_failure",
        "phase": phase,
        "code": "unexpected_harness_failure",
        "description": sanitize_text(f"{type(exc).__name__}: {exc}"),
        "component": component,
        "operation": operation,
        "execution_key": execution_key,
        "persistence_compromised": False,
    }
    try:
        append_integrity_event(path, event)
    except Exception as write_exc:
        raise IntegrityJournalWriteError(
            "no se pudo persistir el evento de integridad: " + sanitize_text(write_exc)
        ) from None
    return event
