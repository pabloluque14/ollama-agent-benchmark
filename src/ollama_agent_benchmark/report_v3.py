"""Reconstrucción del informe v3 exclusivamente desde evidencia canónica."""

from __future__ import annotations

import base64
import csv
import json
import pathlib
from typing import Any

from .aggregation import aggregate_performance_cells
from .common import config_fingerprint, sha256_file, utc_now, write_json_atomic
from .evidence import load_run_evidence
from .performance import _weighted_metric
from .run_plan import _schema, _validate


def _functional_analysis(plan: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    cases_document = json.loads(
        base64.b64decode(plan["input_snapshots"]["datasets/benchmark_cases_v2.json"])
    )
    cases = {
        item["id"]: item
        for item in cases_document["cases"]
        if item["id"] in plan["effective"]["case_ids"]
    }
    rows = {item["execution_key"]: item for item in records}
    result: dict[str, Any] = {}
    per_case: dict[str, dict[str, bool]] = {}
    for model in plan["effective"]["models"]:
        tracks: dict[str, Any] = {}
        per_case[model] = {}
        for track in ("tool_reliability", "quality_reasoning"):
            case_ids = [case_id for case_id, case in cases.items() if case["track"] == track]
            observed: list[dict[str, Any]] = []
            complete = True
            majority: dict[str, bool] = {}
            consistent = 0
            for case_id in case_ids:
                expected = [
                    item["execution_key"]
                    for item in plan["calendar"]
                    if item["model"] == model and item["target_id"] == case_id
                ]
                case_rows = [rows[key] for key in expected if key in rows]
                observed.extend(case_rows)
                if len(case_rows) != len(expected):
                    complete = False
                    continue
                values = [bool(row["run"]["evaluation"]["passed"]) for row in case_rows]
                majority[case_id] = sum(values) * 2 > len(values)
                consistent += all(values)
            per_case[model].update(majority)
            majority_rate = (
                sum(majority.values()) / len(case_ids) if complete and case_ids else None
            )
            from .report import wilson

            lo, hi = wilson(sum(majority.values()), len(case_ids)) if complete else (None, None)
            tracks[track] = {
                "complete": complete,
                "executions": len(observed),
                "passed": sum(bool(row["run"]["evaluation"]["passed"]) for row in observed),
                "success_rate": (
                    sum(bool(row["run"]["evaluation"]["passed"]) for row in observed)
                    / len(observed)
                    if observed
                    else None
                ),
                "majority_cases_passed": sum(majority.values()) if complete else None,
                "majority_success_rate": majority_rate,
                "wilson_95": [lo, hi],
                "unique_cases": len(case_ids),
                "cases_passed_all_repetitions": consistent if complete else None,
                "case_consistency_rate": consistent / len(case_ids)
                if complete and case_ids
                else None,
            }
        model_rows = [row for row in records if row["model"] == model]
        result[model] = {
            "runner_errors": sum(row["status"] == "execution_failure" for row in model_rows),
            "tracks": tracks,
            "executions": len(model_rows),
        }
    comparisons = []
    from .report import exact_mcnemar

    models = plan["effective"]["models"]
    for index, first in enumerate(models):
        for second in models[index + 1 :]:
            common = sorted(set(per_case[first]) & set(per_case[second]))
            first_only = sum(
                per_case[first][case] and not per_case[second][case] for case in common
            )
            second_only = sum(
                not per_case[first][case] and per_case[second][case] for case in common
            )
            comparisons.append(
                {
                    "model_a": first,
                    "model_b": second,
                    "a_pass_b_fail": first_only,
                    "a_fail_b_pass": second_only,
                    "mcnemar_exact_p": exact_mcnemar(first_only, second_only),
                    "case_count": len(common),
                }
            )
    return {"models": result, "pairwise_mcnemar": comparisons, "records": len(records)}


def _performance_summary(
    plan: dict[str, Any], records: list[dict[str, Any]], ttft: list[dict[str, Any]]
) -> dict[str, Any]:
    models = aggregate_performance_cells(plan, records, ttft)
    fields = [
        "hot_prompt_tps",
        "hot_generation_tps",
        "hot_total_seconds",
        "cold_load_seconds",
        "size_vram_bytes",
        "swap_delta_bytes",
    ]
    if plan["effective"]["ttft_runs"]:
        fields.append("ttft_seconds")
    weights = plan["scoring_protocol"]["workload_weights"]
    for data in models.values():
        data["aggregate"] = {
            field: _weighted_metric(data["workloads"], field, weights) for field in fields
        }
    return {"models": models, "workload_weights": weights}


def _provenance(
    functional_dir: pathlib.Path,
    performance_dir: pathlib.Path,
    functional: dict[str, Any],
    performance: dict[str, Any],
) -> dict[str, Any]:
    paths = [
        functional_dir / "plan.json",
        functional_dir / "records.jsonl",
        performance_dir / "plan.json",
        performance_dir / "performance_records.jsonl",
    ]
    ttft = performance_dir / "ttft_records.jsonl"
    if ttft.exists():
        paths.append(ttft)
    return {
        "functional_run_id": functional["plan"]["run_id"],
        "performance_run_id": performance["plan"]["run_id"],
        "evidence_hashes": {str(path): sha256_file(path) for path in paths},
        "plan_fingerprints": {
            "functional": config_fingerprint(functional["plan"]),
            "performance": config_fingerprint(performance["plan"]),
        },
        "algorithms": {
            "functional": functional["plan"]["versions"],
            "performance": performance["plan"]["versions"],
        },
    }


def validate_report_document(document: dict[str, Any]) -> dict[str, Any]:
    schema = _schema("report-v3")
    _validate(document, schema, "informe", schema)
    if document["kind"] == "official":
        available = all(item["complete"] for item in document["scores"].values())
        if document["ranking_available"] != available:
            raise ValueError("informe.ranking_available: incoherente con componentes")
        if bool(document["ranking"]) != available:
            raise ValueError("informe.ranking: disponibilidad incoherente")
    return document


def generate_report_v3(
    functional_dir: pathlib.Path,
    performance_dir: pathlib.Path,
    output: pathlib.Path,
) -> dict[str, Any]:
    functional_evidence = load_run_evidence(functional_dir, "functional")
    performance_evidence = load_run_evidence(performance_dir, "performance")
    functional_plan = functional_evidence["plan"]
    performance_plan = performance_evidence["plan"]
    for field in ("benchmark_version", "models", "generation", "scoring_protocol", "ollama"):
        if functional_plan[field] != performance_plan[field]:
            raise ValueError(f"runs incompatibles: {field}")
    provenance = _provenance(
        functional_dir,
        performance_dir,
        functional_evidence,
        performance_evidence,
    )
    events = functional_evidence["integrity_events"] + performance_evidence["integrity_events"]
    official_modes = (
        functional_plan["mode"] == "official-functional"
        and performance_plan["mode"] == "official-performance"
        and functional_plan["official_eligible"]
        and performance_plan["official_eligible"]
    )
    if events or not official_modes:
        document = {
            "schema_version": 3,
            "benchmark_version": "0.3.0",
            "kind": "diagnostic",
            "eligible": False,
            "ranking_available": False,
            "created_at_utc": utc_now().isoformat(),
            "provenance": provenance,
            "reason": ("benchmark_integrity_failure" if events else "modo o entorno no elegible"),
            "integrity_events": events,
        }
        validate_report_document(document)
        output.mkdir(parents=True, exist_ok=True)
        write_json_atomic(output / "report.json", document)
        (output / "report.md").write_text(
            "# Diagnóstico no oficial\n\nEl run no es elegible para informe, scores ni ranking oficiales.\n",
            encoding="utf-8",
        )
        return document

    functional = _functional_analysis(functional_plan, functional_evidence["records"]["functional"])
    performance_summary = _performance_summary(
        performance_plan,
        performance_evidence["records"]["performance"],
        performance_evidence["records"]["ttft"],
    )
    from .report import performance_scores

    models = [item["name"] for item in functional_plan["models"]]
    perf = performance_scores(
        performance_summary, models, functional_plan["scoring_protocol"]["speed_weights"]
    )
    weights = functional_plan["scoring_protocol"]["weights"]
    scores: dict[str, Any] = {}
    for model in models:
        tool = functional["models"][model]["tracks"]["tool_reliability"]["majority_success_rate"]
        quality = functional["models"][model]["tracks"]["quality_reasoning"][
            "majority_success_rate"
        ]
        components = {
            "tool_reliability": tool * 100 if tool is not None else None,
            "quality_reasoning": quality * 100 if quality is not None else None,
            "speed": perf[model]["speed_score"],
            "memory_stability": perf[model]["memory_stability_score"],
        }
        complete = all(value is not None for value in components.values())
        scores[model] = {
            "components": components,
            "final_score": (
                sum(weights[name] * components[name] for name in weights) if complete else None
            ),
            "complete": complete,
        }
    ranking_available = all(item["complete"] for item in scores.values())
    ranking = (
        sorted(models, key=lambda model: scores[model]["final_score"], reverse=True)
        if ranking_available
        else []
    )
    warnings = []
    if (output / "report.json").exists():
        warnings.append("Se descartó y regeneró un derivado previo desde evidencia canónica.")
    document = {
        "schema_version": 3,
        "benchmark_version": "0.3.0",
        "kind": "official",
        "eligible": True,
        "ranking_available": ranking_available,
        "created_at_utc": utc_now().isoformat(),
        "provenance": provenance,
        "warnings": warnings,
        "functional": functional,
        "performance": {"summary": performance_summary, "scores": perf},
        "scores": scores,
        "ranking": ranking,
    }
    validate_report_document(document)
    output.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output / "report.json", document)
    with (output / "scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "model", "score"])
        for rank, model in enumerate(ranking, 1):
            writer.writerow([rank, model, scores[model]["final_score"]])
    lines = ["# Informe oficial Ollama Agent Benchmark 0.3.0", ""]
    lines.append(
        "Ranking global disponible."
        if ranking_available
        else "Comparación inconclusa: ranking global no disponible."
    )
    for model in models:
        value = scores[model]["final_score"]
        lines.append(f"- {model}: {'N/D' if value is None else f'{value:.2f}'}")
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return document
