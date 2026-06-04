"""Token counting via tiktoken.

We use OpenAI's o200k_base as a proxy tokenizer. Modern frontier-model
tokenizers (GPT-4o, Claude, Gemini) produce similar counts for code, so this
is a defensible single number to optimize against. The compression engine is
tokenizer-agnostic — only this counter changes if a different model is wired in.
"""
from __future__ import annotations

import tiktoken

_ENCODER_CACHE: dict[str, tiktoken.Encoding] = {}

# Approximate USD per input token for several frontier models. Used only for
# the "estimated cost savings" headline number in the dashboard — these prices
# change over time and the user should treat them as ballpark.
PRICE_PER_TOKEN_USD = {
    "gpt-4o": 2.50 / 1_000_000,
    "claude-opus": 15.00 / 1_000_000,
    "claude-sonnet": 3.00 / 1_000_000,
    "gemini-pro": 1.25 / 1_000_000,
}


def get_encoder(name: str = "o200k_base") -> tiktoken.Encoding:
    if name not in _ENCODER_CACHE:
        try:
            _ENCODER_CACHE[name] = tiktoken.get_encoding(name)
        except (ValueError, KeyError):
            _ENCODER_CACHE[name] = tiktoken.get_encoding("cl100k_base")
    return _ENCODER_CACHE[name]


def count_tokens(text: str, encoding: str = "o200k_base") -> int:
    return len(get_encoder(encoding).encode(text))
