from __future__ import annotations

import gzip
from dataclasses import dataclass
from typing import Literal

StoredAs = Literal["raw", "gzip"]


@dataclass(frozen=True)
class CompressResult:
    stored_as: StoredAs
    payload: bytes  # raw bytes (if stored_as="raw") or gzip bytes (if stored_as="gzip")


def compress_conditional(raw: bytes, *, level: int = 6, min_gain_ratio: float = 0.02) -> CompressResult:
    """Compress raw bytes with gzip, but only keep compressed form if it saves space.

    Args:
        raw: original bytes
        level: gzip compression level (1..9)
        min_gain_ratio: minimum relative gain required to keep compression.
            Example: 0.02 means "must be at least 2% smaller".

    Returns:
        CompressResult(stored_as="gzip", payload=<compressed>) OR
        CompressResult(stored_as="raw",  payload=<raw>)
    """
    if not raw:
        # empty chunk: store as raw
        return CompressResult(stored_as="raw", payload=raw)

    comp = gzip.compress(raw, compresslevel=level)

    # Keep compressed only if smaller by at least min_gain_ratio
    # i.e., comp_len <= raw_len * (1 - min_gain_ratio)
    if len(comp) <= int(len(raw) * (1.0 - min_gain_ratio)):
        return CompressResult(stored_as="gzip", payload=comp)

    return CompressResult(stored_as="raw", payload=raw)


def decompress(payload: bytes, stored_as: StoredAs) -> bytes:
    """Decode stored payload back to raw bytes."""
    if stored_as == "raw":
        return payload
    if stored_as == "gzip":
        return gzip.decompress(payload)
    raise ValueError(f"stored_as inválido: {stored_as!r}")
