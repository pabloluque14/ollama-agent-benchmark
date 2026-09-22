from __future__ import annotations

import argparse
import base64
import csv
import json
import pathlib
import re
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from typing import Any

from .common import (
    BENCHMARK_VERSION,
    CONFIG_PATH,
    ROOT,
    SCHEMA_VERSION,
    api_base,
    append_jsonl,
    config_fingerprint,
    detect_power,
    iter_jsonl,
    load_config,
    metric_rates,
    model_ps_snapshot,
    parse_json_strict,
    parse_swap_used_bytes,
    post_json,
    public_base_url,
    read_json,
    sha256_file,
    system_snapshot,
    unload_model,
    utc_now,
    validate_manifest_compatibility,
    wait_until_unloaded,
    write_json_atomic,
)
from .failures import (
    BenchmarkIntegrityFailure,
    ExecutionFailureError,
    classify_failure,
    record_integrity_failure,
    sanitize_text,
)
from .input_contracts import validate_dataset
from .primary_records import append_primary_record
from .resume import validate_resume_evidence
from .run_plan import (
    create_run_plan,
    make_run_plan,
    performance_calendar,
    preflight_run_plan,
    validate_planning_inputs,
    validate_run_plan,
)

WORKLOADS_PATH = ROOT / "datasets" / "performance_workloads_v2.json"


def inputs_from_performance_plan(plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Reconstruye la ejecución desde el plan original inmutable."""
    workloads_doc = parse_json_strict(
        base64.b64decode(
            plan["input_snapshots"]["datasets/performance_workloads_v2.json"]
        ).decode("utf-8")
    )
    by_id = {item["id"]: item for item in workloads_doc["workloads"]}
    effective = plan["effective"]
    config = {
        "models": effective["models"],
        "ollama": {"base_url": plan["ollama"]["base_url"]},
        "generation": plan["generation"],
        "order_control": plan["order_control"],
        "performance": {
            "cold_runs": effective["cold_runs"],
            "hot_runs": effective["hot_runs"],
            "ttft_runs": effective["ttft_runs"],
            "keep_alive": effective["keep_alive"],
            "pause_after_unload_seconds": effective["pause_after_unload_seconds"],
            "pause_between_models_seconds": effective["pause_between_models_seconds"],
        },
        **plan["scoring_protocol"],
    }
    lock = {
        "ollama_server_version": plan["ollama"]["version"],
        "models": plan["models"],
    }
    return config, [by_id[item] for item in effective["workload_ids"]], lock


def build_messages(workload: dict[str, Any]) -> list[dict[str, str]]:
    if "messages" in workload:
        return workload["messages"]
    builder = workload.get("builder") or {}
    repeated = str(builder.get("repeat_text", "")) * int(builder.get("repeat_count", 1))
    prompt = str(builder.get("prefix", "")) + repeated + str(builder.get("suffix", ""))
    return [{"role": "user", "content": prompt}]


def streaming_ttft(
    base: str,
    payload: dict[str, Any],
    workload: dict[str, Any] | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    body = json.dumps({**payload, "stream": True}).encode("utf-8")
    request = urllib.request.Request(
        base.rstrip("/") + "/api/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
    )
    started = time.monotonic()
    first = None
    final: dict[str, Any] | None = None
    chunks = 0
    content: list[str] = []
    thinking: list[str] = []
    tool_calls: list[Any] = []
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw in response:
            if not raw.strip():
                continue
            try:
                chunk = json.loads(raw)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ExecutionFailureError("stream NDJSON malformado") from exc
            if not isinstance(chunk, dict):
                raise ExecutionFailureError("chunk NDJSON no es un objeto")
            chunks += 1
            message = chunk.get("message") or {}
            if not isinstance(message, dict):
                raise ExecutionFailureError("message del stream no es un objeto")
            has_payload = bool(
                message.get("content") or message.get("thinking") or message.get("tool_calls")
            )
            if first is None and has_payload:
                first = time.monotonic() - started
            if isinstance(message.get("content"), str):
                content.append(message["content"])
            if isinstance(message.get("thinking"), str):
                thinking.append(message["thinking"])
            calls = message.get("tool_calls")
            if isinstance(calls, list):
                tool_calls.extend(calls)
            if chunk.get("done"):
                final = chunk
    if final is None:
        raise ExecutionFailureError("stream truncado o sin señal final")
    reconstructed = {
        **final,
        "message": {
            "role": "assistant",
            "content": "".join(content),
            "thinking": "".join(thinking),
            "tool_calls": tool_calls,
        },
    }
    compliance = (
        validate_workload_response(workload, reconstructed)
        if workload is not None
        else {
            "valid": first is not None,
            "checks": {"payload": first is not None},
            "failed_checks": [] if first is not None else ["payload"],
        }
    )
    return {
        "ttft_seconds": first if compliance["valid"] else None,
        "observed_ttft_seconds": first,
        "stream_total_seconds": time.monotonic() - started,
        "chunks": chunks,
        "final_metrics": metric_rates(final),
        "reconstructed_response": reconstructed,
        "workload_compliance": compliance,
    }


def run_response(
    base: str, model: str, workload: dict[str, Any], config: dict[str, Any], keep_alive: str
) -> tuple[dict[str, Any], float]:
    generation = config["generation"]
    options = {
        key: value
        for key, value in generation.items()
        if key not in {"think", "stream", "keep_alive"}
    }
    if workload.get("num_predict") is not None:
        options["num_predict"] = int(workload["num_predict"])
    payload = {
        "model": model,
        "messages": build_messages(workload),
        "think": generation.get("think", False),
        "stream": False,
        "keep_alive": keep_alive,
        "options": options,
    }
    started = time.monotonic()
    response = post_json(base.rstrip("/") + "/api/chat", payload, timeout=1200)
    return {"request": payload, "response": response}, time.monotonic() - started


def stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "stdev": None, "min": None, "max": None}
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def validate_workload_response(
    workload: dict[str, Any], response: dict[str, Any]
) -> dict[str, Any]:
    rules = workload.get("compliance", {})
    raw_message = response.get("message")
    message: dict[str, Any] = raw_message if isinstance(raw_message, dict) else {}
    content = str(message.get("content", ""))
    checks: dict[str, bool] = {
        "done": response.get("done") is True,
        "nonempty": bool(content.strip()),
    }
    eval_count = response.get("eval_count")
    if "min_output_tokens" in rules:
        checks["min_output_tokens"] = isinstance(eval_count, int) and eval_count >= int(
            rules["min_output_tokens"]
        )
    if "must_contain" in rules:
        checks["must_contain"] = all(
            str(value).casefold() in content.casefold() for value in rules["must_contain"]
        )
    if "must_contain_any" in rules:
        checks["must_contain_any"] = any(
            str(value).casefold() in content.casefold() for value in rules["must_contain_any"]
        )
    for index, pattern in enumerate(rules.get("required_regex", []), 1):
        checks[f"regex_{index}"] = re.search(str(pattern), content) is not None
    numbered = re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+", content)
    if "min_numbered_points" in rules:
        checks["min_numbered_points"] = len(numbered) >= int(rules["min_numbered_points"])
    if "max_numbered_points" in rules:
        checks["max_numbered_points"] = len(numbered) <= int(rules["max_numbered_points"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {"valid": not failed, "checks": checks, "failed_checks": failed}


def _weighted_metric(
    workloads: dict[str, Any], field: str, weights: dict[str, float]
) -> dict[str, Any]:
    values: list[tuple[float, float]] = []
    for workload_id, data in workloads.items():
        value = data.get(field, {}).get("median")
        if isinstance(value, (int, float)) and workload_id in weights:
            values.append((float(value), float(weights[workload_id])))
    if len(values) != len(workloads) or not values:
        return stats([])
    total_weight = sum(weight for _, weight in values)
    value = sum(metric * weight for metric, weight in values) / total_weight
    return {
        "count": len(values),
        "mean": value,
        "median": value,
        "stdev": None,
        "min": min(x for x, _ in values),
        "max": max(x for x, _ in values),
    }


def summarize(
    records_path: pathlib.Path,
    ttft_path: pathlib.Path,
    output_dir: pathlib.Path,
    workload_weights: dict[str, float] | None = None,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = list(iter_jsonl(records_path)) if records_path.is_file() else []
    ttft = list(iter_jsonl(ttft_path)) if ttft_path.is_file() else []
    for label, source_rows in (("rendimiento", records), ("TTFT", ttft)):
        keys = [row.get("execution_key") for row in source_rows]
        duplicate = next((key for key in keys if key is not None and keys.count(key) > 1), None)
        if duplicate is not None:
            raise ValueError(f"Ejecución {label} duplicada: {duplicate}")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        grouped[(item["model"], item["workload_id"])].append(item)

    rows: list[dict[str, Any]] = []
    models_summary: dict[str, Any] = {}
    for (model, workload_id), items in grouped.items():
        model_summary = models_summary.setdefault(
            model, {"records": 0, "runner_errors": 0, "invalid_records": 0, "workloads": {}}
        )
        model_summary["records"] += len(items)
        model_summary["runner_errors"] += sum(bool(x.get("runner_error")) for x in items)
        model_summary["invalid_records"] += sum(
            not x.get("workload_compliance", {}).get("valid", False) for x in items
        )
        valid = [
            x
            for x in items
            if not x.get("runner_error") and x.get("workload_compliance", {}).get("valid")
        ]
        hot = [x for x in valid if x["temperature_state"] == "hot"]
        cold = [
            x
            for x in valid
            if x["temperature_state"] == "cold" and x.get("cold_unload_verified") is True
        ]

        def metric(subset: list[dict[str, Any]], name: str) -> dict[str, Any]:
            return stats(
                [
                    float(x["metrics"][name])
                    for x in subset
                    if isinstance(x.get("metrics", {}).get(name), (int, float))
                ]
            )

        relevant_ttft = [
            x
            for x in ttft
            if x.get("model") == model
            and x.get("workload_id") == workload_id
            and not x.get("runner_error")
        ]
        workload_summary = {
            "records": len(items),
            "valid_records": len(valid),
            "hot_prompt_tps": metric(hot, "prompt_tokens_per_second"),
            "hot_generation_tps": metric(hot, "generation_tokens_per_second"),
            "hot_total_seconds": metric(hot, "total_seconds"),
            "cold_load_seconds": metric(cold, "load_seconds"),
            "size_vram_bytes": stats(
                [
                    float(x["model_ps"]["size_vram"])
                    for x in valid
                    if isinstance(x.get("model_ps"), dict)
                    and isinstance(x["model_ps"].get("size_vram"), int)
                ]
            ),
            "swap_delta_bytes": stats(
                [
                    float(x["swap_delta_bytes"])
                    for x in valid
                    if isinstance(x.get("swap_delta_bytes"), int)
                ]
            ),
            "ttft_seconds": stats(
                [
                    float(x["ttft_seconds"])
                    for x in relevant_ttft
                    if isinstance(x.get("ttft_seconds"), (int, float))
                ]
            ),
        }
        model_summary["workloads"][workload_id] = workload_summary
        for item in items:
            rows.append(
                {
                    "model": model,
                    "workload": item["workload_id"],
                    "temperature_state": item["temperature_state"],
                    "run_index": item["run_index"],
                    "wall_seconds": item.get("wall_seconds"),
                    "prompt_tps": item["metrics"].get("prompt_tokens_per_second"),
                    "generation_tps": item["metrics"].get("generation_tokens_per_second"),
                    "total_seconds": item["metrics"].get("total_seconds"),
                    "load_seconds": item["metrics"].get("load_seconds"),
                    "size_vram_bytes": (item.get("model_ps") or {}).get("size_vram"),
                    "swap_delta_bytes": item.get("swap_delta_bytes"),
                    "runner_error": item.get("runner_error"),
                    "workload_valid": item.get("workload_compliance", {}).get("valid"),
                }
            )

    if plan is not None:
        from .aggregation import aggregate_performance_cells

        models_summary = aggregate_performance_cells(plan, records, ttft)

    for _model, data in models_summary.items():
        workloads = data["workloads"]
        if workload_weights is None:
            weights = {key: 1.0 / len(workloads) for key in workloads} if workloads else {}
        else:
            weights = workload_weights
        fields = [
            "hot_prompt_tps",
            "hot_generation_tps",
            "hot_total_seconds",
            "cold_load_seconds",
            "size_vram_bytes",
            "swap_delta_bytes",
        ]
        if plan is None or plan["effective"]["ttft_runs"]:
            fields.append("ttft_seconds")
        data["aggregate"] = {field: _weighted_metric(workloads, field, weights) for field in fields}

    csv_path = output_dir / "performance_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["model"])
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "created_at_utc": utc_now().isoformat(),
        "workload_weights": workload_weights,
        "models": models_summary,
        "csv": str(csv_path),
    }
    write_json_atomic(output_dir / "performance_summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oab performance",
        description="Mide carga, prompt, generación, TTFT y memoria de modelos Ollama.",
    )
    parser.add_argument(
        "--mode", choices=("dry-run", "smoke", "official-performance"), default="dry-run"
    )
    parser.add_argument("--models", help="Modelos separados por comas; deben existir en el lock")
    parser.add_argument("--workloads", help="IDs de cargas separados por comas")
    parser.add_argument("--run-id", help="Identificador estable para guardar o reanudar")
    parser.add_argument(
        "--allow-battery",
        action="store_true",
        default=None,
        help="Permite batería, pero marca un run oficial como exploratorio",
    )
    parser.add_argument("--resume", action="store_true", help="Reanuda un run compatible")
    args = parser.parse_args(argv)

    if args.resume and not args.run_id:
        print("ERROR: --resume requiere --run-id para localizar el plan original.", file=sys.stderr)
        return 4
    run_id = args.run_id or f"{args.mode}_{utc_now().strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = ROOT / "runs" / run_id
    records_path = run_dir / "performance_records.jsonl"
    ttft_path = run_dir / "ttft_records.jsonl"
    manifest_path = run_dir / "performance_manifest.json"
    plan_path = run_dir / "plan.json"
    integrity_path = run_dir / "integrity.jsonl"
    lock_path = CONFIG_PATH.parent / "models.lock.json"
    if args.resume and not plan_path.exists():
        detail = (
            "run v2 sin plan v3; no hay migración ni reanudación compatible"
            if manifest_path.exists()
            else "run huérfano sin plan v3"
        )
        print(f"ERROR: --resume rechazado: {detail}.", file=sys.stderr)
        return 4

    try:
        if args.resume:
            run_plan = validate_run_plan(read_json(plan_path))
            if run_plan["runner"] != "performance" or run_plan["mode"] != args.mode:
                raise ValueError("modo o runner distinto del plan original")
            effective = run_plan["effective"]
            requested_models = (
                [item.strip() for item in args.models.split(",") if item.strip()]
                if args.models
                else None
            )
            requested_workloads = (
                [item.strip() for item in args.workloads.split(",") if item.strip()]
                if args.workloads
                else None
            )
            if requested_models is not None and requested_models != effective["models"]:
                raise ValueError("override de modelos distinto del plan original")
            if requested_workloads is not None and requested_workloads != effective["workload_ids"]:
                raise ValueError("override de workloads distinto del plan original")
            if (
                args.allow_battery is not None
                and args.allow_battery != run_plan["overrides"]["allow_battery"]
            ):
                raise ValueError("override allow_battery distinto del plan original")
            config, workloads, lock = inputs_from_performance_plan(run_plan)
            models = effective["models"]
            cold_runs = effective["cold_runs"]
            hot_runs = effective["hot_runs"]
            ttft_runs = effective["ttft_runs"]
        else:
            config = load_config(CONFIG_PATH)
            workloads_doc = read_json(WORKLOADS_PATH)
            lock = read_json(lock_path)
            validate_planning_inputs(config, lock)
            validate_dataset("workloads", workloads_doc)
            models = config["models"]
            if args.models:
                requested_models = [
                    item.strip() for item in args.models.split(",") if item.strip()
                ]
                unknown = sorted(set(requested_models) - set(models))
                if unknown:
                    raise ValueError(f"modelos no bloqueados: {unknown}")
                models = requested_models
            workloads = workloads_doc["workloads"]
            all_workloads = {item["id"]: item for item in workloads}
            if args.workloads:
                requested_workloads = [
                    item.strip() for item in args.workloads.split(",") if item.strip()
                ]
                unknown = sorted(set(requested_workloads) - set(all_workloads))
                if unknown:
                    raise ValueError(f"workloads desconocidos: {unknown}")
                workloads = [all_workloads[item] for item in requested_workloads]
            elif args.mode == "smoke":
                workloads = workloads[:1]
            perf = config["performance"]
            cold_runs = 1 if args.mode == "smoke" else int(perf.get("cold_runs", 3))
            hot_runs = 1 if args.mode == "smoke" else int(perf.get("hot_runs", 5))
            ttft_runs = 0 if args.mode == "smoke" else int(perf.get("ttft_runs", 3))
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR de validación: {exc}", file=sys.stderr)
        return 4 if args.resume else 1

    by_id = {item["id"]: item for item in workloads}
    perf = config["performance"]
    print("===== PLAN DE RENDIMIENTO =====")
    print(f"Modo: {args.mode}")
    print(f"Modelos: {', '.join(models)}")
    print(f"Workloads: {', '.join(x['id'] for x in workloads)}")
    print(f"Por modelo/workload: {cold_runs} fría + {hot_runs} calientes + {ttft_runs} TTFT")
    print(f"Respuestas no streaming: {len(models) * len(workloads) * (cold_runs + hot_runs)}")
    print()
    power = detect_power()
    allow_battery = bool(args.allow_battery)
    eligible = (
        run_plan["official_eligible"]
        if args.resume
        else args.mode == "official-performance"
        and power["condition"] in {"ac_power", "not_applicable"}
        and not allow_battery
    )
    if (
        args.mode == "official-performance"
        and power["condition"] == "battery"
        and not allow_battery
    ):
        print("ERROR: el modo oficial exige AC Power en macOS.", file=sys.stderr)
        return 3

    base = api_base(config)
    if run_dir.exists() and not args.resume:
        print(f"ERROR: ya existe {run_dir}; usa --resume o cambia --run-id", file=sys.stderr)
        return 4
    keep_alive = perf["keep_alive"]
    after_unload = perf["pause_after_unload_seconds"]
    between_models = perf["pause_between_models_seconds"]
    try:
        if not args.resume:
            calendar = performance_calendar(
                [item for item in lock["models"] if item["name"] in models],
                [item["id"] for item in workloads],
                cold_runs,
                hot_runs,
                ttft_runs,
                config["order_control"]["seed"],
            )
            run_plan = make_run_plan(
                run_id=run_id,
                runner="performance",
                mode=args.mode,
                config=config,
                lock=lock,
                effective={
                    "models": models,
                    "workload_ids": [item["id"] for item in workloads],
                    "cold_runs": cold_runs,
                    "hot_runs": hot_runs,
                    "ttft_runs": ttft_runs,
                    "keep_alive": keep_alive,
                    "pause_after_unload_seconds": after_unload,
                    "pause_between_models_seconds": between_models,
                },
                overrides={
                    "models": [x.strip() for x in args.models.split(",") if x.strip()]
                    if args.models
                    else None,
                    "workloads": [x.strip() for x in args.workloads.split(",") if x.strip()]
                    if args.workloads
                    else None,
                    "allow_battery": allow_battery,
                },
                calendar=calendar,
                input_hashes={
                    str(CONFIG_PATH.relative_to(ROOT)): sha256_file(CONFIG_PATH),
                    str(lock_path.relative_to(ROOT)): sha256_file(lock_path),
                    str(WORKLOADS_PATH.relative_to(ROOT)): sha256_file(WORKLOADS_PATH),
                },
                input_snapshots={
                    str(WORKLOADS_PATH.relative_to(ROOT)): base64.b64encode(
                        WORKLOADS_PATH.read_bytes()
                    ).decode("ascii")
                },
                power_condition=power["condition"],
                official_eligible=eligible,
            )
        if args.mode == "dry-run":
            print("Resultado: OK. Plan validado. No se llamó a Ollama ni se guardaron mediciones.")
            return 0
        if not args.resume:
            create_run_plan(plan_path, run_plan)
        completed_by_kind = validate_resume_evidence(
            run_plan,
            {"performance": records_path, "ttft": ttft_path},
            integrity_path,
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR materializando plan: {exc}", file=sys.stderr)
        return 4

    try:
        preflight_run_plan(run_plan)
    except Exception as exc:
        print(f"ERROR verificando lock/Ollama: {exc}", file=sys.stderr)
        return 1

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "runner_version": "performance-runner-v3",
        "run_id": run_id,
        "mode": args.mode,
        "created_at_utc": utc_now().isoformat(),
        "power_at_start": power,
        "eligible_for_main_score": eligible,
        "models": models,
        "workloads": [x["id"] for x in workloads],
        "cold_runs": cold_runs,
        "hot_runs": hot_runs,
        "ttft_runs": ttft_runs,
        "ollama_server_version": lock.get("ollama_server_version"),
        "ollama_base_url": public_base_url(base),
        "model_identities": [
            {"name": item.get("name"), "digest": item.get("digest")}
            for item in lock.get("models", [])
            if item.get("name") in models
        ],
        "generation": config["generation"],
        "order_control": config["order_control"],
        "config_fingerprint": config_fingerprint(config),
        "workloads_hash": run_plan["input_hashes"][
            "datasets/performance_workloads_v2.json"
        ],
        "scoring_protocol": {
            "weights": config["weights"],
            "speed_weights": config["speed_weights"],
            "workload_weights": config["workload_weights"],
            "missing_metric_policy": config["missing_metric_policy"],
        },
    }
    if manifest_path.exists() and not args.resume:
        try:
            validate_manifest_compatibility(
                json.loads(manifest_path.read_text(encoding="utf-8")),
                manifest,
                (
                    "schema_version",
                    "benchmark_version",
                    "runner_version",
                    "mode",
                    "models",
                    "workloads",
                    "cold_runs",
                    "hot_runs",
                    "ttft_runs",
                    "ollama_server_version",
                    "ollama_base_url",
                    "model_identities",
                    "generation",
                    "order_control",
                    "config_fingerprint",
                    "workloads_hash",
                    "scoring_protocol",
                ),
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 5
    elif not args.resume:
        write_json_atomic(manifest_path, manifest)
    completed = completed_by_kind["performance"]
    completed_ttft = completed_by_kind["ttft"]

    total = len(models) * len(workloads) * (cold_runs + hot_runs)
    done = len(completed)

    append_jsonl(
        run_dir / "performance_system_snapshots.jsonl",
        {"event": "run_start", "snapshot": system_snapshot(base)},
    )
    try:
        for entry in run_plan["calendar"]:
            workload = by_id[entry["target_id"]]
            model = entry["model"]
            state = entry["measurement_type"]
            index = entry["repetition"]
            key = entry["execution_key"]
            print(f"===== {workload['id']} / {model} / {state} {index} =====")
            if state == "ttft":
                if key in completed_ttft:
                    print(f"[SKIP] {key}")
                    continue
                payload = {
                    "model": model,
                    "messages": build_messages(workload),
                    "think": config["generation"].get("think", False),
                    "keep_alive": keep_alive,
                    "options": {
                        **{
                            k: v
                            for k, v in config["generation"].items()
                            if k not in {"think", "stream", "keep_alive"}
                        },
                        "num_predict": int(
                            workload.get(
                                "num_predict", config["generation"].get("num_predict", 256)
                            )
                        ),
                    },
                }
                started_ttft = utc_now()
                try:
                    result = streaming_ttft(base, payload, workload)
                    error = None
                except Exception as exc:
                    if classify_failure(exc) == "benchmark_integrity_failure":
                        record_integrity_failure(
                            integrity_path,
                            phase="execution",
                            component="ttft",
                            operation="streaming_ttft",
                            exc=exc,
                            execution_key=key,
                        )
                        raise BenchmarkIntegrityFailure(
                            "fallo de integridad durante la medición TTFT"
                        ) from None
                    result = {
                        "ttft_seconds": None,
                        "observed_ttft_seconds": None,
                        "stream_total_seconds": None,
                        "chunks": 0,
                        "final_metrics": {},
                        "reconstructed_response": {},
                        "workload_compliance": {
                            "valid": False,
                            "checks": {},
                            "failed_checks": ["execution_failure"],
                        },
                    }
                    error = sanitize_text(f"{type(exc).__name__}: {exc}")
                append_primary_record(
                    ttft_path,
                    "ttft",
                    {
                        "schema_version": 3,
                        "run_id": run_id,
                        "execution_key": key,
                        "measurement_key": key,
                        "status": "completed" if error is None else "execution_failure",
                        "model": model,
                        "workload_id": workload["id"],
                        "run_index": index,
                        "eligible_for_main_score": eligible,
                        "power_condition": power["condition"],
                        "started_at_utc": started_ttft.isoformat(),
                        "completed_at_utc": utc_now().isoformat(),
                        "runner_error": error,
                        **result,
                    },
                    run_plan,
                )
                if error is None:
                    completed_ttft.add(key)
                continue
            if key in completed:
                print(f"[SKIP] {key}")
                continue
            if state == "cold":
                unload_model(model, base)
                unloaded = wait_until_unloaded(model, base)
                if after_unload:
                    time.sleep(after_unload)
            else:
                unloaded = None
            swap_before = parse_swap_used_bytes()
            started = utc_now()
            error = None
            try:
                exchange, wall = run_response(base, model, workload, config, keep_alive)
                metrics = metric_rates(exchange["response"])
                ps = model_ps_snapshot(model, base)
                compliance = validate_workload_response(workload, exchange["response"])
            except Exception as exc:
                if classify_failure(exc) == "benchmark_integrity_failure":
                    record_integrity_failure(
                        integrity_path,
                        phase="execution",
                        component="performance",
                        operation="run_response",
                        exc=exc,
                        execution_key=key,
                    )
                    raise BenchmarkIntegrityFailure(
                        "fallo de integridad durante la medición de rendimiento"
                    ) from None
                exchange, wall, metrics, ps = {}, None, {}, None
                compliance = {"valid": False, "checks": {}, "failed_checks": ["runner_error"]}
                error = sanitize_text(f"{type(exc).__name__}: {exc}")
            if state == "cold" and not unloaded:
                error = error or "ColdUnloadError: no se confirmó la descarga del modelo"
                compliance = {
                    "valid": False,
                    "checks": {"cold_unload_verified": False},
                    "failed_checks": ["cold_unload_verified"],
                }
            swap_after = parse_swap_used_bytes()
            record = {
                "schema_version": 3,
                "execution_key": key,
                "measurement_key": key,
                "status": "completed" if error is None else "execution_failure",
                "run_id": run_id,
                "eligible_for_main_score": eligible,
                "power_condition": power["condition"],
                "model": model,
                "workload_id": workload["id"],
                "temperature_state": state,
                "cold_unload_verified": unloaded,
                "run_index": index,
                "started_at_utc": started.isoformat(),
                "completed_at_utc": utc_now().isoformat(),
                "wall_seconds": wall,
                "metrics": metrics,
                "model_ps": ps,
                "swap_before_bytes": swap_before,
                "swap_after_bytes": swap_after,
                "swap_delta_bytes": (swap_after - swap_before)
                if swap_before is not None and swap_after is not None
                else None,
                "runner_error": error,
                "workload_compliance": compliance,
                "exchange": exchange,
            }
            append_primary_record(records_path, "performance", record, run_plan)
            if error is None:
                completed.add(key)
            done += 1
            print(
                f"[{state.upper()}] {done}/{total} "
                f"gen={metrics.get('generation_tokens_per_second')} tok/s "
                f"prompt={metrics.get('prompt_tokens_per_second')} tok/s "
                f"error={error or '-'}"
            )
    except BenchmarkIntegrityFailure as exc:
        print(f"ERROR: {sanitize_text(exc)}", file=sys.stderr)
        return 6
    except KeyboardInterrupt:
        print("Interrumpido. Usa --resume para continuar.", file=sys.stderr)
        return 130
    finally:
        for model in models:
            unload_model(model, base)
        append_jsonl(
            run_dir / "performance_system_snapshots.jsonl",
            {"event": "run_end", "snapshot": system_snapshot(base)},
        )

    summary = summarize(records_path, ttft_path, run_dir, config["workload_weights"], plan=run_plan)
    print("===== RESUMEN DE RENDIMIENTO =====")
    for model, item in summary["models"].items():
        print(
            f"- {model}: gen agregada={item['aggregate']['hot_generation_tps']['median']} tok/s; "
            f"prompt agregada={item['aggregate']['hot_prompt_tps']['median']} tok/s; "
            f"carga fría agregada={item['aggregate']['cold_load_seconds']['median']} s"
        )
    print(f"Run: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
