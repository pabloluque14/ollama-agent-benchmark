from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import functional, model_lock, performance, preflight, report, validate
from .common import CONFIG_PATH, ROOT


def init_config(force: bool = False) -> int:
    example = ROOT / "config" / "benchmark.example.json"
    if CONFIG_PATH.exists() and not force:
        print(f"Ya existe {CONFIG_PATH}. Usa --force para reemplazarlo.", file=sys.stderr)
        return 1
    shutil.copy2(example, CONFIG_PATH)
    print(f"Configuración creada: {CONFIG_PATH}")
    print("Edita la lista 'models' y después ejecuta: oab lock")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oab",
        description="Benchmark reproducible de modelos agentes locales servidos por Ollama.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    init_p = sub.add_parser("init", help="Crea config/benchmark.json desde el ejemplo")
    init_p.add_argument("--force", action="store_true")
    sub.add_parser("lock", help="Fija digests y metadatos exactos")
    sub.add_parser("preflight", help="Comprueba el entorno")
    sub.add_parser("validate", help="Audita dataset y simulador sin Ollama")
    sub.add_parser("functional", help="Ejecuta el benchmark funcional")
    sub.add_parser("performance", help="Ejecuta velocidad, TTFT y memoria")
    sub.add_parser("report", help="Genera informe y ranking")
    args, remainder = parser.parse_known_args(argv)

    if args.command == "init":
        return init_config(args.force)
    handlers = {
        "lock": model_lock.main,
        "preflight": preflight.main,
        "validate": validate.main,
        "functional": functional.main,
        "performance": performance.main,
        "report": report.main,
    }
    return handlers[args.command](remainder)


if __name__ == "__main__":
    raise SystemExit(main())
