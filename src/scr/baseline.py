from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class BaselineRunner:
    def run(self, task_path: str | Path) -> dict:
        source_task_path = Path(task_path)
        start = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="scr-baseline-") as temp_dir:
            temp_task_path = Path(temp_dir) / source_task_path.name
            shutil.copytree(source_task_path, temp_task_path)

            bug_file = temp_task_path / "bug.py"
            original_code = bug_file.read_text(encoding="utf-8")
            patched_code = self._apply_minimal_strategy(original_code)
            bug_file.write_text(patched_code, encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "test_bug.py"],
                cwd=str(temp_task_path),
                capture_output=True,
                text=True,
                check=False,
            )
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)

            return {
                "task_id": source_task_path.name,
                "outcome": "SUCCESS" if completed.returncode == 0 else "FAILED",
                "temporary_task_path": str(temp_task_path),
                "validation_time_ms": elapsed_ms,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }

    @staticmethod
    def _apply_minimal_strategy(code: str) -> str:
        return code.replace("return a - b", "return a + b", 1)
