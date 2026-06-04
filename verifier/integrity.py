"""Integrity verification.

We compare structural entity counts between the original and the compressed
source. Identifier renaming + whitespace normalization should leave the AST
shape unchanged: same number of functions, classes, imports. If those counts
drift, the compression dropped or duplicated something and we surface that.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict

import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
from tree_sitter import Language

from compressor.treesitter_compressor import _parser_for, _walk

JS_LANG = Language(tsjs.language())
JAVA_LANG = Language(tsjava.language())


@dataclass
class VerificationReport:
    language: str
    original_counts: Dict[str, int] = field(default_factory=dict)
    compressed_counts: Dict[str, int] = field(default_factory=dict)
    mismatches: Dict[str, int] = field(default_factory=dict)
    integrity_score: float = 1.0
    parse_ok: bool = True
    parse_error: str = ""

    @property
    def ok(self) -> bool:
        return self.parse_ok and not self.mismatches


def _python_counts(source: str) -> Dict[str, int]:
    tree = ast.parse(source)
    counts = {"functions": 0, "classes": 0, "imports": 0}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            counts["functions"] += 1
        elif isinstance(node, ast.ClassDef):
            counts["classes"] += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            counts["imports"] += 1
    return counts


def _ts_counts(source: str, language: Language, types: Dict[str, set]) -> Dict[str, int]:
    parser = _parser_for(language)
    tree = parser.parse(source.encode("utf-8"))
    counts = {k: 0 for k in types}
    for node in _walk(tree.root_node):
        for category, type_set in types.items():
            if node.type in type_set:
                counts[category] += 1
    return counts


_JS_TYPES = {
    "functions": {"function_declaration", "method_definition", "arrow_function", "function_expression"},
    "classes": {"class_declaration"},
    "imports": {"import_statement"},
}

_JAVA_TYPES = {
    "functions": {"method_declaration", "constructor_declaration"},
    "classes": {"class_declaration", "interface_declaration", "record_declaration", "enum_declaration"},
    "imports": {"import_declaration"},
}


def _counts_for(language: str, source: str) -> Dict[str, int]:
    if language == "python":
        return _python_counts(source)
    if language == "javascript":
        return _ts_counts(source, JS_LANG, _JS_TYPES)
    if language == "java":
        return _ts_counts(source, JAVA_LANG, _JAVA_TYPES)
    raise ValueError(f"Unknown language: {language}")


def verify(original: str, compressed: str, language: str) -> VerificationReport:
    """Confirm the compressed source has the same structural entity counts
    as the original. Any drift is reported as a mismatch and pulls down the
    integrity score."""
    report = VerificationReport(language=language)
    try:
        report.original_counts = _counts_for(language, original)
    except Exception as e:
        report.parse_ok = False
        report.parse_error = f"original parse failed: {e}"
        report.integrity_score = 0.0
        return report

    try:
        report.compressed_counts = _counts_for(language, compressed)
    except Exception as e:
        report.parse_ok = False
        report.parse_error = f"compressed parse failed: {e}"
        report.integrity_score = 0.0
        return report

    mismatches = {}
    for key, orig in report.original_counts.items():
        new = report.compressed_counts.get(key, 0)
        if orig != new:
            mismatches[key] = new - orig
    report.mismatches = mismatches

    total_entities = sum(report.original_counts.values()) or 1
    total_drift = sum(abs(d) for d in mismatches.values())
    report.integrity_score = max(0.0, 1.0 - total_drift / total_entities)
    return report
