import json
from pathlib import Path

from scr.application_benchmark import ApplicationThreadBenchmark


def test_application_thread_loads_from_json() -> None:
    benchmark = ApplicationThreadBenchmark()

    thread = benchmark.load_thread(Path("tasks/task_001/application_thread.json").resolve())

    assert thread.thread_id == "thread_task_001"
    assert "divergence" in thread.required_competences


def test_application_thread_benchmark_produces_scr_thread_result(tmp_path) -> None:
    benchmark = ApplicationThreadBenchmark(output_path=tmp_path / "thread_benchmark.json")

    result_path = benchmark.run(
        Path("tasks/task_001/application_thread.json").resolve(),
        Path("tasks/task_001").resolve(),
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert "scr_thread_result" in payload
    assert "outcome" in payload["scr_thread_result"]


def test_application_thread_benchmark_produces_baseline_thread_result(tmp_path) -> None:
    benchmark = ApplicationThreadBenchmark(output_path=tmp_path / "thread_benchmark.json")

    result_path = benchmark.run(
        Path("tasks/task_001/application_thread.json").resolve(),
        Path("tasks/task_001").resolve(),
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert "baseline_thread_result" in payload
    assert "outcome" in payload["baseline_thread_result"]


def test_application_thread_benchmark_calculates_resource_cost_score(tmp_path) -> None:
    benchmark = ApplicationThreadBenchmark(output_path=tmp_path / "thread_benchmark.json")

    result_path = benchmark.run(
        Path("tasks/task_001/application_thread.json").resolve(),
        Path("tasks/task_001").resolve(),
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert payload["scr_thread_result"]["resource_cost_score"] > 0
    assert payload["baseline_thread_result"]["resource_cost_score"] > 0


def test_application_thread_benchmark_calculates_deltas(tmp_path) -> None:
    benchmark = ApplicationThreadBenchmark(output_path=tmp_path / "thread_benchmark.json")

    result_path = benchmark.run(
        Path("tasks/task_001/application_thread.json").resolve(),
        Path("tasks/task_001").resolve(),
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert "quality_delta" in payload
    assert "cost_delta" in payload
    assert "value_delta" in payload
