"""Database helpers shared by collectors."""

from __future__ import annotations

from collections.abc import Iterator

# PostgREST `.in_()` URL length limits on large ID lists.
SUPABASE_IN_BATCH_SIZE = 100


def batched_ids(ids: list[str], batch_size: int = SUPABASE_IN_BATCH_SIZE) -> Iterator[list[str]]:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    for i in range(0, len(ids), batch_size):
        yield ids[i : i + batch_size]
