"""Agregación v3 con completitud estricta de celdas."""

from __future__ import annotations

import statistics
from collections.abc import Callable
from typing import Any


def _stats(values: list[float]) -> dict[str, float | int | None]:
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


def aggregate_performance_cells(
    plan: dict[str, Any],
    records: list[dict[str, Any]],
    ttft_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Solo agrega una métrica cuando todas sus muestras planificadas son válidas."""
    by_key = {row["execution_key"]: row for row in records}
    ttft_by_key = {row["execution_key"]: row for row in ttft_records}
    output: dict[str, Any] = {}

    def cell(
        model: str,
        workload: str,
        state: str,
        source: dict[str, dict[str, Any]],
        value: Callable[[dict[str, Any]], Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        expected = [
            item["execution_key"]
            for item in plan["calendar"]
            if item["model"] == model
            and item["target_id"] == workload
            and item["measurement_type"] == state
        ]
        rows = [source[key] for key in expected if key in source]
        values = [value(row) for row in rows]
        valid = bool(expected) and len(rows) == len(expected)
        valid = valid and all(
            row["status"] == "completed"
            and row["workload_compliance"]["valid"]
            and (state != "cold" or row["cold_unload_verified"] is True)
            for row in rows
        )
        valid = valid and all(
            isinstance(item, (int, float)) and not isinstance(item, bool) for item in values
        )
        return _stats([float(item) for item in values]) if valid else _stats([]), {
            "expected": len(expected),
            "observed": len(rows),
            "valid": valid,
        }

    for model in plan["effective"]["models"]:
        model_result: dict[str, Any] = {
            "records": 0,
            "runner_errors": 0,
            "invalid_records": 0,
            "workloads": {},
        }
        for workload in plan["effective"]["workload_ids"]:
            relevant = [
                row for row in records if row["model"] == model and row["workload_id"] == workload
            ]
            model_result["records"] += len(relevant)
            model_result["runner_errors"] += sum(
                row["status"] == "execution_failure" for row in relevant
            )
            model_result["invalid_records"] += sum(
                not row["workload_compliance"]["valid"] for row in relevant
            )
            definitions = {
                "hot_prompt_tps": (
                    "hot",
                    by_key,
                    lambda row: row["metrics"].get("prompt_tokens_per_second"),
                ),
                "hot_generation_tps": (
                    "hot",
                    by_key,
                    lambda row: row["metrics"].get("generation_tokens_per_second"),
                ),
                "hot_total_seconds": (
                    "hot",
                    by_key,
                    lambda row: row["metrics"].get("total_seconds"),
                ),
                "cold_load_seconds": (
                    "cold",
                    by_key,
                    lambda row: row["metrics"].get("load_seconds"),
                ),
                "size_vram_bytes": (
                    "hot",
                    by_key,
                    lambda row: (row.get("model_ps") or {}).get("size_vram"),
                ),
                "swap_delta_bytes": ("hot", by_key, lambda row: row.get("swap_delta_bytes")),
            }
            workload_result: dict[str, Any] = {
                "records": len(relevant),
                "valid_records": sum(
                    row["status"] == "completed" and row["workload_compliance"]["valid"]
                    for row in relevant
                ),
                "cells": {},
            }
            cells: dict[str, Any] = workload_result["cells"]
            for name, (state, source, getter) in definitions.items():
                metric, diagnostic = cell(model, workload, state, source, getter)
                workload_result[name] = metric
                cells[name] = diagnostic
            if plan["effective"]["ttft_runs"]:
                metric, diagnostic = cell(
                    model, workload, "ttft", ttft_by_key, lambda row: row["ttft_seconds"]
                )
                workload_result["ttft_seconds"] = metric
                cells["ttft_seconds"] = diagnostic
            workloads: dict[str, Any] = model_result["workloads"]
            workloads[workload] = workload_result
        output[model] = model_result
    return output
