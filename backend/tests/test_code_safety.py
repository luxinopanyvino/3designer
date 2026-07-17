from app.services.code_safety import check_code

VALID_CODE = """
import cadquery as cq
import math

WIDTH = 40.0
result = cq.Workplane("XY").box(WIDTH, 20, 3)
"""


def test_valid_code_passes():
    assert check_code(VALID_CODE) is None

def test_syntax_error_reported():
    err = check_code("result = (")
    assert err is not None and "SyntaxError" in err

def test_forbidden_import():
    err = check_code("import os\nresult = None")
    assert err is not None and "os" in err

def test_forbidden_import_from():
    err = check_code("from subprocess import run\nresult = None")
    assert err is not None

def test_forbidden_name():
    err = check_code("data = open('x.txt')")
    assert err is not None and "open" in err

def test_forbidden_dunder():
    err = check_code("x = (1).__class__")
    assert err is not None and "__class__" in err

def test_numpy_and_math_allowed():
    assert check_code("import numpy as np\nimport math\nx = np.array([1])") is None
