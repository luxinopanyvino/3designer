"""Static AST allowlist check for LLM-generated CadQuery code.

This runs in-process before any code is executed. A rejection is fed back to
the LLM through the repair prompt, exactly like a runtime error.
"""

import ast

ALLOWED_IMPORTS = {"cadquery", "build123d", "math", "numpy"}

FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "input", "breakpoint",
    "globals", "locals", "vars", "memoryview",
    "os", "sys", "subprocess", "socket", "pathlib", "shutil", "importlib",
    "ctypes", "pickle", "marshal", "builtins",
}

ALLOWED_DUNDER_ATTRS = {"__name__"}


def check_code(code: str) -> str | None:
    """Return a human/LLM-readable error message if the code is unsafe, else None."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    return (
                        f"Forbidden import '{alias.name}'. "
                        f"Only these imports are allowed: cadquery, math, numpy."
                    )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.level != 0 or root not in ALLOWED_IMPORTS:
                return (
                    f"Forbidden import 'from {node.module or '.'}'. "
                    f"Only these imports are allowed: cadquery, math, numpy."
                )
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return (
                f"Forbidden name '{node.id}'. Do not use file/system access or "
                f"dynamic execution; only cadquery, math and numpy operations."
            )
        elif isinstance(node, ast.Attribute):
            attr = node.attr
            if attr.startswith("__") and attr.endswith("__") and attr not in ALLOWED_DUNDER_ATTRS:
                return f"Forbidden dunder attribute access '{attr}'."

    return None
