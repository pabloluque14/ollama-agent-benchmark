"""Puerta única de validación para reanudar evidencia v3."""

from __future__ import annotations

import pathlib
from collections import Counter
from typing import Any

from .common import iter_jsonl
from .failures import validate_integrity_event
from .primary_records import validate_primary_record
from .run_plan import validate_run_plan


def validate_resume_evidence(
    plan: dict[str, Any],
    records: dict[str, pathlib.Path],
    integrity_path: pathlib.Path,
) -> dict[str, set[str]]:
    """Valida toda la evidencia antes de devolver las claves terminales."""
    validate_run_plan(plan)
    if integrity_path.exists():
        events = list(iter_jsonl(integrity_path))
        for event in events:
            validate_integrity_event(event)
        if events:
            raise ValueError("reanudación rechazada: el run contiene fallos de integridad")
    completed: dict[str, set[str]] = {}
    for kind, path in records.items():
        rows = list(iter_jsonl(path)) if path.exists() else []
        for row in rows:
            validate_primary_record(kind, row, plan)
        keys = [row["execution_key"] for row in rows]
        duplicates = [key for key, count in Counter(keys).items() if count != 1]
        if duplicates:
            raise ValueError(f"reanudación rechazada: claves duplicadas en {path.name}")
        completed[kind] = set(keys)
    return completed
