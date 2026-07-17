"""SDPA-backed implementation of the xformers ops TRELLIS uses.

TRELLIS (trellis/modules/sparse/attention/full_attn.py) calls:

    mask = xops.fmha.BlockDiagonalMask.from_seqlens(q_seqlen, kv_seqlen)
    out = xops.memory_efficient_attention(q, k, v, mask)

with q/k/v of shape [1, T, H, C] where T concatenates the per-sample
sequences. With a single sample (this service always sends one image) the
block-diagonal mask is one block, i.e. plain full attention; the multi-block
case falls back to one SDPA call per block.
"""

import torch
import torch.nn.functional as F

from . import fmha
from .fmha import BlockDiagonalMask

__all__ = ["memory_efficient_attention", "unbind", "fmha", "BlockDiagonalMask"]


def unbind(x: torch.Tensor, dim: int = 0):
    return torch.unbind(x, dim=dim)


def _sdpa(q, k, v, scale=None):
    # xformers layout [B, M, H, K] -> SDPA layout [B, H, M, K] and back
    out = F.scaled_dot_product_attention(
        q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2), scale=scale
    )
    return out.transpose(1, 2)


def memory_efficient_attention(q, k, v, attn_bias=None, p=0.0, scale=None):
    if p != 0.0:
        raise NotImplementedError("dropout is not supported by the SDPA shim")
    if attn_bias is None:
        return _sdpa(q, k, v, scale)
    if isinstance(attn_bias, torch.Tensor):
        out = F.scaled_dot_product_attention(
            q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2),
            attn_mask=attn_bias, scale=scale,
        )
        return out.transpose(1, 2)
    if isinstance(attn_bias, BlockDiagonalMask):
        if len(attn_bias.q_seqlen) == 1:
            return _sdpa(q, k, v, scale)
        outs = []
        q0, k0 = 0, 0
        for lq, lkv in zip(attn_bias.q_seqlen, attn_bias.kv_seqlen):
            outs.append(_sdpa(q[:, q0:q0 + lq], k[:, k0:k0 + lkv], v[:, k0:k0 + lkv], scale))
            q0 += lq
            k0 += lkv
        return torch.cat(outs, dim=1)
    raise NotImplementedError(f"unsupported attn_bias type: {type(attn_bias)}")
