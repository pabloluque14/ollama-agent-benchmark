from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys
from typing import Any

from .common import (
    BENCHMARK_VERSION,
    CONFIG_PATH,
    LOCK_PATH,
    SCHEMA_VERSION,
    api_base,
    get_json,
    load_config,
    post_json,
    public_base_url,
    sha256_text,
    write_json_atomic,
)


def architecture_metadata(model_info: dict[str, Any]) -> dict[str, Any]:
    architecture = model_info.get("general.architecture")
    result: dict[str, Any] = {
        "architecture": architecture,
        "parameter_count": model_info.get("general.parameter_count"),
    }
    if architecture:
        for suffix in ("block_count", "context_length", "embedding_length"):
            result[suffix] = model_info.get(f"{architecture}.{suffix}")
    return result


def create_lock(
    config_path: pathlib.Path = CONFIG_PATH,
    lock_path: pathlib.Path = LOCK_PATH,
    force: bool = False,
) -> dict[str, Any]:
    config = load_config(config_path)
    if lock_path.exists() and not force:
        raise FileExistsError(f"Ya existe {lock_path}. Usa --force para regenerarlo.")

    base = api_base(config)
    version = get_json(base + "/api/version", timeout=10)
    tags = get_json(base + "/api/tags", timeout=30)
    installed = {item.get("name"): item for item in tags.get("models", [])}

    locked = []
    for name in config["models"]:
        tag = installed.get(name)
        if not tag:
            raise ValueError(f"El modelo no está instalado en Ollama: {name}")
        show = post_json(base + "/api/show", {"model": name, "verbose": False}, timeout=60)
        details = show.get("details") or {}
        locked.append(
            {
                "name": name,
                "digest": tag.get("digest"),
                "size_bytes": tag.get("size"),
                "modified_at": tag.get("modified_at"),
                "format": details.get("format"),
                "family": details.get("family"),
                "parameter_size": details.get("parameter_size"),
                "quantization_level": details.get("quantization_level"),
                "capabilities": show.get("capabilities", []),
                "requires_ollama": show.get("requires"),
                "architecture_metadata": architecture_metadata(show.get("model_info") or {}),
                "default_parameters": show.get("parameters", ""),
                "template_sha256": sha256_text(show.get("template", "")),
                "modelfile_sha256": sha256_text(show.get("modelfile", "")),
            }
        )

    document = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "created_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "ollama_base_url": public_base_url(base),
        "ollama_server_version": version.get("version"),
        "models": locked,
    }
    write_json_atomic(lock_path, document)
    pathlib.Path(str(lock_path) + ".sha256").write_text(
        __import__("hashlib").sha256(lock_path.read_bytes()).hexdigest() + f"  {lock_path.name}\n",
        encoding="utf-8",
    )
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fija digests y metadatos exactos de los modelos instalados."
    )
    parser.add_argument("--config", type=pathlib.Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=pathlib.Path, default=LOCK_PATH)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        lock = create_lock(args.config, args.output, args.force)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("===== MODELOS BLOQUEADOS =====")
    print(f"Ollama: {lock.get('ollama_server_version')}")
    for item in lock["models"]:
        print(
            f"- {item['name']}: {str(item['digest'])[:12]} | "
            f"{item.get('format')} | {item.get('quantization_level')} | "
            f"{item.get('parameter_size')}"
        )
        caps = ", ".join(item.get("capabilities") or [])
        print(f"  capacidades: {caps or '<no declaradas>'}")
    print(f"Lock: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
