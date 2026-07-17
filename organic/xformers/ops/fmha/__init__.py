"""Minimal BlockDiagonalMask: only records the per-sample sequence lengths;
`ops.memory_efficient_attention` interprets them."""


class BlockDiagonalMask:
    def __init__(self, q_seqlen, kv_seqlen):
        self.q_seqlen = list(q_seqlen)
        self.kv_seqlen = list(kv_seqlen)

    @classmethod
    def from_seqlens(cls, q_seqlen, kv_seqlen=None):
        return cls(q_seqlen, kv_seqlen if kv_seqlen is not None else q_seqlen)
