"""Drop-in replacement for the `torchmcubes` package used by TripoSR.

The real torchmcubes needs a C++/CUDA build on Windows; scikit-image ships
prebuilt wheels and its marching cubes is fast enough (one call per model,
~1-2 s at 256^3). Mimics torchmcubes' vertex axis order so TripoSR's
`v_pos[..., [2, 1, 0]]` flip lands back on volume (i, j, k) coordinates.
"""

import numpy as np
import torch
from skimage import measure


def marching_cubes(vol: torch.Tensor, threshold: float):
    array = vol.detach().cpu().numpy()
    verts, faces, _normals, _values = measure.marching_cubes(array, level=threshold)
    verts = np.ascontiguousarray(verts[:, [2, 1, 0]], dtype=np.float32)
    faces = np.ascontiguousarray(faces, dtype=np.int64)
    return torch.from_numpy(verts), torch.from_numpy(faces)
