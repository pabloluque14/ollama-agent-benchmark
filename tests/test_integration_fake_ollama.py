from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

from fake_ollama import FakeOllama

from ollama_agent_benchmark import cli, functional, performance, report
from ollama_agent_benchmark.common import (
    get_json,
    load_config,
    sha256_file,
    unload_model,
    wait_until_unloaded,
)
from ollama_agent_benchmark.failures import record_integrity_failure
from ollama_agent_benchmark.model_lock import create_lock
from ollama_agent_benchmark.performance import (
    build_messages,
    run_response,
    streaming_ttft,
    validate_workload_response,
)
from ollama_agent_benchmark.preflight import run_preflight

ROOT = Path(__file__).resolve().parents[1]


def test_config(base_url: str) -> dict:
    config = json.loads((ROOT / "config/benchmark.example.json").read_text(encoding="utf-8"))
    config["models"] = ["fake-agent:latest"]
    config["ollama"]["base_url"] = base_url
    return config


class FakeOllamaIntegrationTests(unittest.TestCase):
    def test_init_creates_configuration_that_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config/benchmark.example.json").write_text(
                (ROOT / "config/benchmark.example.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with (
                mock.patch.object(cli, "ROOT", root),
                mock.patch.object(cli, "CONFIG_PATH", root / "config/benchmark.json"),
            ):
                self.assertEqual(cli.init_config(), 0)
            self.assertEqual(load_config(root / "config/benchmark.json")["schema_version"], 3)

    def test_lock_preflight_chat_stream_unload_and_identity_changes(self):
        with FakeOllama() as fake, tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "benchmark.json"
            lock_path = root / "models.lock.json"
            config_path.write_text(json.dumps(test_config(fake.base_url)), encoding="utf-8")
            lock = create_lock(config_path, lock_path)
            self.assertEqual(lock["schema_version"], 3)
            with mock.patch("ollama_agent_benchmark.preflight.shutil.which", return_value=None):
                results = run_preflight(config_path, lock_path)
            self.assertTrue(
                any(item.name == "Lock de modelos" and item.level == "OK" for item in results)
            )

            config = load_config(config_path)
            workload = json.loads((ROOT / "datasets/performance_workloads_v2.json").read_text())[
                "workloads"
            ][0]
            exchange, _wall = run_response(fake.base_url, fake.state.model, workload, config, "1m")
            self.assertTrue(validate_workload_response(workload, exchange["response"])["valid"])
            payload = {
                "model": fake.state.model,
                "messages": build_messages(workload),
                "options": {},
            }
            self.assertIsNotNone(streaming_ttft(fake.base_url, payload)["ttft_seconds"])
            self.assertTrue(get_json(fake.base_url + "/api/ps")["models"])
            unload_model(fake.state.model, fake.base_url)
            self.assertTrue(wait_until_unloaded(fake.state.model, fake.base_url, timeout=1))

            fake.state.digest = "sha256:" + "b" * 64
            with self.assertRaisesRegex(ValueError, "no coinciden"):
                from ollama_agent_benchmark.common import verify_lock

                verify_lock(config, lock_path)
            fake.state.digest = lock["models"][0]["digest"]
            fake.state.version = "changed"
            with self.assertRaisesRegex(ValueError, "versión"):
                verify_lock(config, lock_path)

    def test_functional_tool_call_uses_configured_server(self):
        with FakeOllama() as fake:
            cases = json.loads((ROOT / "datasets/benchmark_cases_v2.json").read_text())["cases"]
            case = next(item for item in cases if item["id"] == "T001")
            fixtures = json.loads((ROOT / "datasets/fixtures_v2.json").read_text())
            tools = json.loads((ROOT / "datasets/tools_v2.json").read_text())["tools"]
            result = functional.run_case(
                fake.base_url,
                fake.state.model,
                case,
                functional.tool_map(tools),
                fixtures,
                {"num_ctx": 256, "num_predict": 32},
                "1m",
                False,
                3,
            )
            self.assertTrue(result["evaluation"]["passed"])
            self.assertEqual(len(result["tool_events"]), 1)

    def test_fake_server_simulates_http_errors_and_timeouts(self):
        with FakeOllama() as fake:
            fake.state.http_error_paths.add("/api/version")
            with self.assertRaises(urllib.error.HTTPError):
                get_json(fake.base_url + "/api/version")
            fake.state.http_error_paths.clear()
            fake.state.timeout_paths.add("/api/version")
            with self.assertRaises(TimeoutError):
                get_json(fake.base_url + "/api/version", timeout=0.01)

    def test_complete_minimal_runners_resume_and_report(self):
        with FakeOllama() as fake, tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            datasets_dir = root / "datasets"
            config_dir.mkdir()
            datasets_dir.mkdir()
            config = test_config(fake.base_url)
            config["functional"].update(
                {"repetitions": 1, "pause_between_models_seconds": 0, "smoke_pause_seconds": 0}
            )
            config["performance"].update(
                {
                    "cold_runs": 1,
                    "hot_runs": 1,
                    "ttft_runs": 1,
                    "pause_after_unload_seconds": 0,
                    "pause_between_models_seconds": 0,
                }
            )
            config_path = config_dir / "benchmark.json"
            lock_path = config_dir / "models.lock.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            create_lock(config_path, lock_path)
            for name in (
                "benchmark_cases_v2.json",
                "fixtures_v2.json",
                "tools_v2.json",
                "performance_workloads_v2.json",
            ):
                (datasets_dir / name).write_text(
                    (ROOT / "datasets" / name).read_text(encoding="utf-8"), encoding="utf-8"
                )

            power = {"condition": "not_applicable", "raw": "Linux simulado"}
            functional_run = "functional-min"
            functional_patches = (
                mock.patch.object(functional, "ROOT", root),
                mock.patch.object(functional, "PROTOCOL_PATH", config_path),
                mock.patch.object(functional, "LOCK_PATH", lock_path),
                mock.patch.object(
                    functional, "CASES_PATH", datasets_dir / "benchmark_cases_v2.json"
                ),
                mock.patch.object(functional, "FIXTURES_PATH", datasets_dir / "fixtures_v2.json"),
                mock.patch.object(functional, "TOOLS_PATH", datasets_dir / "tools_v2.json"),
                mock.patch.object(functional, "detect_power", return_value=power),
            )
            with (
                functional_patches[0],
                functional_patches[1],
                functional_patches[2],
                functional_patches[3],
                functional_patches[4],
                functional_patches[5],
                functional_patches[6],
            ):
                command = [
                    "--mode",
                    "official-functional",
                    "--models",
                    fake.state.model,
                    "--case-ids",
                    "T001",
                    "--repetitions",
                    "1",
                    "--run-id",
                    functional_run,
                ]
                self.assertEqual(functional.main(command), 0)
                functional_snapshots = root / "runs" / functional_run / "system_snapshots.jsonl"
                snapshots_before = functional_snapshots.read_bytes()
                with mock.patch.object(
                    functional,
                    "preflight_run_plan",
                    side_effect=AssertionError("un run completo no consulta Ollama"),
                ) as preflight:
                    self.assertEqual(functional.main([*command, "--resume"]), 0)
                preflight.assert_not_called()
                self.assertEqual(functional_snapshots.read_bytes(), snapshots_before)

                fault_command = [*command[:-1], "functional-journal-fault"]
                error = StringIO()
                with (
                    mock.patch.object(
                        functional,
                        "run_case",
                        side_effect=RuntimeError("token=hidden-secret"),
                    ),
                    mock.patch(
                        "ollama_agent_benchmark.failures.append_jsonl",
                        side_effect=OSError("password=storage-secret"),
                    ),
                    redirect_stderr(error),
                ):
                    self.assertEqual(functional.main(fault_command), 6)
                self.assertNotIn("hidden-secret", error.getvalue())
                self.assertNotIn("storage-secret", error.getvalue())
                self.assertFalse(
                    (root / "runs" / "functional-journal-fault" / "records.jsonl").exists()
                )

                persistence_command = [*command[:-1], "functional-record-fault"]
                with mock.patch.object(
                    functional,
                    "append_primary_record",
                    side_effect=OSError("token=hidden-secret"),
                ):
                    self.assertEqual(functional.main(persistence_command), 6)
                fault_dir = root / "runs" / "functional-record-fault"
                self.assertFalse((fault_dir / "records.jsonl").exists())
                self.assertEqual(
                    json.loads((fault_dir / "integrity.jsonl").read_text())["category"],
                    "benchmark_integrity_failure",
                )
                self.assertNotIn("hidden-secret", (fault_dir / "integrity.jsonl").read_text())
            functional_records = root / "runs" / functional_run / "records.jsonl"
            self.assertEqual(len(functional_records.read_text().splitlines()), 1)

            performance_run = "performance-min"
            with (
                mock.patch.object(performance, "ROOT", root),
                mock.patch.object(performance, "CONFIG_PATH", config_path),
                mock.patch.object(
                    performance,
                    "WORKLOADS_PATH",
                    datasets_dir / "performance_workloads_v2.json",
                ),
                mock.patch.object(performance, "detect_power", return_value=power),
            ):
                command = [
                    "--mode",
                    "official-performance",
                    "--models",
                    fake.state.model,
                    "--workloads",
                    "short_technical_answer",
                    "--run-id",
                    performance_run,
                ]
                self.assertEqual(performance.main(command), 0)
                performance_snapshots = (
                    root / "runs" / performance_run / "performance_system_snapshots.jsonl"
                )
                snapshots_before = performance_snapshots.read_bytes()
                with mock.patch.object(
                    performance,
                    "preflight_run_plan",
                    side_effect=AssertionError("un run completo no consulta Ollama"),
                ) as preflight:
                    self.assertEqual(performance.main([*command, "--resume"]), 0)
                preflight.assert_not_called()
                self.assertEqual(performance_snapshots.read_bytes(), snapshots_before)

            output = root / "report"
            self.assertEqual(
                report.main(
                    [
                        "--functional-run",
                        str(root / "runs" / functional_run),
                        "--performance-run",
                        str(root / "runs" / performance_run),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            self.assertTrue((output / "report.md").is_file())
            document = json.loads((output / "report.json").read_text())
            self.assertEqual(document["kind"], "official")
            self.assertFalse(document["ranking_available"])
            self.assertEqual(document["ranking"], [])

            performance_csv = root / "runs" / performance_run / "performance_results.csv"
            original_csv = performance_csv.read_bytes()
            (root / "runs" / performance_run / "performance_summary.json").unlink()
            with mock.patch.object(report, "ROOT", root):
                self.assertEqual(report.locate_latest("performance"), root / "runs" / performance_run)

            canonical = [
                root / "runs" / functional_run / "plan.json",
                root / "runs" / functional_run / "records.jsonl",
                root / "runs" / performance_run / "plan.json",
                root / "runs" / performance_run / "performance_records.jsonl",
                root / "runs" / performance_run / "ttft_records.jsonl",
            ]
            hashes = {path: sha256_file(path) for path in canonical}
            (root / "runs" / performance_run / "performance_summary.json").write_text("{}")
            performance_csv.write_text("derivado obsoleto", encoding="utf-8")
            regenerated = root / "report-regenerated"
            self.assertEqual(
                report.main(
                    [
                        "--functional-run",
                        str(root / "runs" / functional_run),
                        "--performance-run",
                        str(root / "runs" / performance_run),
                        "--output",
                        str(regenerated),
                    ]
                ),
                0,
            )
            self.assertEqual(hashes, {path: sha256_file(path) for path in canonical})
            self.assertEqual(
                json.loads((regenerated / "report.json").read_text())["scores"],
                document["scores"],
            )
            regenerated_document = json.loads((regenerated / "report.json").read_text())
            self.assertTrue(any("derivado" in item for item in regenerated_document["warnings"]))
            self.assertEqual(
                json.loads(
                    (root / "runs" / performance_run / "performance_summary.json").read_text()
                )["models"],
                regenerated_document["performance"]["summary"]["models"],
            )
            self.assertEqual(performance_csv.read_bytes(), original_csv)

            integrity = root / "runs" / functional_run / "integrity.jsonl"
            record_integrity_failure(
                integrity,
                phase="execution",
                component="functional",
                operation="test",
                exc=RuntimeError("harness"),
            )
            diagnostic = root / "diagnostic"
            self.assertEqual(
                report.main(
                    [
                        "--functional-run",
                        str(root / "runs" / functional_run),
                        "--performance-run",
                        str(root / "runs" / performance_run),
                        "--output",
                        str(diagnostic),
                    ]
                ),
                0,
            )
            diagnostic_document = json.loads((diagnostic / "report.json").read_text())
            self.assertEqual(diagnostic_document["kind"], "diagnostic")
            self.assertNotIn("scores", diagnostic_document)
            self.assertFalse((diagnostic / "scores.csv").exists())
            self.assertTrue((output / "scores.csv").exists())
            self.assertEqual(
                report.main(
                    [
                        "--functional-run",
                        str(root / "runs" / functional_run),
                        "--performance-run",
                        str(root / "runs" / performance_run),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            self.assertFalse((output / "scores.csv").exists())

            integrity.unlink()
            records_path = root / "runs" / functional_run / "records.jsonl"
            records_path.write_bytes(records_path.read_bytes() * 2)
            rejected = root / "rejected"
            self.assertEqual(
                report.main(
                    [
                        "--functional-run",
                        str(root / "runs" / functional_run),
                        "--performance-run",
                        str(root / "runs" / performance_run),
                        "--output",
                        str(rejected),
                    ]
                ),
                1,
            )
            self.assertFalse(rejected.exists())


if __name__ == "__main__":
    unittest.main()
