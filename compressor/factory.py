"""Compressor selection by file extension."""
from __future__ import annotations

from .base import BaseCompressor


_REGISTRY: dict[str, str] = {
    "py": "compressor.python_compressor:PythonCompressor",
    "js": "compressor.js_compressor:JavaScriptCompressor",
    "mjs": "compressor.js_compressor:JavaScriptCompressor",
    "cjs": "compressor.js_compressor:JavaScriptCompressor",
    "java": "compressor.java_compressor:JavaCompressor",
}


def supported_extensions() -> list[str]:
    return sorted(_REGISTRY.keys())


def _load(spec: str) -> type[BaseCompressor]:
    mod_name, cls_name = spec.split(":")
    mod = __import__(mod_name, fromlist=[cls_name])
    return getattr(mod, cls_name)


def get_compressor(extension: str) -> BaseCompressor:
    ext = extension.lower().lstrip(".")
    if ext not in _REGISTRY:
        raise ValueError(
            f"Unsupported extension: .{ext}. Supported: {supported_extensions()}"
        )
    return _load(_REGISTRY[ext])()
