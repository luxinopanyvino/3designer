Analyze this image of a mechanical part to be reproduced as a 3D-printable model.

Reply with ONLY a JSON object, no prose, with this shape:

{
  "part_type": "short name of the part",
  "overall_dims_estimate_mm": {"x": 0, "y": 0, "z": 0},
  "features": [
    {"type": "hole|slot|boss|rib|fillet|chamfer|pattern|other", "count": 1, "position": "description", "size_mm": 0}
  ],
  "notes": "anything relevant for modeling it (symmetry, proportions, function)"
}

Estimate dimensions from visual proportions; the user may provide one real dimension to scale from.
