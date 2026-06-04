"""JavaScript compressor (tree-sitter)."""
from __future__ import annotations

import tree_sitter_javascript as tsjs
from tree_sitter import Language

from .treesitter_compressor import TreeSitterCompressor

# https://github.com/tc39/proposal-reserved-words ish — enough to cover the
# globals/keywords our alias generator might collide with.
JS_RESERVED = {
    # keywords
    "break", "case", "catch", "class", "const", "continue", "debugger",
    "default", "delete", "do", "else", "export", "extends", "finally", "for",
    "function", "if", "import", "in", "instanceof", "new", "of", "return",
    "super", "switch", "this", "throw", "try", "typeof", "var", "void",
    "while", "with", "yield", "let", "static", "async", "await",
    # literals
    "true", "false", "null", "undefined", "NaN", "Infinity",
    # commonly-used globals
    "console", "window", "document", "globalThis", "process", "module",
    "exports", "require", "Math", "JSON", "Object", "Array", "String",
    "Number", "Boolean", "Promise", "Map", "Set", "Date", "Error",
    "Symbol", "RegExp", "Buffer", "setTimeout", "setInterval", "clearTimeout",
    "clearInterval", "fetch",
}


class JavaScriptCompressor(TreeSitterCompressor):
    language = "javascript"
    ts_language = Language(tsjs.language())
    definition_parent_types = {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "variable_declarator",
        # JS arrow & function expressions don't always have a `name` field,
        # but when assigned via variable_declarator we'll pick them up there.
    }
    skip_subtree_types = {
        "import_statement",
        "import_clause",
        "import_specifier",
        "export_statement",
    }
    reserved = JS_RESERVED
    legend_comment_prefix = "//"
    identifier_node_type = "identifier"
    base_indent = 2  # most JS uses 2-space indent
