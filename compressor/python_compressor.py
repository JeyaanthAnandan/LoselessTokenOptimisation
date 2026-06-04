"""Python source compressor.

Uses libcst (concrete syntax tree) so comments and docstrings are preserved
through the transform — Python's stdlib `ast` module strips them.

Rename policy
-------------
- Eligible: module-level functions, classes, and top-level variable bindings.
- All Name references to those identifiers are renamed everywhere they appear.
- Attribute names (`obj.attr`) are NEVER touched — they may belong to external
  APIs we can't safely rewrite.
- Method names defined inside classes are NOT eligible (they're attributes of
  the class instance and renaming them would desync from `self.method()` call
  sites, which look like attribute access).
- Identifiers in the dunder convention (`__name__`) are preserved.
- A heuristic skips identifiers where the legend overhead exceeds the savings.

A `# LEGEND: a=long_name b=other_name` comment is prepended so an LLM
consuming the output can mentally re-expand the aliases.
"""
from __future__ import annotations

import builtins
import keyword
import re
from collections import Counter
from typing import Dict, Set

import libcst as cst

from .aliases import alias_stream
from .base import BaseCompressor, CompressionResult

PY_KEYWORDS = set(keyword.kwlist) | set(keyword.softkwlist)
PY_BUILTINS = set(dir(builtins))
PROTECTED = PY_KEYWORDS | PY_BUILTINS | {
    "self", "cls", "__init__", "__main__", "__name__",
    "__file__", "__doc__", "__class__", "__dict__", "__all__",
    "__repr__", "__str__", "__eq__", "__hash__", "__iter__",
    "__next__", "__enter__", "__exit__", "__call__", "__len__",
}


class _ModuleLevelCollector(cst.CSTVisitor):
    """Find identifiers defined at module scope (eligible for rename)."""

    def __init__(self) -> None:
        self.names: Set[str] = set()
        self._depth = 0  # 0 == module scope

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if self._depth == 0:
            self.names.add(node.name.value)
        self._depth += 1
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        self._depth -= 1

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self._depth == 0:
            self.names.add(node.name.value)
        self._depth += 1
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self._depth -= 1

    def visit_Assign(self, node: cst.Assign) -> bool:
        if self._depth == 0:
            for tgt in node.targets:
                if isinstance(tgt.target, cst.Name):
                    self.names.add(tgt.target.value)
        return True

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        if self._depth == 0 and isinstance(node.target, cst.Name):
            self.names.add(node.target.value)
        return True


class _UsageCounter(cst.CSTVisitor):
    """Count every Name occurrence in the tree."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        # Names of imported symbols — we don't want to rename these even if
        # they happen to be referenced like module-level names, because
        # renaming the def at the import site is hairy and the savings are
        # small compared to risk.
        self.imported: Set[str] = set()

    def visit_Name(self, node: cst.Name) -> None:
        self.counts[node.value] += 1

    def visit_ImportAlias(self, node: cst.ImportAlias) -> None:
        # `import foo as bar` — bar is the bound name. `import foo` — foo is.
        if node.asname is not None:
            if isinstance(node.asname.name, cst.Name):
                self.imported.add(node.asname.name.value)
        else:
            # node.name can be Name or Attribute
            n = node.name
            while isinstance(n, cst.Attribute):
                n = n.value
            if isinstance(n, cst.Name):
                self.imported.add(n.value)


class _Renamer(cst.CSTTransformer):
    """Rewrite Name nodes whose value is in the rename map. Attribute names
    are deliberately untouched (they're cst.Name nodes but appear as the
    `.attr` field of Attribute, which we override to skip)."""

    def __init__(self, rename: Dict[str, str]) -> None:
        super().__init__()
        self.rename = rename

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        new = self.rename.get(updated_node.value)
        if new is not None:
            return updated_node.with_changes(value=new)
        return updated_node

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        # Restore the original attribute name even if leave_Name rewrote it.
        # libcst visits children depth-first, so updated_node.attr may already
        # have been rewritten by leave_Name. We undo only the attr side.
        if updated_node.attr.value != original_node.attr.value:
            return updated_node.with_changes(attr=original_node.attr)
        return updated_node


def _build_rename_map(
    eligible: Set[str], usages: Counter, imported: Set[str]
) -> Dict[str, str]:
    """Decide which eligible names are worth renaming.

    Heuristic: rename if `usages * (len - 1) > legend_overhead`. The legend
    entry costs roughly `len(name) + 4` chars (e.g., "a=name "), and each
    rename site saves roughly `len(name) - len(alias)` characters which
    translates to ~`(len(name) - 1) * usages` tokens of savings (BPE doesn't
    work in chars but this is a reasonable proxy).
    """
    candidates = []
    for name in eligible:
        if name in PROTECTED or name in imported:
            continue
        if name.startswith("__") and name.endswith("__"):
            continue
        if len(name) < 4:  # too short — alias won't help
            continue
        count = usages.get(name, 0)
        if count < 2:
            continue
        overhead = len(name) + 4
        savings = count * (len(name) - 1)
        if savings <= overhead:
            continue
        candidates.append((name, count * len(name)))

    candidates.sort(key=lambda t: -t[1])  # biggest wins first get shortest aliases

    forbidden = PROTECTED | set(usages.keys()) | imported
    gen = alias_stream(forbidden)
    rename: Dict[str, str] = {}
    for name, _ in candidates:
        alias = next(gen)
        rename[name] = alias
    return rename


_INDENT_RE = re.compile(r"^(\s*)")


def _detect_indent_unit(code: str) -> int:
    for ln in code.split("\n"):
        m = _INDENT_RE.match(ln)
        if m and m.group(1) and ln.strip():
            return len(m.group(1).expandtabs(4))
    return 4


def _normalize_whitespace(code: str) -> str:
    """Re-indent to 1 space per level and drop blank lines.

    Python is indent-sensitive so we can't just strip whitespace — we need to
    preserve relative depth. We detect the source's indent unit and divide.
    """
    unit = _detect_indent_unit(code) or 4
    out = []
    for ln in code.split("\n"):
        stripped = ln.lstrip(" \t")
        if not stripped:
            continue
        leading = ln[: len(ln) - len(stripped)].expandtabs(unit)
        level = len(leading) // unit
        out.append(" " * level + stripped.rstrip())
    return "\n".join(out)


class PythonCompressor(BaseCompressor):
    language = "python"

    def compress(self, source: str) -> CompressionResult:
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError as e:
            raise ValueError(f"Python parse error: {e}") from e

        collector = _ModuleLevelCollector()
        module.visit(collector)
        usages = _UsageCounter()
        module.visit(usages)

        rename = _build_rename_map(collector.names, usages.counts, usages.imported)
        renamed = module.visit(_Renamer(rename))
        compressed = _normalize_whitespace(renamed.code)

        if rename:
            legend = "# LEGEND: " + " ".join(f"{v}={k}" for k, v in rename.items())
            compressed = legend + "\n" + compressed

        return CompressionResult(
            original=source,
            compressed=compressed,
            language=self.language,
            legend=rename,
            notes={"strategy": "module-scope identifier rename + 1-space indent"},
        )
