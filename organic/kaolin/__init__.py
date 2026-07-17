"""Drop-in replacement for the `kaolin` package used by TRELLIS's FlexiCubes.

FlexiCubes only imports `kaolin.utils.testing.check_tensor` for shape
assertions; real kaolin requires a build matched to the exact torch version
and is unavailable as a Windows cu128 wheel. See `utils/testing.py`.
"""
