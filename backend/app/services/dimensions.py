"""Extract a target dimension in mm from a free-form user prompt.

Regex only — a local LLM round trip costs a VRAM model swap for phrases
that are almost always "<number> mm/cm"-shaped.
"""

import re

AXIS_WORDS = {
    "alto": "height",
    "altura": "height",
    "height": "height",
    "ancho": "width",
    "anchura": "width",
    "largo": "width",
    "width": "width",
    "diámetro": "width",
    "diametro": "width",
}

_DIMENSION_RE = re.compile(
    r"(?:(\w+)\s+(?:de\s+)?)?(\d+(?:[.,]\d+)?)\s*(mm|cm)\b",
    re.IGNORECASE,
)


def parse_target_size_mm(text: str) -> tuple[float, str | None] | None:
    """First '<number> mm|cm' in the text -> (value_mm, 'width'|'height'|None)."""
    if not text:
        return None
    match = _DIMENSION_RE.search(text)
    if match is None:
        return None
    word, number, unit = match.groups()
    value = float(number.replace(",", "."))
    if unit.lower() == "cm":
        value *= 10.0
    axis = AXIS_WORDS.get(word.lower()) if word else None
    return value, axis
