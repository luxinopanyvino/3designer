"""Standalone sandbox runner, executed in a subprocess by cad_executor.

Usage: python runner.py <code_file> <out_dir>

Executes the generated CadQuery script, expects the final solid in a variable
named `result`, exports model.stl (binary) and model.step into <out_dir>, and
prints exactly one JSON line to stdout:

    {"ok": true}
    {"ok": false, "error_type": "...", "traceback": "..."}

The traceback is trimmed to the frames of the generated code so the LLM sees
line numbers that match its own script.
"""

import json
import sys
import traceback
from pathlib import Path

CODE_FILENAME = "model.py"
STL_TOLERANCE = 0.05


def emit(payload: dict) -> None:
    print(json.dumps(payload), flush=True)


def fail(error_type: str, message: str) -> None:
    emit({"ok": False, "error_type": error_type, "traceback": message})
    sys.exit(0)


def trimmed_traceback(exc: BaseException) -> str:
    frames = [
        frame
        for frame in traceback.extract_tb(exc.__traceback__)
        if frame.filename == CODE_FILENAME
    ]
    lines = traceback.format_list(frames) if frames else []
    lines += traceback.format_exception_only(exc)
    return "".join(lines).strip()


def main() -> None:
    code_file, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    code = code_file.read_text(encoding="utf-8")

    import math

    import cadquery as cq
    import numpy

    namespace = {
        "cq": cq,
        "cadquery": cq,
        "math": math,
        "numpy": numpy,
        "np": numpy,
        "__name__": "__cad_model__",
    }

    try:
        exec(compile(code, CODE_FILENAME, "exec"), namespace)
    except BaseException as exc:  # noqa: BLE001 - anything the script raises goes to the LLM
        fail(type(exc).__name__, trimmed_traceback(exc))

    result = namespace.get("result")
    if result is None:
        fail(
            "MissingResult",
            "The script must assign the final solid to a variable named `result`.",
        )

    if isinstance(result, cq.Workplane) and not result.vals():
        fail("EmptyResult", "`result` is an empty Workplane with no solid in it.")

    try:
        cq.exporters.export(result, str(out_dir / "model.stl"), tolerance=STL_TOLERANCE)
        cq.exporters.export(result, str(out_dir / "model.step"))
    except BaseException as exc:  # noqa: BLE001
        fail(
            type(exc).__name__,
            "Exporting `result` failed - it is probably not a valid solid. "
            + trimmed_traceback(exc),
        )

    emit({"ok": True})


if __name__ == "__main__":
    main()
