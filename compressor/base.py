from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CompressionResult:
    original: str
    compressed: str
    language: str
    legend: Dict[str, str] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)


class BaseCompressor:
    """Subclasses produce a CompressionResult from raw source text."""

    language: str = "unknown"

    def compress(self, source: str) -> CompressionResult:
        raise NotImplementedError
