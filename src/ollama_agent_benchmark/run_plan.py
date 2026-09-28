"""Contrato local y persistencia inmutable del plan del run v3."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import pathlib
import platform
import random
import re
import tempfile
from datetime import datetime
from functools import cache
from typing import Any

from .common import (
    BENCHMARK_VERSION,
    api_base,
    get_json,
    parse_json_strict,
    public_base_url,
    read_json,
    utc_now,
)


@cache
def _schema(name: str) -> dict[str, Any]:
    path = pathlib.Path(__file__).parent / "contracts" / f"{name}.schema.json"
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
        if "maxItems" in rule and len(value) > rule["maxItems"]:
            raise ValueError(f"{path}: demasiados elementos")
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
    from .input_contracts import validate_dataset

    schema = _schema("run-plan-v3")
    _validate(plan, schema, "plan", schema)
    if plan["runner"] == "functional":
        if plan["mode"] not in {"dry-run", "smoke", "official-functional"}:
            raise ValueError("plan.mode: incompatible con runner funcional")
        if "case_ids" not in plan["effective"] or "case_ids" not in plan["overrides"]:
            raise ValueError("plan.effective: no corresponde al runner funcional")
    else:
        if plan["mode"] not in {"dry-run", "smoke", "official-performance"}:
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
    required_snapshots = (
        {"datasets/benchmark_cases_v2.json", "datasets/fixtures_v2.json", "datasets/tools_v2.json"}
        if plan["runner"] == "functional"
        else {"datasets/performance_workloads_v2.json"}
    )
    if set(plan["input_snapshots"]) != required_snapshots:
        raise ValueError("plan.input_snapshots: faltan o sobran inputs metodológicos")
    if set(plan["input_hashes"]) != required_snapshots | {
        "config/benchmark.json",
        "config/models.lock.json",
    }:
        raise ValueError("plan.input_hashes: faltan o sobran hashes de planificación")
    snapshot_kinds = {
        "datasets/benchmark_cases_v2.json": "cases",
        "datasets/fixtures_v2.json": "fixtures",
        "datasets/tools_v2.json": "tools",
        "datasets/performance_workloads_v2.json": "workloads",
    }
    snapshots = {}
    for path, encoded in plan["input_snapshots"].items():
        try:
            payload = base64.b64decode(encoded, validate=True)
            document = parse_json_strict(payload.decode("utf-8"))
        except (binascii.Error, UnicodeError, ValueError) as exc:
            raise ValueError(f"plan.input_snapshots.{path}: JSON/base64 inválido") from exc
        if hashlib.sha256(payload).hexdigest() != plan["input_hashes"].get(path):
            raise ValueError(f"plan.input_snapshots.{path}: hash incompatible")
        if not isinstance(document, dict) or document.get("schema_version") != 2:
            raise ValueError(f"plan.input_snapshots.{path}: versión de input incompatible")
        validate_dataset(snapshot_kinds[path], document)
        snapshots[path] = document
    if plan["runner"] == "functional":
        cases = snapshots["datasets/benchmark_cases_v2.json"].get("cases")
        if not isinstance(cases, list) or any(not isinstance(case, dict) for case in cases):
            raise ValueError("plan.input_snapshots: casos inválidos")
        ids = [case.get("id") for case in cases]
        if (
            any(not isinstance(item, str) for item in ids)
            or len(ids) != len(set(ids))
            or not set(plan["effective"]["case_ids"]) <= set(ids)
        ):
            raise ValueError("plan.input_snapshots: casos planificados ausentes o duplicados")
    else:
        workloads = snapshots["datasets/performance_workloads_v2.json"].get("workloads")
        if not isinstance(workloads, list) or any(not isinstance(item, dict) for item in workloads):
            raise ValueError("plan.input_snapshots: workloads inválidos")
        ids = [item.get("id") for item in workloads]
        if (
            any(not isinstance(item, str) for item in ids)
            or len(ids) != len(set(ids))
            or not set(plan["effective"]["workload_ids"]) <= set(ids)
        ):
            raise ValueError("plan.input_snapshots: workloads planificados ausentes o duplicados")
    effective = plan["effective"]
    if plan["measurement_protocol"] != _measurement_protocol(plan["runner"], effective):
        raise ValueError("plan.measurement_protocol: métricas o políticas incompatibles")
    expected_versions = {
        "package": BENCHMARK_VERSION,
        "runner": f"{plan['runner']}-runner-v3",
        "scheduler": "balanced-block-v3",
        "aggregation": "v3",
        "scoring": "v3",
        "report": "v3",
        "error_policy": "classified-v3",
    }
    if plan["versions"] != expected_versions:
        raise ValueError("plan.versions: implementación o algoritmo incompatible")
    if plan["runner"] == "functional":
        expected_calendar = functional_calendar(
            plan["models"],
            effective["case_ids"],
            effective["repetitions"],
            plan["order_control"]["seed"],
        )
    else:
        expected_calendar = performance_calendar(
            plan["models"],
            effective["workload_ids"],
            effective["cold_runs"],
            effective["hot_runs"],
            effective["ttft_runs"],
            plan["order_control"]["seed"],
        )
    if plan["calendar"] != expected_calendar:
        raise ValueError("plan.calendar: calendario o claves incompatibles con inputs y seed")
    if plan["official_eligible"] and (
        not plan["mode"].startswith("official-") or plan["overrides"]["allow_battery"]
    ):
        raise ValueError("plan.official_eligible: modo u override no oficial")
    if plan["official_eligible"] and plan["environment"]["power"] not in {
        "ac_power",
        "not_applicable",
    }:
        raise ValueError("plan.official_eligible: alimentación incompatible")
    return plan


def _measurement_protocol(runner: str, effective: dict[str, Any]) -> dict[str, Any]:
    metrics = (
        ["case_pass", "track_success_rate"]
        if runner == "functional"
        else [
            "hot_prompt_tps",
            "hot_generation_tps",
            "hot_total_seconds",
            "cold_load_seconds",
            "size_vram_bytes",
            "swap_delta_bytes",
        ]
    )
    if runner == "performance" and effective["ttft_runs"]:
        metrics.append("ttft_seconds")
    return {
        "metrics": metrics,
        "compliance_policy": "dataset-contract-v2",
        "sample_validity_policy": "all-required-evidence-v3",
        "cell_completeness_policy": "all-planned-samples-v3",
        "execution_failure_policy": "terminal-without-positive-metrics-v3",
        "integrity_failure_policy": "journal-nonterminal-v3",
    }


def validate_planning_inputs(config: Any, lock: Any = None) -> None:
    """Contrato v3 de los documentos fuente de configuración y lock, sin coerciones."""
    schema = _schema("planning-inputs-v3")
    _validate({"schema_version": 3, "config": config, "lock": lock}, schema, "inputs", schema)
    if api_base(config) != public_base_url(api_base(config)):
        raise ValueError("inputs.config.ollama.base_url: credenciales o parámetros no permitidos")
    for group in ("weights", "speed_weights", "workload_weights"):
        if not math.isclose(sum(config[group].values()), 1.0, abs_tol=1e-12):
            raise ValueError(f"inputs.config.{group}: los pesos no suman 1")
    if lock is not None:
        names = [item["name"] for item in lock["models"]]
        if names != config["models"]:
            raise ValueError("inputs.lock.models: no coincide con config.models")
        if lock["ollama_base_url"] != public_base_url(api_base(config)):
            raise ValueError("inputs.lock.ollama_base_url: no coincide con config.ollama.base_url")


def _balanced_orders(
    identities: list[dict[str, str]], seed: int, block: str, repetitions: int
) -> list[list[str]]:
    ordered = sorted((item["name"], item["digest"]) for item in identities)
    if not ordered or len({name for name, _digest in ordered}) != len(ordered):
        raise ValueError("plan.models: identidades vacías o duplicadas")
    encoded = json.dumps([seed, block, ordered], ensure_ascii=False, separators=(",", ":"))
    rng = random.Random(int(hashlib.sha256(encoded.encode("utf-8")).hexdigest(), 16))
    names = [name for name, _digest in ordered]
    rng.shuffle(names)
    offset = rng.randrange(len(names))
    return [
        names[(offset + rep) % len(names) :] + names[: (offset + rep) % len(names)]
        for rep in range(repetitions)
    ]


def functional_calendar(
    identities: list[dict[str, str]], case_ids: list[str], repetitions: int, seed: int
) -> list[dict[str, Any]]:
    """Calendario funcional equilibrado por caso, independiente del orden configurado."""
    orders = _balanced_orders(identities, seed, "functional", repetitions)
    calendar = []
    for rep, names in enumerate(orders, 1):
        cases = list(case_ids)
        random.Random(seed + rep - 1).shuffle(cases)
        for position, model in enumerate(names, 1):
            for case_id in cases:
                calendar.append(
                    {
                        "execution_key": json.dumps(
                            ["functional", model, case_id, rep, position],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        "model": model,
                        "target_id": case_id,
                        "repetition": rep,
                        "measurement_type": "functional",
                        "block": case_id,
                        "position": position,
                    }
                )
    return calendar


def performance_calendar(
    identities: list[dict[str, str]],
    workload_ids: list[str],
    cold_runs: int,
    hot_runs: int,
    ttft_runs: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Calendario de cada workload/tipo con rotación equilibrada entre muestras."""
    calendar = []
    for workload in workload_ids:
        for state, count in (("cold", cold_runs), ("hot", hot_runs), ("ttft", ttft_runs)):
            for index, names in enumerate(
                _balanced_orders(identities, seed, f"{workload}:{state}", count), 1
            ):
                for position, model in enumerate(names, 1):
                    calendar.append(
                        {
                            "execution_key": json.dumps(
                                ["performance", model, workload, state, index, position],
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                            "model": model,
                            "target_id": workload,
                            "repetition": index,
                            "measurement_type": state,
                            "block": f"{workload}:{state}",
                            "position": position,
                        }
                    )
    return calendar


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
    input_snapshots: dict[str, str],
    power_condition: str,
    official_eligible: bool,
) -> dict[str, Any]:
    """Materializa el contrato únicamente desde inputs bloqueados y valores efectivos."""
    validate_planning_inputs(config, lock)
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
            "runner": f"{runner}-runner-v3",
            "scheduler": "balanced-block-v3",
            "aggregation": "v3",
            "scoring": "v3",
            "report": "v3",
            "error_policy": "classified-v3",
        },
        "ollama": {"base_url": base, "version": lock["ollama_server_version"]},
        "models": [{"name": name, "digest": identities[name]} for name in effective["models"]],
        "generation": config["generation"],
        "order_control": config["order_control"],
        "effective": effective,
        "overrides": overrides,
        "calendar": calendar,
        "input_hashes": input_hashes,
        "input_snapshots": input_snapshots,
        "scoring_protocol": {
            "weights": config["weights"],
            "speed_weights": config["speed_weights"],
            "workload_weights": config["workload_weights"],
            "missing_metric_policy": config["missing_metric_policy"],
        },
        "measurement_protocol": _measurement_protocol(runner, effective),
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
    if plan["mode"] == "dry-run":
        raise ValueError("dry-run no puede publicar evidencia canónica")
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


def preflight_run_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Contrasta el servidor observable solo con las identidades ya fijadas en el plan."""
    validate_run_plan(plan)
    base = plan["ollama"]["base_url"]
    version = get_json(base + "/api/version", timeout=10)
    if version.get("version") != plan["ollama"]["version"]:
        raise RuntimeError("preflight: versión de Ollama distinta del plan")
    tags = get_json(base + "/api/tags", timeout=30)
    models = tags.get("models")
    if not isinstance(models, list):
        raise RuntimeError("preflight: inventario de modelos inválido")
    actual = {item.get("name"): item.get("digest") for item in models if isinstance(item, dict)}
    if any(actual.get(item["name"]) != item["digest"] for item in plan["models"]):
        raise RuntimeError("preflight: digest o modelo distinto del plan")
    return {"version": version, "tags": tags}
