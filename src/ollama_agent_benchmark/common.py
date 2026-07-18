from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from typing import Any, Iterable


def project_root() -> pathlib.Path:
    override = os.environ.get("OAB_ROOT")
    if override:
        return pathlib.Path(override).expanduser().resolve()
    return pathlib.Path(__file__).resolve().parents[2]


ROOT = project_root()
CONFIG_PATH = ROOT / "config" / "benchmark.json"
LOCK_PATH = ROOT / "config" / "models.lock.json"
API_DEFAULT = "http://127.0.0.1:11434"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp = pathlib.Path(handle.name)
    os.replace(temp, path)


def append_jsonl(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def api_base(config: dict[str, Any]) -> str:
    return str(config.get("ollama", {}).get("base_url", API_DEFAULT)).rstrip("/")


def get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def post_json(url: str, payload: dict[str, Any], timeout: int = 900) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "error": str(exc)}


def detect_power() -> dict[str, str]:
    if platform.system() != "Darwin":
        return {"condition": "not_applicable", "raw": "Power gate is macOS-specific."}
    result = run_command(["pmset", "-g", "batt"])
    text = str(result.get("stdout", ""))
    if "AC Power" in text:
        condition = "ac_power"
    elif "Battery Power" in text:
        condition = "battery"
    else:
        condition = "unknown"
    return {"condition": condition, "raw": text.strip()}


def parse_swap_used_bytes() -> int | None:
    if platform.system() != "Darwin":
        return None
    result = run_command(["sysctl", "vm.swapusage"])
    text = str(result.get("stdout", ""))
    match = re.search(r"used\s*=\s*([0-9.,]+)([KMG])", text)
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    factor = {"K": 1024, "M": 1024**2, "G": 1024**3}[match.group(2)]
    return int(value * factor)


def system_snapshot(base_url: str | None = None) -> dict[str, Any]:
    base = (base_url or API_DEFAULT).rstrip("/")
    snapshot: dict[str, Any] = {
        "captured_at_utc": utc_now().isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "power": detect_power(),
        "swap_used_bytes": parse_swap_used_bytes(),
        "processes": run_command(
            ["ps", "-axo", "pid,ppid,%cpu,%mem,rss,vsz,etime,command"], timeout=20
        ),
    }
    if platform.system() == "Darwin":
        snapshot.update(
            thermal=run_command(["pmset", "-g", "therm"]),
            vm_stat=run_command(["vm_stat"]),
        )
    try:
        snapshot["ollama_ps_api"] = get_json(base + "/api/ps", timeout=10)
    except Exception as exc:  # snapshot must not crash a run
        snapshot["ollama_ps_api_error"] = str(exc)
    return snapshot


def unload_model(model: str, base_url: str) -> None:
    try:
        post_json(
            base_url.rstrip("/") + "/api/generate",
            {"model": model, "stream": False, "keep_alive": 0},
            timeout=300,
        )
    except Exception:
        pass


def load_config(path: pathlib.Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"No existe {path}. Copia config/benchmark.example.json a config/benchmark.json."
        )
    config = read_json(path)
    models = config.get("models")
    if not isinstance(models, list) or not models or not all(isinstance(x, str) and x for x in models):
        raise ValueError("config.models debe ser una lista no vacía de nombres de Ollama")
    weights = config.get("weights", {})
    expected = {"tool_reliability", "quality_reasoning", "speed", "memory_stability"}
    if set(weights) != expected:
        raise ValueError(f"config.weights debe contener exactamente: {sorted(expected)}")
    if abs(sum(float(v) for v in weights.values()) - 1.0) > 1e-12:
        raise ValueError("Las ponderaciones deben sumar 1.0")
    return config


def verify_lock(config: dict[str, Any], lock_path: pathlib.Path = LOCK_PATH) -> dict[str, Any]:
    if not lock_path.is_file():
        raise FileNotFoundError(f"No existe {lock_path}. Ejecuta: oab lock")
    lock = read_json(lock_path)
    locked_names = [item.get("name") for item in lock.get("models", [])]
    if locked_names != config.get("models"):
        raise ValueError(
            "El orden o contenido de config.models no coincide con models.lock.json. "
            "Regenera el lock con: oab lock --force"
        )
    base = api_base(config)
    version = get_json(base + "/api/version", timeout=10)
    tags = get_json(base + "/api/tags", timeout=30)
    actual = {item.get("name"): item.get("digest") for item in tags.get("models", [])}
    mismatches = []
    for item in lock.get("models", []):
        if actual.get(item.get("name")) != item.get("digest"):
            mismatches.append(
                {
                    "model": item.get("name"),
                    "expected": item.get("digest"),
                    "actual": actual.get(item.get("name")),
                }
            )
    if mismatches:
        raise ValueError(f"Los modelos locales no coinciden con el lock: {mismatches}")
    if lock.get("ollama_server_version") != version.get("version"):
        raise ValueError(
            "La versión de Ollama cambió desde que se creó el lock: "
            f"lock={lock.get('ollama_server_version')} actual={version.get('version')}"
        )
    return lock


def ns_seconds(value: Any) -> float | None:
    return value / 1e9 if isinstance(value, int) else None


def metric_rates(response: dict[str, Any]) -> dict[str, Any]:
    out = {
        key: response.get(key)
        for key in (
            "total_duration",
            "load_duration",
            "prompt_eval_count",
            "prompt_eval_duration",
            "eval_count",
            "eval_duration",
        )
    }
    pe_count, pe_dur = out.get("prompt_eval_count"), out.get("prompt_eval_duration")
    ev_count, ev_dur = out.get("eval_count"), out.get("eval_duration")
    out["prompt_tokens_per_second"] = (
        pe_count / (pe_dur / 1e9)
        if isinstance(pe_count, int) and isinstance(pe_dur, int) and pe_dur > 0
        else None
    )
    out["generation_tokens_per_second"] = (
        ev_count / (ev_dur / 1e9)
        if isinstance(ev_count, int) and isinstance(ev_dur, int) and ev_dur > 0
        else None
    )
    out["total_seconds"] = ns_seconds(out.get("total_duration"))
    out["load_seconds"] = ns_seconds(out.get("load_duration"))
    return out


def rotate_models(models: list[str], repetitions: int) -> list[list[str]]:
    return [models[i % len(models):] + models[: i % len(models)] for i in range(repetitions)]


def wait_until_unloaded(model: str, base_url: str, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            data = get_json(base_url.rstrip("/") + "/api/ps", timeout=5)
            names = {item.get("name") for item in data.get("models", [])}
            if model not in names:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def model_ps_snapshot(model: str, base_url: str) -> dict[str, Any] | None:
    data = get_json(base_url.rstrip("/") + "/api/ps", timeout=10)
    for item in data.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            return item
    return None


def ensure_localhost(base_url: str) -> bool:
    return base_url.startswith("http://127.0.0.1:") or base_url.startswith("http://localhost:")


def safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_")


def iter_jsonl(path: pathlib.Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)
