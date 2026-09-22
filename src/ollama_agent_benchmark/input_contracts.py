"""Contratos estructurales y semánticos de los inputs versionados."""

from __future__ import annotations

import hashlib
from typing import Any

from .run_plan import _schema, _validate


def validate_dataset(kind: str, document: Any) -> dict[str, Any]:
    schemas = {
        "cases": "benchmark-cases-v2",
        "fixtures": "fixtures-v2",
        "tools": "tools-v2",
        "workloads": "performance-workloads-v2",
    }
    if kind not in schemas:
        raise ValueError("input: tipo de dataset desconocido")
    schema = _schema(schemas[kind])
    _validate(document, schema, f"input.{kind}", schema)
    if kind == "cases":
        ids = [item["id"] for item in document["cases"]]
        if len(ids) != len(set(ids)):
            raise ValueError("input.cases: IDs duplicados")
        counts = document["counts"]
        actual = {
            "tool_reliability": sum(
                item["track"] == "tool_reliability" for item in document["cases"]
            ),
            "quality_reasoning": sum(
                item["track"] == "quality_reasoning" for item in document["cases"]
            ),
            "total": len(document["cases"]),
        }
        if counts != actual:
            raise ValueError("input.cases.counts: recuentos incoherentes")
    elif kind == "fixtures":
        for name, item in document["virtual_files"].items():
            content = item["content"].encode("utf-8")
            if (
                item["size_bytes"] != len(content)
                or item["sha256"] != hashlib.sha256(content).hexdigest()
            ):
                raise ValueError(f"input.fixtures.virtual_files.{name}: hash o tamaño incoherente")
    elif kind == "tools":
        names = [item["function"]["name"] for item in document["tools"]]
        if len(names) != len(set(names)):
            raise ValueError("input.tools: nombres duplicados")
    else:
        ids = [item["id"] for item in document["workloads"]]
        if len(ids) != len(set(ids)):
            raise ValueError("input.workloads: IDs duplicados")
        for index, item in enumerate(document["workloads"]):
            if ("messages" in item) == ("builder" in item):
                raise ValueError(
                    f"input.workloads[{index}]: debe contener exactamente messages o builder"
                )
            minimum = item["compliance"].get("min_numbered_points")
            maximum = item["compliance"].get("max_numbered_points")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"input.workloads[{index}].compliance: límites incoherentes")
    return document
