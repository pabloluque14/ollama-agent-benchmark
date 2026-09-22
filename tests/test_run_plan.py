from __future__ import annotations

import copy
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from ollama_agent_benchmark import functional, performance
from ollama_agent_benchmark.run_plan import create_run_plan, validate_run_plan

ROOT = Path(__file__).resolve().parents[1]


class RunPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = {
            "schema_version": 3,
            "benchmark_version": "0.3.0",
            "run_id": "example-run",
            "runner": "functional",
            "mode": "official-functional",
            "created_at_utc": "2026-09-22T12:00:00+00:00",
            "versions": {
                "package": "0.2.0",
                "runner": "functional-runner-v2",
                "scheduler": "rotating_models_shuffled_cases-v2",
                "aggregation": "v2",
                "scoring": "v2",
                "report": "v2",
                "error_policy": "v2",
            },
            "ollama": {"base_url": "http://127.0.0.1:11434", "version": "0.11.0"},
            "models": [{"name": "fake:latest", "digest": "sha256:" + "a" * 64}],
            "generation": {
                "num_ctx": 8192,
                "temperature": 0,
                "seed": 42,
                "top_k": 1,
                "top_p": 1.0,
                "min_p": 0.0,
                "repeat_penalty": 1.0,
                "presence_penalty": 0.0,
                "num_predict": 1024,
                "think": False,
            },
            "order_control": {"seed": 42, "policy": "rotating_models_shuffled_cases"},
            "effective": {
                "models": ["fake:latest"],
                "case_ids": ["T001"],
                "repetitions": 1,
                "max_turns": 8,
                "keep_alive": "5m",
                "pause_seconds": 0,
            },
            "overrides": {
                "models": None,
                "case_ids": None,
                "repetitions": None,
                "allow_battery": False,
            },
            "calendar": [
                {
                    "execution_key": "R1:fake:latest:T001",
                    "model": "fake:latest",
                    "target_id": "T001",
                    "repetition": 1,
                    "measurement_type": "functional",
                    "block": "R1:T001",
                    "position": 1,
                }
            ],
            "input_hashes": {"config/benchmark.json": "a" * 64},
            "scoring_protocol": {
                "weights": {
                    "tool_reliability": 0.4,
                    "quality_reasoning": 0.25,
                    "speed": 0.2,
                    "memory_stability": 0.15,
                },
                "speed_weights": {
                    "generation": 0.35,
                    "prompt": 0.2,
                    "hot_latency": 0.15,
                    "ttft": 0.15,
                    "cold_load": 0.15,
                },
                "workload_weights": {"short_technical_answer": 1.0},
                "missing_metric_policy": "incomplete_score",
            },
            "environment": {"platform": "Darwin", "machine": "arm64", "power": "ac_power"},
            "official_eligible": True,
        }

    def test_plan_is_durable_and_cannot_be_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            create_run_plan(path, self.plan)
            original = path.read_bytes()
            self.assertEqual(json.loads(original), self.plan)
            with self.assertRaises(FileExistsError):
                create_run_plan(path, self.plan)
            self.assertEqual(path.read_bytes(), original)

    def test_validator_rejects_missing_extra_and_coerced_fields(self) -> None:
        for mutation in ("missing", "extra", "coerced", "bool_as_int"):
            with self.subTest(mutation=mutation):
                plan = copy.deepcopy(self.plan)
                if mutation == "missing":
                    del plan["effective"]["repetitions"]
                elif mutation == "extra":
                    plan["surprise"] = True
                elif mutation == "coerced":
                    plan["effective"]["repetitions"] = "1"
                else:
                    plan["effective"]["repetitions"] = True
                with self.assertRaisesRegex(ValueError, "effective.repetitions|surprise"):
                    validate_run_plan(plan)

    def test_validator_rejects_calendar_metadata_that_disagrees_with_key(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan["calendar"][0]["repetition"] = 2
        with self.assertRaisesRegex(ValueError, "plan.calendar"):
            validate_run_plan(plan)

    def test_validator_rejects_unsafe_run_id_and_non_official_eligibility(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan["run_id"] = ".."
        with self.assertRaisesRegex(ValueError, "plan.run_id"):
            validate_run_plan(plan)
        plan["run_id"] = "safe"
        plan["mode"] = "smoke"
        with self.assertRaisesRegex(ValueError, "official_eligible"):
            validate_run_plan(plan)

    def test_validator_rejects_invalid_weights_without_mutating_input(self) -> None:
        original = copy.deepcopy(self.plan)
        self.assertIs(validate_run_plan(self.plan), self.plan)
        self.assertEqual(self.plan, original)
        plan = copy.deepcopy(self.plan)
        plan["scoring_protocol"]["workload_weights"]["short_technical_answer"] = 0
        with self.assertRaisesRegex(ValueError, "workload_weights"):
            validate_run_plan(plan)


class RunPlanCliTests(unittest.TestCase):
    def test_plan_precedes_preflight_and_resume_rejects_changed_effective_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_dir = root / "config"
            data_dir = root / "datasets"
            config_dir.mkdir()
            data_dir.mkdir()
            config = json.loads((ROOT / "config/benchmark.example.json").read_text())
            config["models"] = ["fake:latest"]
            config["performance"]["ttft_runs"] = 0
            config_path = config_dir / "benchmark.json"
            config_path.write_text(json.dumps(config))
            lock_path = config_dir / "models.lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "benchmark_version": "0.2.0",
                        "ollama_base_url": "http://127.0.0.1:11434",
                        "ollama_server_version": "0.99.0-fake",
                        "models": [{"name": "fake:latest", "digest": "sha256:" + "a" * 64}],
                    }
                )
            )
            for name in (
                "benchmark_cases_v2.json",
                "fixtures_v2.json",
                "tools_v2.json",
                "performance_workloads_v2.json",
            ):
                (data_dir / name).write_bytes((ROOT / "datasets" / name).read_bytes())
            functional_args = [
                "--mode",
                "official-functional",
                "--case-ids",
                "T001",
                "--repetitions",
                "1",
                "--run-id",
                "f",
            ]
            with (
                mock.patch.object(functional, "ROOT", root),
                mock.patch.object(functional, "PROTOCOL_PATH", config_path),
                mock.patch.object(functional, "LOCK_PATH", lock_path),
                mock.patch.object(functional, "CASES_PATH", data_dir / "benchmark_cases_v2.json"),
                mock.patch.object(functional, "FIXTURES_PATH", data_dir / "fixtures_v2.json"),
                mock.patch.object(functional, "TOOLS_PATH", data_dir / "tools_v2.json"),
                mock.patch.object(
                    functional,
                    "detect_power",
                    return_value={"condition": "not_applicable", "raw": "test"},
                ),
            ):
                with (
                    mock.patch.object(
                        functional,
                        "verify_ollama_and_models",
                        side_effect=AssertionError("contactó Ollama"),
                    ),
                    redirect_stdout(StringIO()),
                ):
                    self.assertEqual(
                        functional.main(["--mode", "dry-run", "--run-id", "preview"]), 0
                    )
                self.assertFalse((root / "runs").exists())

                def functional_preflight(_lock: object, _base: object) -> None:
                    plan = validate_run_plan(json.loads((root / "runs/f/plan.json").read_text()))
                    self.assertEqual(plan["effective"]["repetitions"], 1)
                    raise RuntimeError("detenido antes de medir")

                with (
                    mock.patch.object(
                        functional, "verify_ollama_and_models", side_effect=functional_preflight
                    ),
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    self.assertEqual(functional.main(functional_args), 1)
                plan_path = root / "runs/f/plan.json"
                original = plan_path.read_bytes()
                with (
                    mock.patch.object(
                        functional,
                        "verify_ollama_and_models",
                        side_effect=AssertionError("contactó Ollama"),
                    ),
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    changed = [
                        "--mode",
                        "official-functional",
                        "--case-ids",
                        "T001",
                        "--repetitions",
                        "2",
                        "--run-id",
                        "f",
                        "--resume",
                    ]
                    self.assertEqual(functional.main(changed), 4)
                self.assertEqual(plan_path.read_bytes(), original)
                self.assertFalse((root / "runs/f/records.jsonl").exists())

            performance_args = [
                "--mode",
                "official-performance",
                "--workloads",
                "short_technical_answer",
                "--run-id",
                "p",
            ]
            with (
                mock.patch.object(performance, "ROOT", root),
                mock.patch.object(performance, "CONFIG_PATH", config_path),
                mock.patch.object(
                    performance, "WORKLOADS_PATH", data_dir / "performance_workloads_v2.json"
                ),
                mock.patch.object(
                    performance,
                    "detect_power",
                    return_value={"condition": "not_applicable", "raw": "test"},
                ),
            ):

                def performance_preflight(_config: object) -> None:
                    plan = validate_run_plan(json.loads((root / "runs/p/plan.json").read_text()))
                    self.assertEqual(plan["effective"]["ttft_runs"], 0)
                    self.assertFalse(
                        any(item["measurement_type"] == "ttft" for item in plan["calendar"])
                    )
                    raise ValueError("detenido antes de medir")

                with (
                    mock.patch.object(
                        performance, "verify_lock", side_effect=performance_preflight
                    ),
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    self.assertEqual(performance.main(performance_args), 1)
                plan_path = root / "runs/p/plan.json"
                original = plan_path.read_bytes()
                with (
                    mock.patch.object(
                        performance, "verify_lock", side_effect=AssertionError("contactó Ollama")
                    ),
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    changed = [
                        "--mode",
                        "official-performance",
                        "--workloads",
                        "long_generation",
                        "--run-id",
                        "p",
                        "--resume",
                    ]
                    self.assertEqual(performance.main(changed), 4)
                self.assertEqual(plan_path.read_bytes(), original)
                self.assertFalse((root / "runs/p/performance_records.jsonl").exists())

    def test_dry_run_creates_no_canonical_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "benchmark.json"
            config.write_bytes((ROOT / "config/benchmark.example.json").read_bytes())
            output = StringIO()
            with (
                mock.patch.object(performance, "ROOT", root),
                mock.patch.object(performance, "CONFIG_PATH", config),
                mock.patch.object(
                    performance, "WORKLOADS_PATH", ROOT / "datasets/performance_workloads_v2.json"
                ),
                mock.patch.object(
                    performance, "verify_lock", side_effect=AssertionError("contactó Ollama")
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(performance.main(["--mode", "dry-run", "--run-id", "preview"]), 0)
            self.assertIn("No se llamó a Ollama", output.getvalue())
            self.assertFalse((root / "runs").exists())
