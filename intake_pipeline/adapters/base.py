"""Contract for plugging a new public source into the intake pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class CollectedRecord:
    """One logical document from a public source."""

    record_id: str
    source_url: str
    title: str | None = None
    raw_text: str | None = None
    raw_bytes: bytes | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CollectorAdapter(Protocol):
    """Implement for each intake source (RSS, directory, API, etc.)."""

    source_key: str

    def collect(self) -> list[CollectedRecord]:
        """Fetch zero or more records from the public source."""
        ...
