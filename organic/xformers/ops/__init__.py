"""SDPA-backed implementation of the xformers ops TRELLIS and TRELLIS.2 use.

Both versions call the same two entry points:

    mask = xops.fmha.BlockDiagonalMask.from_seqlens(q_seqlen, kv_seqlen)
    out = xops.memory_efficient_attention(q, k, v, mask)

with q/k/v of shape [1, T, H, C] where T concatenates the per-block sequences.

TRELLIS v1 only ever produced a single block (one image per request), so a plain
SDPA call sufficed. TRELLIS.2 also runs *windowed* sparse attention, where every
spatial window is its own block -- thousands of them per layer, with wildly
uneven lengths. Those go through a jagged nested tensor, which SDPA attends to
in one launch with no padding: measured on a 2000-block layer that is ~5x faster
than looping per block and uses less memory than either the loop or a padded
batch (padding to the longest window costs several GB when the distribution is
skewed, which matters on a 16 GB card).
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


def _jagged_sdpa(q, k, v, seqlens, scale=None):
    """Block-diagonal self-attention via a jagged nested tensor (one SDPA launch)."""
    lens = torch.as_tensor(seqlens, device=q.device, dtype=torch.long).reshape(-1)
    offsets = torch.zeros(lens.numel() + 1, dtype=torch.long, device=q.device)
    torch.cumsum(lens, 0, out=offsets[1:])

    def jag(x):  # [1, T, H, C] -> nested [B, *, H, C] -> [B, H, *, C]
        return torch.nested.nested_tensor_from_jagged(x[0], offsets).transpose(1, 2)

    out = F.scaled_dot_product_attention(jag(q), jag(k), jag(v), scale=scale)
    return out.transpose(1, 2).values().unsqueeze(0)  # [1, T, H, C]


def _looped_sdpa(q, k, v, q_seqlen, kv_seqlen, scale=None):
    """Fallback for cross-attention blocks, where q and kv lengths differ."""
    outs, q_at, kv_at = [], 0, 0
    for len_q, len_kv in zip(q_seqlen, kv_seqlen):
        len_q, len_kv = int(len_q), int(len_kv)
        outs.append(
            _sdpa(
                q[:, q_at:q_at + len_q],
                k[:, kv_at:kv_at + len_kv],
                v[:, kv_at:kv_at + len_kv],
                scale,
            )
        )
        q_at += len_q
        kv_at += len_kv
    return torch.cat(outs, dim=1)


def _same_lengths(a, b) -> bool:
    if a is b:
        return True
    if isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor):
        return a.shape == b.shape and bool(torch.equal(a, b))
    if isinstance(a, torch.Tensor) or isinstance(b, torch.Tensor):
        return False
    return list(a) == list(b)


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
        q_seqlen, kv_seqlen = attn_bias.q_seqlen, attn_bias.kv_seqlen
        if len(q_seqlen) == 1:
            return _sdpa(q, k, v, scale)
        if _same_lengths(q_seqlen, kv_seqlen):
            return _jagged_sdpa(q, k, v, q_seqlen, scale)
        return _looped_sdpa(q, k, v, q_seqlen, kv_seqlen, scale)
    raise NotImplementedError(f"unsupported attn_bias type: {type(attn_bias)}")
