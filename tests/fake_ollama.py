from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeState:
    def __init__(self) -> None:
        self.version = "0.99.0-fake"
        self.digest = "sha256:" + "a" * 64
        self.model = "fake-agent:latest"
        self.loaded: set[str] = set()
        self.http_error_paths: set[str] = set()
        self.timeout_paths: set[str] = set()


class FakeOllama:
    def __init__(self) -> None:
        self.state = FakeState()
        state = self.state

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *args: Any) -> None:
                return

            def _json(self, value: dict[str, Any], status: int = 200) -> None:
                body = json.dumps(value).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _guard(self) -> bool:
                if self.path in state.timeout_paths:
                    time.sleep(0.2)
                if self.path in state.http_error_paths:
                    self._json({"error": "simulated"}, 500)
                    return False
                return True

            def do_GET(self) -> None:
                if not self._guard():
                    return
                if self.path == "/api/version":
                    self._json({"version": state.version})
                elif self.path == "/api/tags":
                    self._json(
                        {"models": [{"name": state.model, "digest": state.digest, "size": 42}]}
                    )
                elif self.path == "/api/ps":
                    self._json(
                        {
                            "models": [
                                {"name": name, "size_vram": 1024} for name in sorted(state.loaded)
                            ]
                        }
                    )
                else:
                    self._json({"error": "not found"}, 404)

            def do_POST(self) -> None:
                if not self._guard():
                    return
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/show":
                    self._json(
                        {
                            "details": {
                                "format": "gguf",
                                "family": "fake",
                                "parameter_size": "1B",
                                "quantization_level": "Q4",
                            },
                            "capabilities": ["completion", "tools"],
                            "model_info": {
                                "general.architecture": "fake",
                                "general.parameter_count": 1,
                            },
                            "template": "fake-template",
                            "modelfile": "FROM fake",
                        }
                    )
                elif self.path == "/api/generate":
                    model = str(payload.get("model"))
                    if payload.get("keep_alive") == 0:
                        state.loaded.discard(model)
                    else:
                        state.loaded.add(model)
                    self._json({"done": True})
                elif self.path == "/api/chat":
                    model = str(payload.get("model"))
                    state.loaded.add(model)
                    if payload.get("stream"):
                        chunks = [
                            {"message": {"role": "assistant", "content": "primer"}, "done": False},
                            self._chat_response(" resultado final"),
                        ]
                        body = b"".join(json.dumps(chunk).encode() + b"\n" for chunk in chunks)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-ndjson")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    else:
                        messages = payload.get("messages", [])
                        if payload.get("tools") and not any(
                            msg.get("role") == "tool" for msg in messages
                        ):
                            self._json(
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": "",
                                        "tool_calls": [
                                            {
                                                "id": "call-1",
                                                "function": {
                                                    "name": "simulated_terminal",
                                                    "arguments": {
                                                        "operation": "count_lines",
                                                        "arguments": [
                                                            "documentos/configuracion.txt"
                                                        ],
                                                    },
                                                },
                                            }
                                        ],
                                    },
                                    "done": True,
                                }
                            )
                        else:
                            self._json(
                                self._chat_response(
                                    "4"
                                    if payload.get("tools")
                                    else "- uno\n- dos\n- tres\n- cuatro"
                                )
                            )
                else:
                    self._json({"error": "not found"}, 404)

            @staticmethod
            def _chat_response(content: str) -> dict[str, Any]:
                return {
                    "message": {"role": "assistant", "content": content},
                    "done": True,
                    "total_duration": 1_000_000_000,
                    "load_duration": 100_000_000,
                    "prompt_eval_count": 20,
                    "prompt_eval_duration": 200_000_000,
                    "eval_count": 200,
                    "eval_duration": 800_000_000,
                }

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> FakeOllama:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
