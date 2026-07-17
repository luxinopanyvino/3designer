"""Minimal `check_tensor` with kaolin's semantics: validate shape (None = any
size), dtype and device; return the verdict or raise when `throw`."""


def check_tensor(tensor, shape=None, dtype=None, device=None, throw=True):
    ok = True
    if shape is not None:
        ok = len(tensor.shape) == len(shape) and all(
            expected is None or actual == expected
            for actual, expected in zip(tensor.shape, shape)
        )
    if ok and dtype is not None:
        ok = tensor.dtype == dtype
    if ok and device is not None:
        ok = str(tensor.device) == str(device)
    if not ok and throw:
        raise ValueError(
            f"tensor check failed: shape {tuple(tensor.shape)} vs {shape}, "
            f"dtype {tensor.dtype} vs {dtype}, device {tensor.device} vs {device}"
        )
    return ok
