from __future__ import annotations

import argparse
import csv
import html
import itertools
import json
import math
import pathlib
import statistics
import sys
from collections import defaultdict
from typing import Any

from .common import ROOT, iter_jsonl, load_config, read_json, utc_now, write_json_atomic


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def exact_mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2 * tail)


def ratio_high(value: float | None, best: float | None) -> float | None:
    if value is None or best is None or best <= 0:
        return None
    return min(100.0, 100.0 * value / best)


def ratio_low(value: float | None, best: float | None) -> float | None:
    if value is None or best is None or value <= 0:
        return None
    return min(100.0, 100.0 * best / value)


def median_field(summary: dict[str, Any], model: str, field: str) -> float | None:
    value = summary["models"].get(model, {}).get(field, {}).get("median")
    return float(value) if isinstance(value, (int, float)) else None


def locate_latest(kind: str) -> pathlib.Path | None:
    candidates = []
    for run_dir in (ROOT / "runs").glob("*"):
        if kind == "functional" and (run_dir / "records.jsonl").is_file():
            candidates.append(run_dir)
        if kind == "performance" and (run_dir / "performance_summary.json").is_file():
            candidates.append(run_dir)
    return sorted(candidates)[-1] if candidates else None


def functional_analysis(run_dir: pathlib.Path, models: list[str]) -> dict[str, Any]:
    records = list(iter_jsonl(run_dir / "records.jsonl"))
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        by_model[item["model"]].append(item)
    result: dict[str, Any] = {}
    per_case_majority: dict[str, dict[str, bool]] = {model: {} for model in models}

    for model in models:
        items = by_model.get(model, [])
        tracks: dict[str, Any] = {}
        for track in ("tool_reliability", "quality_reasoning"):
            subset = [x for x in items if x["case"]["track"] == track]
            passed = sum(bool(x["run"]["evaluation"]["passed"]) for x in subset)
            lo, hi = wilson(passed, len(subset))
            cases: dict[str, list[bool]] = defaultdict(list)
            for item in subset:
                cases[item["case"]["id"]].append(bool(item["run"]["evaluation"]["passed"]))
            consistent = sum(all(values) for values in cases.values())
            majority = {case_id: sum(values) >= math.ceil(len(values) / 2) for case_id, values in cases.items()}
            per_case_majority[model].update(majority)
            tracks[track] = {
                "executions": len(subset),
                "passed": passed,
                "success_rate": passed / len(subset) if subset else None,
                "wilson_95": [lo, hi],
                "unique_cases": len(cases),
                "cases_passed_all_repetitions": consistent,
                "case_consistency_rate": consistent / len(cases) if cases else None,
            }
        result[model] = {
            "runner_errors": sum(bool(x.get("runner_error")) for x in items),
            "tracks": tracks,
            "executions": len(items),
        }

    comparisons = []
    for a, b in itertools.combinations(models, 2):
        common = sorted(set(per_case_majority[a]) & set(per_case_majority[b]))
        b_only = sum((not per_case_majority[a][case]) and per_case_majority[b][case] for case in common)
        a_only = sum(per_case_majority[a][case] and (not per_case_majority[b][case]) for case in common)
        comparisons.append(
            {
                "model_a": a,
                "model_b": b,
                "a_pass_b_fail": a_only,
                "a_fail_b_pass": b_only,
                "mcnemar_exact_p": exact_mcnemar(a_only, b_only),
                "case_count": len(common),
            }
        )
    return {"models": result, "pairwise_mcnemar": comparisons, "records": len(records)}


def performance_scores(summary: dict[str, Any], models: list[str]) -> dict[str, Any]:
    gen = {m: median_field(summary, m, "hot_generation_tps") for m in models}
    prompt = {m: median_field(summary, m, "hot_prompt_tps") for m in models}
    total = {m: median_field(summary, m, "hot_total_seconds") for m in models}
    load = {m: median_field(summary, m, "cold_load_seconds") for m in models}
    memory = {m: median_field(summary, m, "size_vram_bytes") for m in models}
    swap = {m: median_field(summary, m, "swap_delta_bytes") for m in models}
    errors = {m: int(summary["models"].get(m, {}).get("runner_errors", 0)) for m in models}
    records = {m: int(summary["models"].get(m, {}).get("records", 0)) for m in models}

    best_gen = max((x for x in gen.values() if x is not None), default=None)
    best_prompt = max((x for x in prompt.values() if x is not None), default=None)
    best_total = min((x for x in total.values() if x and x > 0), default=None)
    best_load = min((x for x in load.values() if x and x > 0), default=None)
    best_memory = min((x for x in memory.values() if x and x > 0), default=None)
    nonnegative_swap = {m: max(0.0, x or 0.0) for m, x in swap.items()}

    output: dict[str, Any] = {}
    for model in models:
        speed_components = {
            "generation_tps": ratio_high(gen[model], best_gen),
            "prompt_tps": ratio_high(prompt[model], best_prompt),
            "total_latency": ratio_low(total[model], best_total),
            "cold_load": ratio_low(load[model], best_load),
        }
        if all(value is not None for value in speed_components.values()):
            speed_score = (
                0.45 * speed_components["generation_tps"]
                + 0.20 * speed_components["prompt_tps"]
                + 0.20 * speed_components["total_latency"]
                + 0.15 * speed_components["cold_load"]
            )
        else:
            speed_score = None

        memory_component = ratio_low(memory[model], best_memory)
        # A 0 MiB de incremento le corresponde 100. La penalización es gradual.
        swap_component = 100.0 / (1.0 + nonnegative_swap[model] / 1024**3)
        error_free = 100.0 * (1 - errors[model] / records[model]) if records[model] else None
        memory_score = (
            0.60 * memory_component + 0.20 * swap_component + 0.20 * error_free
            if memory_component is not None and error_free is not None
            else None
        )
        output[model] = {
            "raw": {
                "generation_tps_median": gen[model],
                "prompt_tps_median": prompt[model],
                "hot_total_seconds_median": total[model],
                "cold_load_seconds_median": load[model],
                "size_vram_bytes_median": memory[model],
                "swap_delta_bytes_median": swap[model],
                "runner_errors": errors[model],
            },
            "speed_components": speed_components,
            "speed_score": speed_score,
            "memory_components": {
                "relative_memory": memory_component,
                "swap": swap_component,
                "error_free": error_free,
            },
            "memory_stability_score": memory_score,
        }
    return output


def svg_bars(path: pathlib.Path, title: str, values: list[tuple[str, float]], suffix: str = "") -> None:
    width, left, right, row_h = 1000, 330, 80, 54
    height = 100 + row_h * max(1, len(values))
    max_value = max((v for _, v in values), default=1.0) or 1.0
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="30" y="42" font-family="sans-serif" font-size="24" font-weight="bold">{html.escape(title)}</text>',
    ]
    chart_width = width - left - right
    for index, (label, value) in enumerate(values):
        y = 72 + index * row_h
        bar_width = chart_width * value / max_value
        lines.append(f'<text x="30" y="{y + 25}" font-family="sans-serif" font-size="16">{html.escape(label)}</text>')
        lines.append(f'<rect x="{left}" y="{y + 5}" width="{bar_width:.1f}" height="28" rx="4" fill="#4c78a8"/>')
        lines.append(f'<text x="{left + bar_width + 10:.1f}" y="{y + 26}" font-family="sans-serif" font-size="15">{value:.2f}{html.escape(suffix)}</text>')
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt_pct(value: float | None) -> str:
    return "N/D" if value is None else f"{value * 100:.1f}%"


def fmt_score(value: float | None) -> str:
    return "N/D" if value is None else f"{value:.2f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Combina calidad, herramientas, velocidad y memoria en un informe explicado.")
    parser.add_argument("--functional-run", type=pathlib.Path)
    parser.add_argument("--performance-run", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)

    try:
        config = load_config()
        functional_dir = args.functional_run or locate_latest("functional")
        performance_dir = args.performance_run or locate_latest("performance")
        if not functional_dir or not performance_dir:
            raise FileNotFoundError("Falta un run funcional o de rendimiento")
        performance_summary = read_json(performance_dir / "performance_summary.json")
        functional_models = {item["model"] for item in iter_jsonl(functional_dir / "records.jsonl")}
        performance_models = set(performance_summary.get("models", {}))
        models = [m for m in config["models"] if m in functional_models and m in performance_models]
        if not models:
            raise ValueError("Los runs funcional y de rendimiento no comparten modelos")
        functional = functional_analysis(functional_dir, models)
        perf = performance_scores(performance_summary, models)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    scores: dict[str, Any] = {}
    weights = config["weights"]
    for model in models:
        tool_rate = functional["models"][model]["tracks"]["tool_reliability"]["success_rate"]
        quality_rate = functional["models"][model]["tracks"]["quality_reasoning"]["success_rate"]
        components = {
            "tool_reliability": tool_rate * 100 if tool_rate is not None else None,
            "quality_reasoning": quality_rate * 100 if quality_rate is not None else None,
            "speed": perf[model]["speed_score"],
            "memory_stability": perf[model]["memory_stability_score"],
        }
        complete = all(value is not None for value in components.values())
        final = sum(weights[name] * components[name] for name in weights) if complete else None
        scores[model] = {"components": components, "final_score": final, "complete": complete}

    ranking = sorted(models, key=lambda m: scores[m]["final_score"] if scores[m]["final_score"] is not None else -1, reverse=True)
    output = args.output or ROOT / "reports" / f"report_{utc_now().strftime('%Y%m%dT%H%M%SZ')}"
    output.mkdir(parents=True, exist_ok=True)

    document = {
        "schema_version": 1,
        "created_at_utc": utc_now().isoformat(),
        "functional_run": str(functional_dir),
        "performance_run": str(performance_dir),
        "weights": weights,
        "functional": functional,
        "performance": perf,
        "scores": scores,
        "ranking": ranking,
    }
    write_json_atomic(output / "report.json", document)

    with (output / "scores.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["rank", "model", "tool_reliability", "quality_reasoning", "speed", "memory_stability", "final_score"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, model in enumerate(ranking, 1):
            writer.writerow({"rank": rank, "model": model, **scores[model]["components"], "final_score": scores[model]["final_score"]})

    svg_bars(output / "charts" / "final_score.svg", "Puntuación final", [(m, scores[m]["final_score"] or 0.0) for m in ranking], "")
    svg_bars(output / "charts" / "tool_reliability.svg", "Fiabilidad de herramientas", [(m, scores[m]["components"]["tool_reliability"] or 0.0) for m in ranking], "%")
    svg_bars(output / "charts" / "generation_tps.svg", "Velocidad de generación (mediana)", [(m, perf[m]["raw"]["generation_tps_median"] or 0.0) for m in ranking], " tok/s")
    svg_bars(output / "charts" / "memory_gib.svg", "Memoria del modelo según /api/ps", [(m, (perf[m]["raw"]["size_vram_bytes_median"] or 0.0) / 1024**3) for m in ranking], " GiB")

    lines = [
        "# Informe del benchmark de agentes Ollama",
        "",
        f"- Run funcional: `{functional_dir}`",
        f"- Run de rendimiento: `{performance_dir}`",
        f"- Generado: `{document['created_at_utc']}`",
        "",
        "## Resultado ejecutivo",
        "",
        "| Puesto | Modelo | Herramientas | Calidad | Velocidad | Memoria/estabilidad | Final |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for rank, model in enumerate(ranking, 1):
        c = scores[model]["components"]
        lines.append(
            f"| {rank} | `{model}` | {fmt_score(c['tool_reliability'])} | {fmt_score(c['quality_reasoning'])} | "
            f"{fmt_score(c['speed'])} | {fmt_score(c['memory_stability'])} | **{fmt_score(scores[model]['final_score'])}** |"
        )

    lines += [
        "",
        "La puntuación final aplica las ponderaciones configuradas. Las categorías funcionales son porcentajes absolutos de éxito. Velocidad y memoria son puntuaciones relativas al mejor resultado observado dentro de esta comparación; por eso no deben compararse directamente entre runs con conjuntos de modelos distintos.",
        "",
        "## Cómo interpretar las métricas",
        "",
        "- **Herramientas:** porcentaje de ejecuciones que eligieron la herramienta correcta, usaron argumentos válidos, respetaron confirmaciones y utilizaron fielmente los resultados.",
        "- **Calidad:** porcentaje de pruebas de instrucciones, razonamiento, síntesis, depuración y detección de información insuficiente superadas.",
        "- **Prompt tok/s:** velocidad de lectura/procesamiento de la entrada. No es la velocidad de escritura de la respuesta.",
        "- **Generation tok/s:** velocidad de generación de tokens de salida.",
        "- **Carga fría:** tiempo invertido en cargar el modelo después de descargarlo de memoria.",
        "- **TTFT:** tiempo medido hasta el primer fragmento en streaming; se informa por separado porque la respuesta no streaming no permite observarlo exactamente.",
        "- **Memoria:** `size_vram` comunicado por `/api/ps`. En Apple Silicon representa memoria usada por el modelo en el subsistema de aceleración y no equivale al tamaño del archivo descargado.",
        "- **Consistencia:** casos superados en todas las repeticiones y comparación pareada de McNemar. Un valor p pequeño indica diferencias consistentes en qué casos gana cada modelo, no solo en el promedio.",
        "",
        "## Resultados funcionales",
        "",
    ]
    for model in models:
        item = functional["models"][model]
        lines.append(f"### `{model}`")
        for track, data in item["tracks"].items():
            lo, hi = data["wilson_95"]
            lines.append(
                f"- {track}: {data['passed']}/{data['executions']} = {fmt_pct(data['success_rate'])}; "
                f"IC Wilson 95%: {fmt_pct(lo)}–{fmt_pct(hi)}; "
                f"casos perfectos en todas las repeticiones: {data['cases_passed_all_repetitions']}/{data['unique_cases']}."
            )
        lines.append("")

    lines += ["## Comparaciones pareadas", ""]
    for item in functional["pairwise_mcnemar"]:
        lines.append(
            f"- `{item['model_a']}` vs `{item['model_b']}`: discordancias {item['a_pass_b_fail']} / {item['a_fail_b_pass']}; "
            f"McNemar exacto p={item['mcnemar_exact_p']:.4f}."
        )

    lines += [
        "",
        "## Gráficas",
        "",
        "- [Puntuación final](charts/final_score.svg)",
        "- [Fiabilidad de herramientas](charts/tool_reliability.svg)",
        "- [Velocidad de generación](charts/generation_tps.svg)",
        "- [Memoria](charts/memory_gib.svg)",
        "",
        "## Limitaciones",
        "",
        "- El benchmark compara artefactos completos. Si dos modelos cambian simultáneamente de backend, cuantización, plantilla o arquitectura, el resultado no identifica causalmente qué variable produjo la diferencia.",
        "- Los scores relativos de velocidad y memoria dependen del conjunto de modelos incluido.",
        "- Los tags de Ollama pueden cambiar. El `models.lock.json` registra el digest observado, pero para repetir exactamente un artefacto antiguo también debe conservarse una copia de sus blobs.",
        "- Este benchmark usa herramientas simuladas. Un modelo debe superar además una validación controlada antes de recibir herramientas reales.",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("===== INFORME GENERADO =====")
    for rank, model in enumerate(ranking, 1):
        print(f"{rank}. {model}: {fmt_score(scores[model]['final_score'])}")
    print(f"Markdown: {output / 'report.md'}")
    print(f"JSON: {output / 'report.json'}")
    print(f"CSV: {output / 'scores.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
