import json
from pathlib import Path

from scr.baseline import BaselineRunner
from scr.benchmark import BenchmarkRunner


def test_baseline_runner_executes_on_temporary_copy() -> None:
    runner = BaselineRunner()

    result = runner.run(Path("tasks/task_001").resolve())

    assert "scr-baseline-" in result["temporary_task_path"]
    assert Path(result["temporary_task_path"]).name == "task_001"


def test_baseline_runner_does_not_modify_original_files() -> None:
    task_path = Path("tasks/task_001").resolve()
    original_bug = (task_path / "bug.py").read_text(encoding="utf-8")
    original_test = (task_path / "test_bug.py").read_text(encoding="utf-8")
    original_meta = (task_path / "meta.txt").read_text(encoding="utf-8")

    BaselineRunner().run(task_path)

    assert (task_path / "bug.py").read_text(encoding="utf-8") == original_bug
    assert (task_path / "test_bug.py").read_text(encoding="utf-8") == original_test
    assert (task_path / "meta.txt").read_text(encoding="utf-8") == original_meta


def test_benchmark_runner_produces_json(tmp_path) -> None:
    output_path = tmp_path / ".scr" / "benchmarks" / "benchmark_result.json"
    runner = BenchmarkRunner(output_path=output_path)

    result_path = runner.run(Path("tasks/task_001").resolve())

    assert result_path.exists()
    assert result_path == output_path


def test_benchmark_result_contains_scr_and_baseline_metrics(tmp_path) -> None:
    output_path = tmp_path / ".scr" / "benchmarks" / "benchmark_result.json"
    runner = BenchmarkRunner(output_path=output_path)

    result_path = runner.run(Path("tasks/task_001").resolve())
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    expected_keys = {
        "task_id",
        "scr_outcome",
        "baseline_outcome",
        "scr_ticks",
        "scr_hypothesis_count",
        "scr_validated_hypothesis_count",
        "scr_validation_time_ms",
        "baseline_validation_time_ms",
        "winner",
    }
    assert set(payload) >= expected_keys


def test_benchmark_contains_reference_model_result_section(tmp_path) -> None:
    output_path = tmp_path / ".scr" / "benchmarks" / "benchmark_result.json"
    payload = json.loads(BenchmarkRunner(output_path=output_path).run(Path("tasks/task_001").resolve()).read_text(encoding="utf-8"))

    assert "reference_model_result" in payload
    assert payload["reference_model_result"]["outcome"] == "SUCCESS"


def test_benchmark_contains_efficiency_score(tmp_path) -> None:
    output_path = tmp_path / ".scr" / "benchmarks" / "benchmark_result.json"
    payload = json.loads(BenchmarkRunner(output_path=output_path).run(Path("tasks/task_001").resolve()).read_text(encoding="utf-8"))

    assert "efficiency_score" in payload["scr_result"]
    assert "efficiency_score" in payload["baseline_result"]
    assert "efficiency_score" in payload["reference_model_result"]


def test_scr_can_be_compared_with_reference_model_result(tmp_path) -> None:
    output_path = tmp_path / ".scr" / "benchmarks" / "benchmark_result.json"
    payload = json.loads(BenchmarkRunner(output_path=output_path).run(Path("tasks/task_001").resolve()).read_text(encoding="utf-8"))

    assert payload["comparison"]["winner"] in {"SCR", "BASELINE", "REFERENCE_MODEL"}
    assert "REFERENCE_MODEL" in payload["comparison"]["scores"]


def test_benchmark_legacy_fields_remain_present(tmp_path) -> None:
    output_path = tmp_path / ".scr" / "benchmarks" / "benchmark_result.json"
    payload = json.loads(BenchmarkRunner(output_path=output_path).run(Path("tasks/task_001").resolve()).read_text(encoding="utf-8"))

    assert "scr_outcome" in payload
    assert "baseline_outcome" in payload
    assert "winner" in payload


def test_benchmark_winner_is_deterministic(tmp_path) -> None:
    left_path = tmp_path / "left" / "benchmark_result.json"
    right_path = tmp_path / "right" / "benchmark_result.json"
    task_path = Path("tasks/task_001").resolve()

    left_payload = json.loads(BenchmarkRunner(output_path=left_path).run(task_path).read_text(encoding="utf-8"))
    right_payload = json.loads(BenchmarkRunner(output_path=right_path).run(task_path).read_text(encoding="utf-8"))

    assert left_payload["winner"] == right_payload["winner"]


def test_benchmark_default_path_creates_run_id_directory(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    runner = BenchmarkRunner()

    result_path = runner.run((Path(__file__).resolve().parent.parent / "tasks" / "task_001").resolve())

    assert result_path.parent.name.startswith("run_")
    assert result_path.parent.parent == Path(".scr") / "benchmarks"


def test_benchmark_default_path_saves_task_file_in_run_subdirectory(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    runner = BenchmarkRunner()

    result_path = runner.run((Path(__file__).resolve().parent.parent / "tasks" / "task_001").resolve())

    assert result_path.name == "task_001.json"
    assert result_path.exists()


def test_benchmark_default_path_differs_between_consecutive_runs(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    runner = BenchmarkRunner()
    task_path = (Path(__file__).resolve().parent.parent / "tasks" / "task_001").resolve()

    first_path = runner.run(task_path)
    second_path = runner.run(task_path)

    assert first_path != second_path


def test_benchmark_explicit_output_path_still_works(tmp_path) -> None:
    output_path = tmp_path / "explicit" / "benchmark_result.json"
    runner = BenchmarkRunner(output_path=output_path)

    result_path = runner.run(Path("tasks/task_001").resolve())

    assert result_path == output_path
    assert result_path.exists()
