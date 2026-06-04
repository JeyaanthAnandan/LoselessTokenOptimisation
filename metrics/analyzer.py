"""Before/after metrics for a single file."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from compressor.tokenizer import PRICE_PER_TOKEN_USD, count_tokens
from verifier.integrity import verify


@dataclass
class FileMetrics:
    original: Dict[str, float] = field(default_factory=dict)
    compressed: Dict[str, float] = field(default_factory=dict)
    savings: Dict[str, float] = field(default_factory=dict)


def _per_file_metrics(source: str, language: str) -> Dict[str, float]:
    tokens = count_tokens(source)
    lines = source.count("\n") + (0 if source.endswith("\n") else 1)
    return {
        "bytes": len(source.encode("utf-8")),
        "chars": len(source),
        "lines": lines,
        "tokens": tokens,
    }


def analyze(original: str, compressed: str, language: str) -> FileMetrics:
    orig = _per_file_metrics(original, language)
    comp = _per_file_metrics(compressed, language)
    report = verify(original, compressed, language)
    orig["functions"] = report.original_counts.get("functions", 0)
    orig["classes"] = report.original_counts.get("classes", 0)
    orig["imports"] = report.original_counts.get("imports", 0)
    comp["functions"] = report.compressed_counts.get("functions", 0)
    comp["classes"] = report.compressed_counts.get("classes", 0)
    comp["imports"] = report.compressed_counts.get("imports", 0)

    tok_saved = orig["tokens"] - comp["tokens"]
    pct = (tok_saved / orig["tokens"] * 100.0) if orig["tokens"] else 0.0

    savings = {
        "tokens_saved": tok_saved,
        "pct_reduction": pct,
        "ratio": (comp["tokens"] / orig["tokens"]) if orig["tokens"] else 1.0,
        "integrity_score": report.integrity_score,
        "integrity_ok": report.ok,
        "integrity_error": report.parse_error,
        "mismatches": report.mismatches,
    }
    # Cost savings across a few representative models.
    for model, price in PRICE_PER_TOKEN_USD.items():
        savings[f"cost_saved_{model}_usd"] = tok_saved * price
    return FileMetrics(original=orig, compressed=comp, savings=savings)
