from __future__ import annotations

import base64
import copy
import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from ollama_agent_benchmark import functional, performance
from ollama_agent_benchmark.common import append_jsonl, iter_jsonl
from ollama_agent_benchmark.primary_records import append_primary_record
from ollama_agent_benchmark.resume import validate_resume_evidence
from ollama_agent_benchmark.run_plan import (
    create_run_plan,
    load_compatible_run_plan,
    preflight_run_plan,
    validate_planning_inputs,
    validate_run_plan,
)

ROOT = Path(__file__).resolve().parents[1]


class RunPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = {
            "id": "T001",
            "title": "Ejemplo",
            "track": "tool_reliability",
            "category": "single",
            "expected": {"mode": "text_contains"},
        }
        snapshot = json.dumps({"schema_version": 2, "cases": [self.case]}).encode()
        snapshot_path = "datasets/benchmark_cases_v2.json"
        fixtures = b'{"schema_version":2,"virtual_docs":{},"virtual_files":{}}'
        tools = b'{"schema_version":2,"tools":[]}'
        self.plan = {
            "schema_version": 3,
            "benchmark_version": "0.3.0",
            "run_id": "example-run",
            "runner": "functional",
            "mode": "official-functional",
            "created_at_utc": "2026-09-22T12:00:00+00:00",
            "versions": {
                "package": "0.3.0",
                "runner": "functional-runner-v3",
                "scheduler": "balanced-block-v3",
                "aggregation": "v3",
                "scoring": "v3",
                "report": "v3",
                "error_policy": "classified-v3",
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
                    "execution_key": '["functional","fake:latest","T001",1,1]',
                    "model": "fake:latest",
                    "target_id": "T001",
                    "repetition": 1,
                    "measurement_type": "functional",
                    "block": "R1:T001",
                    "position": 1,
                }
            ],
            "input_hashes": {
                "config/benchmark.json": "a" * 64,
                "config/models.lock.json": "b" * 64,
                snapshot_path: hashlib.sha256(snapshot).hexdigest(),
                "datasets/fixtures_v2.json": hashlib.sha256(fixtures).hexdigest(),
                "datasets/tools_v2.json": hashlib.sha256(tools).hexdigest(),
            },
            "input_snapshots": {
                snapshot_path: base64.b64encode(snapshot).decode("ascii"),
                "datasets/fixtures_v2.json": base64.b64encode(fixtures).decode("ascii"),
                "datasets/tools_v2.json": base64.b64encode(tools).decode("ascii"),
            },
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
            "measurement_protocol": {
                "metrics": ["case_pass", "track_success_rate"],
                "compliance_policy": "dataset-contract-v2",
                "sample_validity_policy": "all-required-evidence-v3",
                "cell_completeness_policy": "all-planned-samples-v3",
                "execution_failure_policy": "terminal-without-positive-metrics-v3",
                "integrity_failure_policy": "journal-nonterminal-v3",
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
            proposed = copy.deepcopy(self.plan)
            proposed["created_at_utc"] = "2026-09-23T12:00:00+00:00"
            self.assertEqual(load_compatible_run_plan(path, proposed), self.plan)
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

    def test_validator_rejects_incompatible_implementation_versions(self) -> None:
        for component in ("package", "runner", "scheduler", "aggregation", "scoring", "report", "error_policy"):
            with self.subTest(component=component):
                plan = copy.deepcopy(self.plan)
                plan["versions"][component] = "v2"
                with self.assertRaisesRegex(ValueError, "plan.versions"):
                    validate_run_plan(plan)

    def test_plan_rejects_snapshot_that_disagrees_with_locked_hash(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan["input_snapshots"]["datasets/benchmark_cases_v2.json"] = base64.b64encode(
            b'{"schema_version":3}'
        ).decode("ascii")
        with self.assertRaisesRegex(ValueError, "input_snapshots"):
            validate_run_plan(plan)

    def test_plan_rejects_selected_case_missing_from_its_snapshot(self) -> None:
        plan = copy.deepcopy(self.plan)
        path = "datasets/benchmark_cases_v2.json"
        payload = b'{"schema_version":2,"cases":[{"id":"T002"}]}'
        plan["input_snapshots"][path] = base64.b64encode(payload).decode("ascii")
        plan["input_hashes"][path] = hashlib.sha256(payload).hexdigest()
        with self.assertRaisesRegex(ValueError, "input_snapshots"):
            validate_run_plan(plan)

    def test_plan_rejects_duplicate_json_keys_in_snapshot(self) -> None:
        plan = copy.deepcopy(self.plan)
        path = "datasets/benchmark_cases_v2.json"
        payload = b'{"schema_version":2,"schema_version":2,"cases":[{"id":"T001"}]}'
        plan["input_snapshots"][path] = base64.b64encode(payload).decode("ascii")
        plan["input_hashes"][path] = hashlib.sha256(payload).hexdigest()
        with self.assertRaisesRegex(ValueError, "input_snapshots"):
            validate_run_plan(plan)

    def test_functional_record_validates_before_append_and_matches_plan(self) -> None:
        key = self.plan["calendar"][0]["execution_key"]
        record = {
            "schema_version": 3,
            "run_id": self.plan["run_id"],
            "execution_key": key,
            "measurement_key": key,
            "status": "completed",
            "eligible_for_main_score": True,
            "power_condition": "ac_power",
            "model": "fake:latest",
            "repetition": 1,
            "case": self.case,
            "started_at_utc": "2026-09-22T12:00:00+00:00",
            "completed_at_utc": "2026-09-22T12:00:01+00:00",
            "wall_duration_seconds": 1.0,
            "runner_error": None,
            "run": {
                "turns": [],
                "tool_events": [],
                "assistant_tool_turns": [],
                "final_content": "ok",
                "max_turns_reached": False,
                "virtual_final_files": {},
                "evaluation": {
                    "passed": True,
                    "mode": "text_contains",
                    "checks": {"final_contains": True},
                    "failed_checks": [],
                },
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            append_primary_record(path, "functional", record, self.plan)
            original = path.read_bytes()
            self.assertEqual(list(iter_jsonl(path)), [record])
            for field, value in (
                ("measurement_key", "unknown"),
                ("model", "other"),
                ("status", "execution_failure"),
            ):
                with self.subTest(field=field):
                    invalid = {**record, field: value}
                    with self.assertRaisesRegex(ValueError, "registro"):
                        append_primary_record(path, "functional", invalid, self.plan)
                    self.assertEqual(path.read_bytes(), original)
            append_jsonl(path, record)
            with self.assertRaisesRegex(ValueError, "duplicadas"):
                validate_resume_evidence(
                    self.plan, {"functional": path}, Path(directory) / "integrity.jsonl"
                )

    def test_preflight_rejects_version_and_digest_from_materialized_plan(self) -> None:
        expected = self.plan["models"][0]
        for version, digest, failure in (
            ("changed", expected["digest"], "versión"),
            (self.plan["ollama"]["version"], "sha256:" + "b" * 64, "digest"),
        ):
            with self.subTest(failure=failure):
                responses = [
                    {"version": version},
                    {"models": [{"name": expected["name"], "digest": digest}]},
                ]
                with (
                    mock.patch(
                        "ollama_agent_benchmark.run_plan.get_json", side_effect=responses
                    ) as request,
                    self.assertRaisesRegex(RuntimeError, failure),
                ):
                    preflight_run_plan(self.plan)
                self.assertEqual(
                    request.call_args_list[0].args[0], "http://127.0.0.1:11434/api/version"
                )
                self.assertEqual(request.call_count, 1 if failure == "versión" else 2)

    def test_planning_inputs_reject_unknown_fields_without_coercion(self) -> None:
        config = json.loads((ROOT / "config/benchmark.example.json").read_text())
        lock = {
            "schema_version": 3,
            "benchmark_version": "0.3.0",
            "ollama_base_url": "http://127.0.0.1:11434",
            "ollama_server_version": "0.99.0-fake",
            "models": [{"name": name, "digest": "sha256:" + "a" * 64} for name in config["models"]],
        }
        original = copy.deepcopy(config)
        validate_planning_inputs(config, lock)
        self.assertEqual(config, original)
        lock["models"][0]["digest"] = "a" * 64
        validate_planning_inputs(config, lock)
        config["functional"]["repetitions"] = "3"
        with self.assertRaisesRegex(ValueError, "functional.repetitions"):
            validate_planning_inputs(config, lock)
        config["functional"]["repetitions"] = 3
        config["unknown"] = 1
        with self.assertRaisesRegex(ValueError, "config.unknown"):
            validate_planning_inputs(config, lock)
        del config["unknown"]
        config["ollama"]["base_url"] += "/?token=secret-value"
        with self.assertRaisesRegex(ValueError, "base_url") as error:
            validate_planning_inputs(config, lock)
        self.assertNotIn("secret-value", str(error.exception))


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
                        "schema_version": 3,
                        "benchmark_version": "0.3.0",
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
                        "preflight_run_plan",
                        side_effect=AssertionError("contactó Ollama"),
                    ),
                    redirect_stdout(StringIO()),
                ):
                    self.assertEqual(
                        functional.main(["--mode", "dry-run", "--run-id", "preview"]), 0
                    )
                self.assertFalse((root / "runs").exists())

                legacy_dir = root / "runs/legacy"
                legacy_dir.mkdir(parents=True)
                (legacy_dir / "run_manifest.json").write_text("{}")
                error = StringIO()
                with redirect_stdout(StringIO()), redirect_stderr(error):
                    self.assertEqual(
                        functional.main(
                            ["--mode", "official-functional", "--run-id", "legacy", "--resume"]
                        ),
                        4,
                    )
                self.assertIn("run v2 sin plan v3", error.getvalue())

                def functional_preflight(_plan: object) -> None:
                    plan = validate_run_plan(json.loads((root / "runs/f/plan.json").read_text()))
                    self.assertEqual(plan["effective"]["repetitions"], 1)
                    raise RuntimeError(
                        "token=secret-value https://localhost/?api_key=url-secret"
                    )

                error = StringIO()
                with (
                    mock.patch.object(
                        functional, "preflight_run_plan", side_effect=functional_preflight
                    ),
                    redirect_stdout(StringIO()),
                    redirect_stderr(error),
                ):
                    self.assertEqual(functional.main(functional_args), 1)
                self.assertNotIn("secret-value", error.getvalue())
                self.assertNotIn("url-secret", error.getvalue())
                plan_path = root / "runs/f/plan.json"
                original = plan_path.read_bytes()
                with (
                    mock.patch.object(
                        functional,
                        "preflight_run_plan",
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

                original_config = config_path.read_bytes()
                original_cases = (data_dir / "benchmark_cases_v2.json").read_bytes()
                config_path.write_text("{}")
                (data_dir / "benchmark_cases_v2.json").write_text("{}")
                with (
                    mock.patch.object(
                        functional,
                        "preflight_run_plan",
                        side_effect=RuntimeError("reanuda desde el plan"),
                    ) as preflight,
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    self.assertEqual(
                        functional.main(
                            [
                                "--mode",
                                "official-functional",
                                "--run-id",
                                "f",
                                "--resume",
                            ]
                        ),
                        1,
                    )
                preflight.assert_called_once()
                config_path.write_bytes(original_config)
                (data_dir / "benchmark_cases_v2.json").write_bytes(original_cases)

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

                def performance_preflight(_plan: object) -> None:
                    plan = validate_run_plan(json.loads((root / "runs/p/plan.json").read_text()))
                    self.assertEqual(plan["effective"]["ttft_runs"], 0)
                    self.assertFalse(
                        any(item["measurement_type"] == "ttft" for item in plan["calendar"])
                    )
                    raise ValueError(
                        "token=secret-value https://localhost/?api_key=url-secret"
                    )

                error = StringIO()
                with (
                    mock.patch.object(
                        performance, "preflight_run_plan", side_effect=performance_preflight
                    ),
                    redirect_stdout(StringIO()),
                    redirect_stderr(error),
                ):
                    self.assertEqual(performance.main(performance_args), 1)
                self.assertNotIn("secret-value", error.getvalue())
                self.assertNotIn("url-secret", error.getvalue())
                plan_path = root / "runs/p/plan.json"
                original = plan_path.read_bytes()
                with (
                    mock.patch.object(
                        performance,
                        "preflight_run_plan",
                        side_effect=AssertionError("contactó Ollama"),
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

                config_path.write_text("{}")
                (data_dir / "performance_workloads_v2.json").write_text("{}")
                with (
                    mock.patch.object(
                        performance,
                        "preflight_run_plan",
                        side_effect=ValueError("reanuda desde el plan"),
                    ) as preflight,
                    redirect_stdout(StringIO()),
                    redirect_stderr(StringIO()),
                ):
                    self.assertEqual(
                        performance.main(
                            [
                                "--mode",
                                "official-performance",
                                "--run-id",
                                "p",
                                "--resume",
                            ]
                        ),
                        1,
                    )
                preflight.assert_called_once()

    def test_dry_run_creates_no_canonical_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            config = root / "config/benchmark.json"
            config.write_bytes((ROOT / "config/benchmark.example.json").read_bytes())
            config_data = json.loads(config.read_text())
            datasets = root / "datasets"
            datasets.mkdir()
            workloads_path = datasets / "performance_workloads_v2.json"
            workloads_path.write_bytes(
                (ROOT / "datasets/performance_workloads_v2.json").read_bytes()
            )
            (root / "config/models.lock.json").write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "benchmark_version": "0.3.0",
                        "ollama_base_url": "http://127.0.0.1:11434",
                        "ollama_server_version": "0.99.0-fake",
                        "models": [
                            {"name": name, "digest": "sha256:" + "a" * 64}
                            for name in config_data["models"]
                        ],
                    }
                )
            )
            output = StringIO()
            with (
                mock.patch.object(performance, "ROOT", root),
                mock.patch.object(performance, "CONFIG_PATH", config),
                mock.patch.object(performance, "WORKLOADS_PATH", workloads_path),
                mock.patch.object(
                    performance, "preflight_run_plan", side_effect=AssertionError("contactó Ollama")
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(performance.main(["--mode", "dry-run", "--run-id", "preview"]), 0)
            self.assertIn("No se llamó a Ollama", output.getvalue())
            self.assertFalse((root / "runs").exists())
