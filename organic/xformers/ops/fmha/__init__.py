"""Minimal BlockDiagonalMask: only records the per-block sequence lengths;
`ops.memory_efficient_attention` interprets them.

TRELLIS v1 passes plain Python lists. TRELLIS.2's windowed attention passes a
CUDA tensor straight out of `torch.bincount`, so lengths are kept as-is rather
than coerced to a list -- converting would force a device sync per layer.
"""


class BlockDiagonalMask:
    def __init__(self, q_seqlen, kv_seqlen):
        self.q_seqlen = q_seqlen
        self.kv_seqlen = kv_seqlen

    @classmethod
    def from_seqlens(cls, q_seqlen, kv_seqlen=None):
        return cls(q_seqlen, q_seqlen if kv_seqlen is None else kv_seqlen)
