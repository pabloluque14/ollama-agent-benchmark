from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any

from .common import ROOT, load_config
from .functional import VirtualTools, resolve_expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oab validate",
        description="Valida configuración, dataset y simulador sin llamar a Ollama.",
    )
    parser.parse_args(argv)
    try:
        config = load_config()
        cases_doc = json.loads(
            (ROOT / "datasets" / "benchmark_cases_v2.json").read_text(encoding="utf-8")
        )
        fixtures = json.loads((ROOT / "datasets" / "fixtures_v2.json").read_text(encoding="utf-8"))
        tools_doc = json.loads((ROOT / "datasets" / "tools_v2.json").read_text(encoding="utf-8"))
        cases = cases_doc["cases"]
        tools = tools_doc["tools"]
        ids = [x["id"] for x in cases]
        if len(ids) != len(set(ids)):
            raise ValueError("Hay IDs duplicados")
        tool_names = {x["function"]["name"] for x in tools}
        for case in cases:
            unknown = set(case.get("allowed_tools", [])) - tool_names
            if unknown:
                raise ValueError(f"{case['id']} usa herramientas desconocidas: {sorted(unknown)}")

        mismatches = []
        checked_steps = 0
        for case in cases:
            expected = case["expected"]
            if expected["mode"] != "tool_sequence":
                continue
            simulator = VirtualTools(fixtures, case)
            previous: list[dict[str, Any]] = []
            for number, step in enumerate(expected.get("steps", []), 1):
                checked_steps += 1
                arguments = resolve_expected(step.get("arguments", {}), previous)
                result = simulator.execute(step["tool"], arguments)
                previous.append(result)
                label = step.get("result")
                if label is not None:
                    actual = {x for x in (result.get("error"), result.get("result_type")) if x}
                    if label not in actual:
                        mismatches.append((case["id"], number, label, sorted(actual)))
        if mismatches:
            raise ValueError(f"Secuencias imposibles: {mismatches}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("===== VALIDACIÓN DEL PROYECTO =====")
    print(f"Modelos configurados: {len(config['models'])}")
    print(f"Casos: {len(cases)}")
    print(f"Tracks: {dict(Counter(x['track'] for x in cases))}")
    print(f"Categorías: {len(set(x['category'] for x in cases))}")
    print(f"Herramientas simuladas: {len(tools)}")
    print(f"Pasos de herramienta auditados: {checked_steps}")
    print("Resultado: OK. No se llamó a Ollama.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
