from app.services.cad_executor import execute_cad_code

VALID_BRACKET = """
import cadquery as cq

LENGTH = 40.0
WIDTH = 20.0
THICKNESS = 3.0
HOLE_D = 3.2

result = (
    cq.Workplane("XY")
    .box(LENGTH, WIDTH, THICKNESS, centered=(True, True, False))
    .faces(">Z")
    .workplane()
    .pushPoints([(-15, 0), (15, 0)])
    .hole(HOLE_D)
)
"""


def test_valid_code_produces_stl_and_step(tmp_path):
    res = execute_cad_code(VALID_BRACKET, tmp_path, timeout_s=90)
    assert res.ok, res.error
    assert res.stl_path.exists() and res.stl_path.stat().st_size > 0
    assert res.step_path.exists() and res.step_path.stat().st_size > 0


def test_runtime_error_reports_trimmed_traceback(tmp_path):
    code = (
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(10, 10, 10).edges().fillet(50)\n"
    )
    res = execute_cad_code(code, tmp_path, timeout_s=90)
    assert not res.ok
    assert "line 2" in res.error or "fillet" in res.error.lower()


def test_missing_result_variable(tmp_path):
    res = execute_cad_code("import cadquery as cq\nx = cq.Workplane('XY').box(5, 5, 5)", tmp_path, timeout_s=90)
    assert not res.ok
    assert "result" in res.error


def test_infinite_loop_times_out(tmp_path):
    res = execute_cad_code("while True:\n    pass", tmp_path, timeout_s=8)
    assert not res.ok
    assert "timed out" in res.error


def test_print_noise_does_not_break_protocol(tmp_path):
    code = (
        "import cadquery as cq\n"
        "print('debug noise {not json}')\n"
        "result = cq.Workplane('XY').box(10, 10, 10)\n"
    )
    res = execute_cad_code(code, tmp_path, timeout_s=90)
    assert res.ok, res.error
