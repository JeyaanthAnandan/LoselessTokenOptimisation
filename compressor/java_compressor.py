"""Java compressor (tree-sitter)."""
from __future__ import annotations

import tree_sitter_java as tsjava
from tree_sitter import Language

from .treesitter_compressor import TreeSitterCompressor

JAVA_RESERVED = {
    # keywords
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "yield", "record",
    "sealed", "permits", "var", "non-sealed",
    # literals
    "true", "false", "null",
    # ubiquitous types/identifiers we don't want to shadow
    "String", "Object", "Integer", "Long", "Double", "Float", "Boolean",
    "Character", "Byte", "Short", "Number", "Math", "System", "Exception",
    "RuntimeException", "Throwable", "List", "Map", "Set", "Collection",
    "ArrayList", "HashMap", "HashSet", "Optional", "Stream", "Arrays",
    "Collections", "main", "args", "out", "err", "in",
}


class JavaCompressor(TreeSitterCompressor):
    language = "java"
    ts_language = Language(tsjava.language())
    definition_parent_types = {
        "method_declaration",
        "class_declaration",
        "interface_declaration",
        "record_declaration",
        "enum_declaration",
        "variable_declarator",
        "formal_parameter",
        "constructor_declaration",
    }
    skip_subtree_types = {
        "import_declaration",
        "package_declaration",
    }
    reserved = JAVA_RESERVED
    legend_comment_prefix = "//"
    identifier_node_type = "identifier"
    base_indent = 4
