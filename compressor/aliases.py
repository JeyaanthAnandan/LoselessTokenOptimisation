"""Short identifier alias generator.

Yields a, b, c, ..., z, aa, ab, ..., zz, aaa, ...
Skips entries that would collide with a caller-supplied "forbidden" set
(language keywords, builtins, names already in the source).
"""
from __future__ import annotations

import string
from typing import Iterable


def alias_stream(forbidden: Iterable[str]):
    blocked = set(forbidden)
    letters = string.ascii_lowercase
    # 1-char
    for c in letters:
        if c not in blocked:
            yield c
    # 2-char
    for a in letters:
        for b in letters:
            cand = a + b
            if cand not in blocked:
                yield cand
    # 3-char (very large codebases)
    for a in letters:
        for b in letters:
            for c in letters:
                cand = a + b + c
                if cand not in blocked:
                    yield cand
