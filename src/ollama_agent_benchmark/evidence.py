"""Carga fail-closed de la evidencia canónica de un run v3."""

from __future__ import annotations

import pathlib
from collections import Counter
from typing import Any

from .common import iter_jsonl, read_json
from .failures import validate_integrity_event
from .primary_records import validate_primary_record
from .run_plan import validate_run_plan


def load_run_evidence(run_dir: pathlib.Path, runner: str) -> dict[str, Any]:
    plan = validate_run_plan(read_json(run_dir / "plan.json"))
    if plan["runner"] != runner:
        raise ValueError(f"{run_dir}: runner incompatible")
    paths = (
        {"functional": run_dir / "records.jsonl"}
        if runner == "functional"
        else {
            "performance": run_dir / "performance_records.jsonl",
            "ttft": run_dir / "ttft_records.jsonl",
        }
    )
    records: dict[str, list[dict[str, Any]]] = {}
    for kind, path in paths.items():
        rows = list(iter_jsonl(path)) if path.exists() else []
        for row in rows:
            validate_primary_record(kind, row, plan)
        counts = Counter(row["execution_key"] for row in rows)
        if any(count != 1 for count in counts.values()):
            raise ValueError(f"{path}: claves duplicadas")
        records[kind] = rows
    journal = run_dir / "integrity.jsonl"
    events = list(iter_jsonl(journal)) if journal.exists() else []
    for event in events:
        validate_integrity_event(event)
    event_counts = Counter(event["event_id"] for event in events)
    if any(count != 1 for count in event_counts.values()):
        raise ValueError(f"{journal}: eventos duplicados")
    return {"plan": plan, "records": records, "integrity_events": events}
