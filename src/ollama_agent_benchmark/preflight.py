from __future__ import annotations

import argparse
import json
import pathlib
import platform
import shutil
from dataclasses import dataclass

from .common import (
    CONFIG_PATH,
    LOCK_PATH,
    api_base,
    detect_power,
    ensure_localhost,
    get_json,
    load_config,
    parse_swap_used_bytes,
    run_command,
    sha256_file,
    verify_lock,
)


@dataclass
class Result:
    level: str
    name: str
    detail: str


def run_preflight(
    config_path: pathlib.Path = CONFIG_PATH,
    lock_path: pathlib.Path = LOCK_PATH,
    require_ac: bool = False,
) -> list[Result]:
    results: list[Result] = []

    def add(level: str, name: str, detail: str) -> None:
        results.append(Result(level, name, detail))

    try:
        config = load_config(config_path)
        add("OK", "Configuración", str(config_path))
    except Exception as exc:
        add("ERROR", "Configuración", str(exc))
        return results

    base = api_base(config)
    if ensure_localhost(base):
        add("OK", "API de Ollama", f"Limitada por configuración a {base}")
    else:
        add("AVISO", "API de Ollama", f"No parece localhost: {base}")

    if not shutil.which("ollama"):
        add("ERROR", "CLI de Ollama", "No se encuentra ollama en PATH")
    else:
        version_cli = run_command(["ollama", "--version"])
        add(
            "OK" if version_cli.get("returncode") == 0 else "AVISO",
            "CLI de Ollama",
            str(version_cli.get("stdout", "")).strip(),
        )

    try:
        lock = verify_lock(config, lock_path)
        add("OK", "Lock de modelos", f"{lock_path} ({sha256_file(lock_path)})")
        for item in lock.get("models", []):
            add("OK", f"Digest {item['name']}", str(item.get("digest")))
    except Exception as exc:
        add("ERROR", "Lock de modelos", str(exc))
        lock = None

    try:
        ps_data = get_json(base + "/api/ps", timeout=10)
        running = [item.get("name") for item in ps_data.get("models", [])]
        add(
            "AVISO" if running else "OK",
            "Modelos cargados",
            ", ".join(running) if running else "Ninguno",
        )
    except Exception as exc:
        add("ERROR", "Estado de Ollama", str(exc))

    power = detect_power()
    if power["condition"] == "ac_power" or power["condition"] == "not_applicable":
        add("OK", "Alimentación", power["raw"])
    elif require_ac:
        add("ERROR", "Alimentación", "El benchmark oficial exige corriente. " + power["raw"])
    else:
        add("AVISO", "Alimentación", power["raw"])

    if platform.system() == "Darwin":
        thermal = run_command(["pmset", "-g", "therm"])
        text = str(thermal.get("stdout", "")).strip().replace("\n", " | ")
        warning_terms = ("CPU_Scheduler_Limit", "CPU_Available_CPUs", "CPU_Speed_Limit")
        add(
            "AVISO" if any(term in text for term in warning_terms) else "OK",
            "Estado térmico",
            text or "Sin datos",
        )
        swap = parse_swap_used_bytes()
        add(
            "INFO",
            "Swap usado",
            f"{swap / 1024**2:.2f} MiB" if swap is not None else "No disponible",
        )

    usage = shutil.disk_usage(config_path.parent)
    free_gib = usage.free / 1024**3
    add("AVISO" if free_gib < 20 else "OK", "Espacio libre", f"{free_gib:.2f} GiB")

    for path in (
        config_path,
        pathlib.Path(__file__).resolve().parents[2] / "datasets" / "benchmark_cases_v2.json",
        pathlib.Path(__file__).resolve().parents[2] / "datasets" / "fixtures_v2.json",
        pathlib.Path(__file__).resolve().parents[2] / "datasets" / "tools_v2.json",
    ):
        if path.is_file():
            add("OK", f"Artefacto {path.name}", sha256_file(path))
        else:
            add("ERROR", f"Artefacto {path.name}", "No existe")

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oab preflight",
        description="Comprueba seguridad, identidad de modelos y condiciones del sistema.",
    )
    parser.add_argument(
        "--config", type=pathlib.Path, default=CONFIG_PATH, help="Ruta de benchmark.json"
    )
    parser.add_argument("--lock", type=pathlib.Path, default=LOCK_PATH, help="Ruta del lock")
    parser.add_argument("--require-ac", action="store_true", help="Exige corriente en macOS")
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Imprime resultados como JSON"
    )
    args = parser.parse_args(argv)

    results = run_preflight(args.config, args.lock, args.require_ac)
    if args.as_json:
        print(json.dumps([r.__dict__ for r in results], ensure_ascii=False, indent=2))
    else:
        order = {"ERROR": 0, "AVISO": 1, "INFO": 2, "OK": 3}
        print("===== PREFLIGHT =====")
        for result in sorted(results, key=lambda x: (order.get(x.level, 99), x.name)):
            print(f"[{result.level:5}] {result.name}: {result.detail}")
        print()
        print(f"Errores críticos: {sum(r.level == 'ERROR' for r in results)}")
        print(f"Avisos: {sum(r.level == 'AVISO' for r in results)}")

    return 1 if any(r.level == "ERROR" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
