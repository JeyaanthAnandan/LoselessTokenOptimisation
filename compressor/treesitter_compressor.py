"""Generic tree-sitter–driven compressor.

Subclasses provide:
  - the tree-sitter Language object
  - the set of "definition parent" node types whose `name` child should be
    treated as a renameable definition (e.g. `function_declaration` in JS).
  - the set of "skip parent" contexts whose identifier child must not be
    renamed (e.g. `import_statement` in JS, where renaming an imported name
    would break the import).
  - the set of reserved language keywords.

Renaming is done by byte-offset substitution on the source text so comments
and whitespace are preserved exactly outside the renamed spans.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Set

from tree_sitter import Language, Parser

from .aliases import alias_stream
from .base import BaseCompressor, CompressionResult


def _parser_for(language: Language) -> Parser:
    # The tree-sitter Python binding API changed across versions. 0.22+ takes
    # the Language in the Parser constructor; older versions used a setter.
    try:
        return Parser(language)
    except TypeError:
        p = Parser()
        try:
            p.language = language  # type: ignore[attr-defined]
        except AttributeError:
            p.set_language(language)  # type: ignore[attr-defined]
        return p


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


class TreeSitterCompressor(BaseCompressor):
    #: tree-sitter Language for this grammar
    ts_language: Language = None  # type: ignore[assignment]
    #: node.type values whose `name` child should be treated as a definition
    definition_parent_types: Set[str] = set()
    #: node.type values whose identifier descendants must NOT be renamed
    skip_subtree_types: Set[str] = set()
    #: reserved words & common globals we must never use as aliases
    reserved: Set[str] = set()
    #: line-comment prefix used to embed the legend (e.g. "//", "#")
    legend_comment_prefix: str = "//"
    #: identifier node type produced by this grammar
    identifier_node_type: str = "identifier"
    #: indent-unit guess for whitespace normalization
    base_indent: int = 4

    def _collect_definitions(self, root) -> Set[str]:
        defs: Set[str] = set()
        for node in _walk(root):
            if node.type in self.definition_parent_types:
                name_child = node.child_by_field_name("name")
                if name_child is not None and name_child.type == self.identifier_node_type:
                    defs.add(name_child.text.decode("utf-8"))
        return defs

    def _identifiers_in_skip_subtrees(self, root) -> Set[int]:
        """Byte offsets (start_byte) of identifiers whose ancestor is a skip
        subtree (e.g. import statements). We never rename those positions."""
        skip_ids: Set[int] = set()
        for node in _walk(root):
            if node.type in self.skip_subtree_types:
                for n in _walk(node):
                    if n.type == self.identifier_node_type:
                        skip_ids.add(n.start_byte)
        return skip_ids

    def _count_usages(self, root) -> Counter:
        c: Counter = Counter()
        for node in _walk(root):
            if node.type == self.identifier_node_type:
                c[node.text.decode("utf-8")] += 1
        return c

    def _build_rename_map(
        self, eligible: Set[str], usages: Counter
    ) -> dict:
        candidates = []
        for name in eligible:
            if name in self.reserved:
                continue
            if len(name) < 4:
                continue
            count = usages.get(name, 0)
            if count < 2:
                continue
            overhead = len(name) + 4
            savings = count * (len(name) - 1)
            if savings <= overhead:
                continue
            candidates.append((name, count * len(name)))
        candidates.sort(key=lambda t: -t[1])
        forbidden = self.reserved | set(usages.keys())
        gen = alias_stream(forbidden)
        return {name: next(gen) for name, _ in candidates}

    def _apply_renames(
        self, source: str, root, rename: dict, skip_positions: Set[int]
    ) -> str:
        src_bytes = source.encode("utf-8")
        edits = []  # (start_byte, end_byte, replacement_bytes)
        for node in _walk(root):
            if node.type != self.identifier_node_type:
                continue
            if node.start_byte in skip_positions:
                continue
            text = node.text.decode("utf-8")
            new = rename.get(text)
            if new is None:
                continue
            edits.append((node.start_byte, node.end_byte, new.encode("utf-8")))
        # Apply from the end so earlier offsets stay valid.
        edits.sort(key=lambda e: -e[0])
        out = bytearray(src_bytes)
        for s, e, rep in edits:
            out[s:e] = rep
        return out.decode("utf-8")

    def _normalize_whitespace(self, code: str) -> str:
        out = []
        for ln in code.split("\n"):
            stripped = ln.lstrip(" \t")
            if not stripped:
                continue
            leading = ln[: len(ln) - len(stripped)].expandtabs(self.base_indent)
            level = len(leading) // self.base_indent
            out.append(" " * level + stripped.rstrip())
        return "\n".join(out)

    def compress(self, source: str) -> CompressionResult:
        parser = _parser_for(self.ts_language)
        tree = parser.parse(source.encode("utf-8"))
        root = tree.root_node

        eligible = self._collect_definitions(root)
        usages = self._count_usages(root)
        rename = self._build_rename_map(eligible, usages)
        skip_positions = self._identifiers_in_skip_subtrees(root)

        rewritten = self._apply_renames(source, root, rename, skip_positions)
        compressed = self._normalize_whitespace(rewritten)

        if rename:
            legend = f"{self.legend_comment_prefix} LEGEND: " + " ".join(
                f"{v}={k}" for k, v in rename.items()
            )
            compressed = legend + "\n" + compressed

        return CompressionResult(
            original=source,
            compressed=compressed,
            language=self.language,
            legend=rename,
            notes={"strategy": "definition-scope identifier rename + 1-space indent"},
        )
