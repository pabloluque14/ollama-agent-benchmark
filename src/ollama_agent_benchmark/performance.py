from __future__ import annotations

import argparse
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
    parse_swap_used_bytes,
    post_json,
    public_base_url,
    sha256_file,
    system_snapshot,
    unload_model,
    utc_now,
    validate_manifest_compatibility,
    verify_lock,
    wait_until_unloaded,
    write_json_atomic,
)

WORKLOADS_PATH = ROOT / "datasets" / "performance_workloads_v2.json"


def build_messages(workload: dict[str, Any]) -> list[dict[str, str]]:
    if "messages" in workload:
        return workload["messages"]
    builder = workload.get("builder") or {}
    repeated = str(builder.get("repeat_text", "")) * int(builder.get("repeat_count", 1))
    prompt = str(builder.get("prefix", "")) + repeated + str(builder.get("suffix", ""))
    return [{"role": "user", "content": prompt}]


def streaming_ttft(base: str, payload: dict[str, Any], timeout: int = 900) -> dict[str, Any]:
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
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw in response:
            if not raw.strip():
                continue
            chunk = json.loads(raw)
            chunks += 1
            message = chunk.get("message") or {}
            has_payload = bool(
                message.get("content") or message.get("thinking") or message.get("tool_calls")
            )
            if first is None and has_payload:
                first = time.monotonic() - started
            if chunk.get("done"):
                final = chunk
    return {
        "ttft_seconds": first,
        "stream_total_seconds": time.monotonic() - started,
        "chunks": chunks,
        "final_metrics": metric_rates(final or {}),
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

    for _model, data in models_summary.items():
        workloads = data["workloads"]
        if workload_weights is None:
            weights = {key: 1.0 / len(workloads) for key in workloads} if workloads else {}
        else:
            weights = workload_weights
        data["aggregate"] = {
            field: _weighted_metric(workloads, field, weights)
            for field in (
                "hot_prompt_tps",
                "hot_generation_tps",
                "hot_total_seconds",
                "cold_load_seconds",
                "size_vram_bytes",
                "swap_delta_bytes",
                "ttft_seconds",
            )
        }

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
        help="Permite batería, pero marca un run oficial como exploratorio",
    )
    parser.add_argument("--resume", action="store_true", help="Reanuda un run compatible")
    args = parser.parse_args(argv)

    try:
        config = load_config(CONFIG_PATH)
        workloads_doc = json.loads(WORKLOADS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR de validación: {exc}", file=sys.stderr)
        return 1

    models = config["models"]
    if args.models:
        requested = [x.strip() for x in args.models.split(",") if x.strip()]
        unknown = sorted(set(requested) - set(models))
        if unknown:
            print(f"ERROR: modelos no bloqueados: {unknown}", file=sys.stderr)
            return 1
        models = requested

    workloads = workloads_doc["workloads"]
    by_id = {x["id"]: x for x in workloads}
    if args.workloads:
        ids = [x.strip() for x in args.workloads.split(",") if x.strip()]
        unknown = sorted(set(ids) - set(by_id))
        if unknown:
            print(f"ERROR: workloads desconocidos: {unknown}", file=sys.stderr)
            return 1
        workloads = [by_id[x] for x in ids]
    elif args.mode == "smoke":
        workloads = workloads[:1]

    perf = config["performance"]
    cold_runs = 1 if args.mode == "smoke" else int(perf.get("cold_runs", 3))
    hot_runs = 1 if args.mode == "smoke" else int(perf.get("hot_runs", 5))
    ttft_runs = 0 if args.mode == "smoke" else int(perf.get("ttft_runs", 3))
    print("===== PLAN DE RENDIMIENTO =====")
    print(f"Modo: {args.mode}")
    print(f"Modelos: {', '.join(models)}")
    print(f"Workloads: {', '.join(x['id'] for x in workloads)}")
    print(f"Por modelo/workload: {cold_runs} fría + {hot_runs} calientes + {ttft_runs} TTFT")
    print(f"Respuestas no streaming: {len(models) * len(workloads) * (cold_runs + hot_runs)}")
    print()
    if args.mode == "dry-run":
        print("Resultado: OK. No se llamó a Ollama ni se cargó ningún modelo.")
        return 0

    try:
        lock = verify_lock(config)
    except Exception as exc:
        print(f"ERROR verificando lock/Ollama: {exc}", file=sys.stderr)
        return 1

    power = detect_power()
    eligible = (
        args.mode == "official-performance"
        and power["condition"] in {"ac_power", "not_applicable"}
        and not args.allow_battery
    )
    if (
        args.mode == "official-performance"
        and power["condition"] == "battery"
        and not args.allow_battery
    ):
        print("ERROR: el modo oficial exige AC Power en macOS.", file=sys.stderr)
        return 3

    base = api_base(config)
    run_id = args.run_id or f"{args.mode}_{utc_now().strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = ROOT / "runs" / run_id
    records_path = run_dir / "performance_records.jsonl"
    ttft_path = run_dir / "ttft_records.jsonl"
    manifest_path = run_dir / "performance_manifest.json"
    if run_dir.exists() and not args.resume:
        print(f"ERROR: ya existe {run_dir}; usa --resume o cambia --run-id", file=sys.stderr)
        return 4
    if args.resume and not manifest_path.exists():
        print(
            "ERROR: --resume exige un manifest existente; no se mezclará un run huérfano",
            file=sys.stderr,
        )
        return 4
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "runner_version": "performance-runner-v2",
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
        "workloads_hash": sha256_file(WORKLOADS_PATH),
        "scoring_protocol": {
            "weights": config["weights"],
            "speed_weights": config["speed_weights"],
            "workload_weights": config["workload_weights"],
            "missing_metric_policy": config["missing_metric_policy"],
        },
    }
    if manifest_path.exists():
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
    else:
        write_json_atomic(manifest_path, manifest)
    completed = (
        {
            item["execution_key"]
            for item in iter_jsonl(records_path)
            if not item.get("runner_error")
            and not str(item.get("execution_key", "")).startswith("failed:")
        }
        if records_path.is_file()
        else set()
    )
    completed_ttft = (
        {
            item["execution_key"]
            for item in iter_jsonl(ttft_path)
            if not item.get("runner_error") and isinstance(item.get("execution_key"), str)
        }
        if ttft_path.is_file()
        else set()
    )

    keep_alive = str(perf.get("keep_alive", "5m"))
    after_unload = float(perf.get("pause_after_unload_seconds", 10))
    between_models = float(perf.get("pause_between_models_seconds", 30))
    order = models
    total = len(models) * len(workloads) * (cold_runs + hot_runs)
    done = len(completed)

    append_jsonl(
        run_dir / "performance_system_snapshots.jsonl",
        {"event": "run_start", "snapshot": system_snapshot(base)},
    )
    try:
        for workload_index, workload in enumerate(workloads):
            sequence = order[workload_index % len(order) :] + order[: workload_index % len(order)]
            for model in sequence:
                print(f"===== {workload['id']} / {model} =====")
                for state, count in (("cold", cold_runs), ("hot", hot_runs)):
                    for index in range(1, count + 1):
                        key = f"{model}:{workload['id']}:{state}:{index}"
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
                            exchange, wall, metrics, ps = {}, None, {}, None
                            compliance = {
                                "valid": False,
                                "checks": {},
                                "failed_checks": ["runner_error"],
                            }
                            error = f"{type(exc).__name__}: {exc}"
                        if state == "cold" and not unloaded:
                            error = (
                                error or "ColdUnloadError: no se confirmó la descarga del modelo"
                            )
                            compliance = {
                                "valid": False,
                                "checks": {"cold_unload_verified": False},
                                "failed_checks": ["cold_unload_verified"],
                            }
                        swap_after = parse_swap_used_bytes()
                        record = {
                            "schema_version": SCHEMA_VERSION,
                            "execution_key": key
                            if error is None
                            else f"failed:{key}:{utc_now().isoformat()}",
                            "measurement_key": key,
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
                        append_jsonl(records_path, record)
                        if error is None:
                            completed.add(key)
                        done += 1
                        print(
                            f"[{state.upper()}] {done}/{total} "
                            f"gen={metrics.get('generation_tokens_per_second')} tok/s "
                            f"prompt={metrics.get('prompt_tokens_per_second')} tok/s "
                            f"error={error or '-'}"
                        )

                for index in range(1, ttft_runs + 1):
                    ttft_key = f"ttft:{model}:{workload['id']}:{index}"
                    if ttft_key in completed_ttft:
                        print(f"[SKIP] {ttft_key}")
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
                    try:
                        result = streaming_ttft(base, payload)
                        error = None
                    except Exception as exc:
                        result = {}
                        error = f"{type(exc).__name__}: {exc}"
                    append_jsonl(
                        ttft_path,
                        {
                            "schema_version": SCHEMA_VERSION,
                            "execution_key": ttft_key
                            if error is None
                            else f"failed:{ttft_key}:{utc_now().isoformat()}",
                            "measurement_key": ttft_key,
                            "model": model,
                            "workload_id": workload["id"],
                            "run_index": index,
                            "eligible_for_main_score": eligible,
                            "runner_error": error,
                            **result,
                        },
                    )
                    if error is None:
                        completed_ttft.add(ttft_key)
                unload_model(model, base)
                wait_until_unloaded(model, base)
                append_jsonl(
                    run_dir / "performance_system_snapshots.jsonl",
                    {
                        "event": "model_end",
                        "model": model,
                        "workload": workload["id"],
                        "snapshot": system_snapshot(base),
                    },
                )
                if between_models:
                    time.sleep(between_models)
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

    summary = summarize(records_path, ttft_path, run_dir, config["workload_weights"])
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
