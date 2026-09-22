"""Contratos v3 de evidencia primaria, compartidos por escritura y lectura."""

from __future__ import annotations

import base64
import json
import pathlib
from datetime import datetime
from typing import Any

from .common import append_jsonl
from .run_plan import _schema, _validate, validate_run_plan


def validate_primary_record(kind: str, record: Any, plan: dict[str, Any]) -> dict[str, Any]:
    if kind not in {"functional", "performance", "ttft"}:
        raise ValueError("registro: tipo desconocido")
    schema = _schema(f"{kind}-record-v3")
    _validate(record, schema, "registro", schema)
    validate_run_plan(plan)
    runner = "functional" if kind == "functional" else "performance"
    if plan["runner"] != runner:
        raise ValueError("registro: runner incompatible con plan")
    matches = [
        item for item in plan["calendar"] if item["execution_key"] == record["execution_key"]
    ]
    if len(matches) != 1:
        raise ValueError("registro.execution_key: clave ausente o duplicada en plan")
    entry = matches[0]
    if record["measurement_key"] != record["execution_key"]:
        raise ValueError("registro.measurement_key: debe identificar la misma muestra terminal")
    if (
        record["run_id"] != plan["run_id"]
        or record["eligible_for_main_score"] != plan["official_eligible"]
        or record["power_condition"] != plan["environment"]["power"]
        or record["model"] != entry["model"]
    ):
        raise ValueError("registro: identidad incompatible con plan")
    target = record["case"]["id"] if kind == "functional" else record["workload_id"]
    repeat = record["repetition"] if kind == "functional" else record["run_index"]
    expected_type = "functional" if kind == "functional" else kind
    if kind == "performance":
        expected_type = record["temperature_state"]
    if (
        target != entry["target_id"]
        or repeat != entry["repetition"]
        or expected_type != entry["measurement_type"]
    ):
        raise ValueError("registro: caso, workload, repetición o tipo incompatible con clave")
    if kind == "functional":
        cases = json.loads(
            base64.b64decode(plan["input_snapshots"]["datasets/benchmark_cases_v2.json"])
        )["cases"]
        case = next(item for item in cases if item["id"] == target)
        if record["case"] != {key: case[key] for key in record["case"]}:
            raise ValueError("registro.case: metadata incompatible con input bloqueado")
        if record["run"]["evaluation"]["mode"] != case["expected"]["mode"]:
            raise ValueError("registro.run.evaluation.mode: incompatible con caso")
    if (record["status"] == "completed") != (record["runner_error"] is None):
        raise ValueError("registro.status: incoherente con runner_error")
    if (
        kind == "functional"
        and record["status"] == "execution_failure"
        and record["run"]["evaluation"]["passed"]
    ):
        raise ValueError("registro.run.evaluation: un fallo de ejecución no puede aprobar")
    if record["status"] == "execution_failure":
        if kind == "performance" and (record["wall_seconds"] is not None or record["metrics"]):
            raise ValueError("registro: un fallo de ejecución no puede aportar métricas positivas")
        if kind == "ttft" and record["ttft_seconds"] is not None:
            raise ValueError("registro: un fallo de ejecución no puede aportar TTFT oficial")
    if kind == "ttft" and (
        record["workload_compliance"]["valid"] != (record["ttft_seconds"] is not None)
    ):
        raise ValueError("registro.ttft_seconds: incoherente con cumplimiento del workload")
    try:
        started = datetime.fromisoformat(record["started_at_utc"])
        completed = datetime.fromisoformat(record["completed_at_utc"])
    except ValueError as exc:
        raise ValueError("registro: timestamps inválidos") from exc
    if started.utcoffset() is None or completed.utcoffset() is None or completed < started:
        raise ValueError("registro: timestamps sin zona u orden inválido")
    return record


def append_primary_record(
    path: pathlib.Path, kind: str, record: dict[str, Any], plan: dict[str, Any]
) -> None:
    validate_primary_record(kind, record, plan)
    append_jsonl(path, record)
