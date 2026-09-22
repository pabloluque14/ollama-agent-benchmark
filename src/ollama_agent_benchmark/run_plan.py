"""Contrato local y persistencia inmutable del plan del run v3."""

from __future__ import annotations

import json
import math
import os
import pathlib
import platform
import re
import tempfile
from datetime import datetime
from functools import cache
from typing import Any

from .common import BENCHMARK_VERSION, api_base, public_base_url, read_json, utc_now


@cache
def _schema() -> dict[str, Any]:
    path = pathlib.Path(__file__).parent / "contracts" / "run-plan-v3.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _type_matches(value: Any, kind: str) -> bool:
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and math.isfinite(value)
        )
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    raise ValueError(f"Tipo de contrato desconocido: {kind}")


def _validate(value: Any, rule: dict[str, Any], path: str, schema: dict[str, Any]) -> None:
    if "$ref" in rule:
        name = rule["$ref"].removeprefix("#/$defs/")
        _validate(value, schema["$defs"][name], path, schema)
        return
    if "oneOf" in rule:
        errors = []
        for branch in rule["oneOf"]:
            try:
                _validate(value, branch, path, schema)
                return
            except ValueError as exc:
                errors.append(exc)
        raise errors[0]
    if "const" in rule and (type(value) is not type(rule["const"]) or value != rule["const"]):
        raise ValueError(f"{path}: versión o valor fijo inválido")
    if "enum" in rule and value not in rule["enum"]:
        raise ValueError(f"{path}: valor no permitido")
    kinds = rule.get("type")
    if kinds is not None:
        allowed = kinds if isinstance(kinds, list) else [kinds]
        if not any(_type_matches(value, kind) for kind in allowed):
            raise ValueError(f"{path}: tipo inválido")
    if isinstance(value, dict):
        required = set(rule.get("required", []))
        missing = required - value.keys()
        if missing:
            raise ValueError(f"{path}.{sorted(missing)[0]}: campo obligatorio ausente")
        if len(value) < rule.get("minProperties", 0):
            raise ValueError(f"{path}: faltan propiedades")
        properties = rule.get("properties", {})
        extra = value.keys() - properties.keys()
        additional = rule.get("additionalProperties", True)
        if extra and additional is False:
            raise ValueError(f"{path}.{sorted(extra)[0]}: campo desconocido")
        for key, item in value.items():
            child_rule = properties.get(key, additional)
            if isinstance(child_rule, dict):
                _validate(item, child_rule, f"{path}.{key}", schema)
    elif isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            raise ValueError(f"{path}: lista vacía o incompleta")
        if rule.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(
            value
        ):
            raise ValueError(f"{path}: elementos duplicados")
        for index, item in enumerate(value):
            _validate(item, rule.get("items", {}), f"{path}[{index}]", schema)
    elif isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            raise ValueError(f"{path}: texto vacío")
        if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
            raise ValueError(f"{path}: formato inválido")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in rule and value < rule["minimum"]:
            raise ValueError(f"{path}: menor que el mínimo")
        if "exclusiveMinimum" in rule and value <= rule["exclusiveMinimum"]:
            raise ValueError(f"{path}: fuera del mínimo exclusivo")


def validate_run_plan(plan: Any) -> dict[str, Any]:
    """Valida estructura y coherencia sin modificar ni completar el plan."""
    schema = _schema()
    _validate(plan, schema, "plan", schema)
    if plan["runner"] == "functional":
        if plan["mode"] not in {"smoke", "official-functional"}:
            raise ValueError("plan.mode: incompatible con runner funcional")
        if "case_ids" not in plan["effective"] or "case_ids" not in plan["overrides"]:
            raise ValueError("plan.effective: no corresponde al runner funcional")
    else:
        if plan["mode"] not in {"smoke", "official-performance"}:
            raise ValueError("plan.mode: incompatible con runner de rendimiento")
        if "workload_ids" not in plan["effective"] or "workloads" not in plan["overrides"]:
            raise ValueError("plan.effective: no corresponde al runner de rendimiento")
    names = [item["name"] for item in plan["models"]]
    if len(names) != len(set(names)) or names != plan["effective"]["models"]:
        raise ValueError("plan.models: identidades y selección efectiva no coinciden")
    if public_base_url(plan["ollama"]["base_url"]) != plan["ollama"]["base_url"]:
        raise ValueError("plan.ollama.base_url: debe estar saneada")
    try:
        created_at = datetime.fromisoformat(plan["created_at_utc"])
    except ValueError as exc:
        raise ValueError("plan.created_at_utc: timestamp inválido") from exc
    if created_at.utcoffset() is None:
        raise ValueError("plan.created_at_utc: falta zona horaria")
    for group in ("weights", "speed_weights", "workload_weights"):
        if not math.isclose(sum(plan["scoring_protocol"][group].values()), 1.0, abs_tol=1e-12):
            raise ValueError(f"plan.scoring_protocol.{group}: los pesos no suman 1")
    expected: set[str] = set()
    effective = plan["effective"]
    if plan["runner"] == "functional":
        for rep in range(1, effective["repetitions"] + 1):
            for model in names:
                for case_id in effective["case_ids"]:
                    expected.add(f"R{rep}:{model}:{case_id}")
    else:
        for model in names:
            for workload in effective["workload_ids"]:
                for state in ("cold", "hot", "ttft"):
                    for index in range(1, effective[f"{state}_runs"] + 1):
                        prefix = "ttft:" if state == "ttft" else ""
                        suffix = "" if state == "ttft" else f":{state}"
                        expected.add(f"{prefix}{model}:{workload}{suffix}:{index}")
    observed = [item["execution_key"] for item in plan["calendar"]]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ValueError("plan.calendar: claves duplicadas, ausentes o inesperadas")
    positions: dict[str, set[int]] = {}
    for item in plan["calendar"]:
        if item["model"] not in names:
            raise ValueError("plan.calendar.model: modelo no planificado")
        if plan["runner"] == "functional":
            if (
                item["target_id"] not in effective["case_ids"]
                or item["measurement_type"] != "functional"
            ):
                raise ValueError("plan.calendar: caso o tipo no planificado")
            key = f"R{item['repetition']}:{item['model']}:{item['target_id']}"
            block = f"R{item['repetition']}:{item['target_id']}"
        elif (
            item["target_id"] not in effective["workload_ids"]
            or item["measurement_type"] == "functional"
        ):
            raise ValueError("plan.calendar: workload o tipo no planificado")
        else:
            state = item["measurement_type"]
            index = item["repetition"]
            key = (
                f"ttft:{item['model']}:{item['target_id']}:{index}"
                if state == "ttft"
                else f"{item['model']}:{item['target_id']}:{state}:{index}"
            )
            block = f"{item['target_id']}:{state}:{index}"
        if item["execution_key"] != key or item["block"] != block:
            raise ValueError("plan.calendar: clave o bloque incoherente con sus metadatos")
        if item["position"] > len(names):
            raise ValueError("plan.calendar.position: fuera de rango")
        seen = positions.setdefault(block, set())
        if item["position"] in seen:
            raise ValueError("plan.calendar.position: posición duplicada en bloque")
        seen.add(item["position"])
    if any(seen != set(range(1, len(names) + 1)) for seen in positions.values()):
        raise ValueError("plan.calendar.position: bloque incompleto")
    if plan["official_eligible"] and not plan["mode"].startswith("official-"):
        raise ValueError("plan.official_eligible: smoke no es oficial")
    if plan["official_eligible"] and plan["environment"]["power"] not in {
        "ac_power",
        "not_applicable",
    }:
        raise ValueError("plan.official_eligible: alimentación incompatible")
    return plan


def make_run_plan(
    *,
    run_id: str,
    runner: str,
    mode: str,
    config: dict[str, Any],
    lock: dict[str, Any],
    effective: dict[str, Any],
    overrides: dict[str, Any],
    calendar: list[dict[str, Any]],
    input_hashes: dict[str, str],
    power_condition: str,
    official_eligible: bool,
) -> dict[str, Any]:
    """Materializa el contrato únicamente desde inputs bloqueados y valores efectivos."""
    configured = config["models"]
    locked = lock["models"]
    if (
        lock.get("schema_version") != config["schema_version"]
        or lock.get("benchmark_version") != config["benchmark_version"]
    ):
        raise ValueError("lock: versión incompatible con la configuración")
    if [item["name"] for item in locked] != configured:
        raise ValueError("lock.models: no coincide con config.models")
    base = public_base_url(api_base(config))
    if lock["ollama_base_url"] != base:
        raise ValueError("lock.ollama_base_url: no coincide con la configuración")
    identities = {item["name"]: item["digest"] for item in locked}
    plan = {
        "schema_version": 3,
        "benchmark_version": "0.3.0",
        "run_id": run_id,
        "runner": runner,
        "mode": mode,
        "created_at_utc": utc_now().isoformat(),
        "versions": {
            "package": BENCHMARK_VERSION,
            "runner": f"{runner}-runner-v2",
            "scheduler": f"{config['order_control']['policy']}-v2",
            "aggregation": "v2",
            "scoring": "v2",
            "report": "v2",
            "error_policy": "v2",
        },
        "ollama": {"base_url": base, "version": lock["ollama_server_version"]},
        "models": [{"name": name, "digest": identities[name]} for name in effective["models"]],
        "generation": config["generation"],
        "order_control": config["order_control"],
        "effective": effective,
        "overrides": overrides,
        "calendar": calendar,
        "input_hashes": input_hashes,
        "scoring_protocol": {
            "weights": config["weights"],
            "speed_weights": config["speed_weights"],
            "workload_weights": config["workload_weights"],
            "missing_metric_policy": config["missing_metric_policy"],
        },
        "environment": {
            "platform": platform.system(),
            "machine": platform.machine(),
            "power": power_condition,
        },
        "official_eligible": official_eligible,
    }
    return validate_run_plan(plan)


def create_run_plan(path: pathlib.Path, plan: dict[str, Any]) -> None:
    """Publica bytes completos de forma atómica, durable y sin sobrescribir."""
    validate_run_plan(plan)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = pathlib.Path(handle.name)
            json.dump(plan, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_compatible_run_plan(path: pathlib.Path, proposed: dict[str, Any]) -> dict[str, Any]:
    """Conserva los bytes originales y rechaza cambios relevantes antes del preflight."""
    original = validate_run_plan(read_json(path))
    stable = set(proposed) - {"created_at_utc"}
    if any(original[key] != proposed[key] for key in stable):
        raise ValueError("plan: modo, overrides o inputs incompatibles con la reanudación")
    return original
