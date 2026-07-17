"""Runs LLM-generated CadQuery code in an isolated subprocess with a timeout."""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "sandbox" / "runner.py"
CREATIONFLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


@dataclass
class ExecResult:
    ok: bool
    error: str | None = None  # message suitable for the LLM repair prompt
    stl_path: Path | None = None
    step_path: Path | None = None


def execute_cad_code(code: str, out_dir: Path, timeout_s: int = 60) -> ExecResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    code_file = out_dir / "code.py"
    code_file.write_text(code, encoding="utf-8")

    try:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), str(code_file), str(out_dir)],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            creationflags=CREATIONFLAGS,
        )
    except subprocess.TimeoutExpired:
        return ExecResult(
            ok=False,
            error=(
                f"Execution timed out after {timeout_s} seconds "
                "(possible infinite loop or excessive geometry)."
            ),
        )

    payload = _parse_runner_output(proc.stdout)
    if payload is None:
        # Runner died without reporting (e.g. OCC segfault).
        detail = (proc.stderr or "").strip()[-500:]
        return ExecResult(
            ok=False,
            error=(
                "The CAD kernel crashed while building the model "
                f"(exit code {proc.returncode}). {detail}"
            ),
        )

    if not payload.get("ok"):
        return ExecResult(ok=False, error=payload.get("traceback", "Unknown error"))

    stl_path = out_dir / "model.stl"
    step_path = out_dir / "model.step"
    if not stl_path.exists():
        return ExecResult(ok=False, error="Runner reported success but model.stl is missing.")
    return ExecResult(ok=True, stl_path=stl_path, step_path=step_path)


def _parse_runner_output(stdout: str) -> dict | None:
    """The runner prints one JSON line; generated code may print noise before it."""
    for line in reversed((stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None
