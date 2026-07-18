from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ollama_agent_benchmark import report


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


class ReportIntegrationTests(unittest.TestCase):
    def test_compatible_report_generates_all_formats_and_rejects_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            functional_dir = root / "functional"
            performance_dir = root / "performance"
            output = root / "report"
            functional_dir.mkdir()
            performance_dir.mkdir()
            scoring = {
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
                "workload_weights": {"w": 1.0},
                "missing_metric_policy": "incomplete_score",
            }
            common = {
                "schema_version": 2,
                "benchmark_version": "0.2.0",
                "eligible_for_main_score": True,
                "models": ["m"],
                "model_identities": [{"name": "m", "digest": "sha256:a"}],
                "order_control": {"seed": 1},
                "config_fingerprint": "config-hash",
                "ollama_base_url": "http://127.0.0.1:9999",
                "scoring_protocol": scoring,
            }
            functional_manifest = {
                **common,
                "mode": "official-functional",
                "ollama_version": "fake",
                "options": {"seed": 1},
                "case_ids": ["T", "Q"],
                "repetitions": 1,
                "input_hashes": {
                    "datasets/benchmark_cases_v2.json": "a",
                    "datasets/fixtures_v2.json": "b",
                    "datasets/tools_v2.json": "c",
                },
            }
            performance_manifest = {
                **common,
                "mode": "official-performance",
                "ollama_server_version": "fake",
                "generation": {"seed": 1},
                "workloads": ["w"],
                "cold_runs": 1,
                "hot_runs": 1,
                "ttft_runs": 1,
                "workloads_hash": "workload-hash",
            }
            write_json(functional_dir / "run_manifest.json", functional_manifest)
            write_json(performance_dir / "performance_manifest.json", performance_manifest)
            records = []
            for case_id, track in (("T", "tool_reliability"), ("Q", "quality_reasoning")):
                records.append(
                    {
                        "model": "m",
                        "repetition": 1,
                        "case": {"id": case_id, "track": track},
                        "run": {"evaluation": {"passed": True}},
                        "runner_error": None,
                    }
                )
            (functional_dir / "records.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8"
            )
            perf_records = [
                {"execution_key": "m:w:cold:1", "measurement_key": "m:w:cold:1"},
                {"execution_key": "m:w:hot:1", "measurement_key": "m:w:hot:1"},
            ]
            (performance_dir / "performance_records.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in perf_records), encoding="utf-8"
            )
            (performance_dir / "ttft_records.jsonl").write_text(
                json.dumps({"execution_key": "ttft:m:w:1", "measurement_key": "ttft:m:w:1"}) + "\n",
                encoding="utf-8",
            )

            def metric(value: float) -> dict[str, float]:
                return {"median": value}

            aggregate = {
                "hot_generation_tps": metric(10),
                "hot_prompt_tps": metric(20),
                "hot_total_seconds": metric(1),
                "cold_load_seconds": metric(2),
                "ttft_seconds": metric(0.1),
                "size_vram_bytes": metric(1024),
                "swap_delta_bytes": metric(0),
            }
            write_json(
                performance_dir / "performance_summary.json",
                {
                    "schema_version": 2,
                    "models": {
                        "m": {
                            "records": 2,
                            "runner_errors": 0,
                            "aggregate": aggregate,
                            "workloads": {"w": {}},
                        }
                    },
                },
            )
            self.assertEqual(
                report.main(
                    [
                        "--functional-run",
                        str(functional_dir),
                        "--performance-run",
                        str(performance_dir),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            for relative in ("report.md", "report.json", "scores.csv", "charts/final_score.svg"):
                self.assertTrue((output / relative).is_file(), relative)

            functional_manifest["schema_version"] = 1
            write_json(functional_dir / "run_manifest.json", functional_manifest)
            self.assertEqual(
                report.main(
                    [
                        "--functional-run",
                        str(functional_dir),
                        "--performance-run",
                        str(performance_dir),
                        "--output",
                        str(root / "bad"),
                    ]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
