from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from typing import Any

from .common import (
    CONFIG_PATH,
    ROOT,
    api_base,
    append_jsonl,
    detect_power,
    get_json,
    iter_jsonl,
    load_config,
    metric_rates,
    model_ps_snapshot,
    parse_swap_used_bytes,
    post_json,
    rotate_models,
    safe_slug,
    system_snapshot,
    unload_model,
    utc_now,
    verify_lock,
    wait_until_unloaded,
    write_json_atomic,
)

WORKLOADS_PATH = ROOT / "datasets" / "performance_workloads_v1.json"


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
            has_payload = bool(message.get("content") or message.get("thinking") or message.get("tool_calls"))
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


def run_response(base: str, model: str, workload: dict[str, Any], config: dict[str, Any], keep_alive: str) -> tuple[dict[str, Any], float]:
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


def summarize(records_path: pathlib.Path, ttft_path: pathlib.Path, output_dir: pathlib.Path) -> dict[str, Any]:
    records = list(iter_jsonl(records_path)) if records_path.is_file() else []
    ttft = list(iter_jsonl(ttft_path)) if ttft_path.is_file() else []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        grouped[item["model"]].append(item)

    rows = []
    models_summary: dict[str, Any] = {}
    for model, items in grouped.items():
        hot = [x for x in items if x["temperature_state"] == "hot" and not x.get("runner_error")]
        cold = [x for x in items if x["temperature_state"] == "cold" and not x.get("runner_error")]
        prompt_tps = [x["metrics"]["prompt_tokens_per_second"] for x in hot if x["metrics"].get("prompt_tokens_per_second") is not None]
        gen_tps = [x["metrics"]["generation_tokens_per_second"] for x in hot if x["metrics"].get("generation_tokens_per_second") is not None]
        total = [x["metrics"]["total_seconds"] for x in hot if x["metrics"].get("total_seconds") is not None]
        loads = [x["metrics"]["load_seconds"] for x in cold if x["metrics"].get("load_seconds") is not None]
        memory = [x["model_ps"].get("size_vram") for x in items if isinstance(x.get("model_ps"), dict) and isinstance(x["model_ps"].get("size_vram"), int)]
        swap_delta = [x["swap_delta_bytes"] for x in items if isinstance(x.get("swap_delta_bytes"), int)]
        ttft_values = [x["ttft_seconds"] for x in ttft if x["model"] == model and isinstance(x.get("ttft_seconds"), (int, float))]
        models_summary[model] = {
            "records": len(items),
            "runner_errors": sum(bool(x.get("runner_error")) for x in items),
            "hot_prompt_tps": stats(prompt_tps),
            "hot_generation_tps": stats(gen_tps),
            "hot_total_seconds": stats(total),
            "cold_load_seconds": stats(loads),
            "size_vram_bytes": stats([float(x) for x in memory]),
            "swap_delta_bytes": stats([float(x) for x in swap_delta]),
            "ttft_seconds": stats([float(x) for x in ttft_values]),
        }
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
                }
            )

    csv_path = output_dir / "performance_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["model"])
        writer.writeheader()
        writer.writerows(rows)
    summary = {"created_at_utc": utc_now().isoformat(), "models": models_summary, "csv": str(csv_path)}
    write_json_atomic(output_dir / "performance_summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mide carga, prompt, generación, TTFT y memoria de modelos Ollama.")
    parser.add_argument("--mode", choices=("dry-run", "smoke", "official-performance"), default="dry-run")
    parser.add_argument("--models", help="Modelos separados por comas; deben existir en el lock")
    parser.add_argument("--workloads", help="IDs de cargas separados por comas")
    parser.add_argument("--run-id")
    parser.add_argument("--allow-battery", action="store_true")
    parser.add_argument("--resume", action="store_true")
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
    cold_runs = 1 if args.mode == "smoke" else int(perf.get("cold_runs", 1))
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
    eligible = args.mode == "official-performance" and power["condition"] in {"ac_power", "not_applicable"} and not args.allow_battery
    if args.mode == "official-performance" and power["condition"] == "battery" and not args.allow_battery:
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
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": 1,
        "runner_version": "performance-runner-v1.0",
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
        "generation": config["generation"],
    }
    write_json_atomic(manifest_path, manifest)
    completed = {
        item["execution_key"]
        for item in iter_jsonl(records_path)
    } if records_path.is_file() else set()

    keep_alive = str(perf.get("keep_alive", "5m"))
    after_unload = float(perf.get("pause_after_unload_seconds", 10))
    between_models = float(perf.get("pause_between_models_seconds", 30))
    order = models
    total = len(models) * len(workloads) * (cold_runs + hot_runs)
    done = len(completed)

    append_jsonl(run_dir / "performance_system_snapshots.jsonl", {"event": "run_start", "snapshot": system_snapshot(base)})
    try:
        for workload_index, workload in enumerate(workloads):
            sequence = order[workload_index % len(order):] + order[:workload_index % len(order)]
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
                            wait_until_unloaded(model, base)
                            if after_unload:
                                time.sleep(after_unload)
                        swap_before = parse_swap_used_bytes()
                        started = utc_now()
                        error = None
                        try:
                            exchange, wall = run_response(base, model, workload, config, keep_alive)
                            metrics = metric_rates(exchange["response"])
                            ps = model_ps_snapshot(model, base)
                        except Exception as exc:
                            exchange, wall, metrics, ps = {}, None, {}, None
                            error = f"{type(exc).__name__}: {exc}"
                        swap_after = parse_swap_used_bytes()
                        record = {
                            "schema_version": 1,
                            "execution_key": key,
                            "run_id": run_id,
                            "eligible_for_main_score": eligible,
                            "power_condition": power["condition"],
                            "model": model,
                            "workload_id": workload["id"],
                            "temperature_state": state,
                            "run_index": index,
                            "started_at_utc": started.isoformat(),
                            "completed_at_utc": utc_now().isoformat(),
                            "wall_seconds": wall,
                            "metrics": metrics,
                            "model_ps": ps,
                            "swap_before_bytes": swap_before,
                            "swap_after_bytes": swap_after,
                            "swap_delta_bytes": (swap_after - swap_before) if swap_before is not None and swap_after is not None else None,
                            "runner_error": error,
                            "exchange": exchange,
                        }
                        append_jsonl(records_path, record)
                        completed.add(key)
                        done += 1
                        print(
                            f"[{state.upper()}] {done}/{total} "
                            f"gen={metrics.get('generation_tokens_per_second')} tok/s "
                            f"prompt={metrics.get('prompt_tokens_per_second')} tok/s "
                            f"error={error or '-'}"
                        )

                for index in range(1, ttft_runs + 1):
                    payload = {
                        "model": model,
                        "messages": build_messages(workload),
                        "think": config["generation"].get("think", False),
                        "keep_alive": keep_alive,
                        "options": {
                            **{k: v for k, v in config["generation"].items() if k not in {"think", "stream", "keep_alive"}},
                            "num_predict": int(workload.get("num_predict", config["generation"].get("num_predict", 256))),
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
                            "model": model,
                            "workload_id": workload["id"],
                            "run_index": index,
                            "eligible_for_main_score": eligible,
                            "runner_error": error,
                            **result,
                        },
                    )
                unload_model(model, base)
                wait_until_unloaded(model, base)
                append_jsonl(run_dir / "performance_system_snapshots.jsonl", {"event": "model_end", "model": model, "workload": workload["id"], "snapshot": system_snapshot(base)})
                if between_models:
                    time.sleep(between_models)
    except KeyboardInterrupt:
        print("Interrumpido. Usa --resume para continuar.", file=sys.stderr)
        return 130
    finally:
        for model in models:
            unload_model(model, base)
        append_jsonl(run_dir / "performance_system_snapshots.jsonl", {"event": "run_end", "snapshot": system_snapshot(base)})

    summary = summarize(records_path, ttft_path, run_dir)
    print("===== RESUMEN DE RENDIMIENTO =====")
    for model, item in summary["models"].items():
        print(
            f"- {model}: gen mediana={item['hot_generation_tps']['median']} tok/s; "
            f"prompt mediana={item['hot_prompt_tps']['median']} tok/s; "
            f"carga fría mediana={item['cold_load_seconds']['median']} s"
        )
    print(f"Run: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
