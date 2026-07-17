"""Drop-in replacement for the `xformers` package used by TRELLIS.

Real xformers wheels are compiled against a specific torch build and lag
behind torch cu128 releases on Windows; TRELLIS only calls
`xformers.ops.memory_efficient_attention` with a `BlockDiagonalMask`
(variable-length batch attention), which maps 1:1 onto torch's native
scaled_dot_product_attention. See `ops/__init__.py`.

Keep XFORMERS_DISABLED=1 in the environment so DINOv2 (torch.hub) takes its
pure-torch path instead of importing APIs this shim does not provide.
"""

__version__ = "0.0.0+printcad-sdpa-shim"
