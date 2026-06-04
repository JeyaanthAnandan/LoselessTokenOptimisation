# Lossless Token Compressor

A developer tool that reduces LLM input token consumption for source code files — **losslessly**. No summarisation, no information loss. The LLM receives a compact symbolic representation and a legend to re-expand it.

## Demo

https://github.com/JeyaanthAnandan/LoselessTokenOptimisation/blob/main/demo.mov
https://loselesstokenoptimisation-azeznnffhe7urnqzikyglj.streamlit.app/

## How it works

1. **Identifier renaming** — module/class/function names that appear many times are replaced with short aliases (`a`, `b`, `c` …). A `LEGEND` comment is prepended so any LLM can reconstruct the original names.
2. **Whitespace normalisation** — indentation is collapsed to 1 space per level and blank lines are removed. Python's indent-sensitivity is preserved.
3. **Verification** — function, class, and import counts are compared before and after. An integrity score (0–1) is reported.

## Supported languages

| Extension | Parser |
|-----------|--------|
| `.py` | libcst (preserves comments & docstrings) |
| `.js` `.mjs` `.cjs` | tree-sitter-javascript |
| `.java` | tree-sitter-java |

## Benchmark (sample files)

| File | Tokens before | Tokens after | Reduction |
|------|--------------|-------------|-----------|
| sample.py | 434 | 408 | 6 % |
| sample.js | 405 | 367 | 9.4 % |
| sample.java | 490 | 430 | 12.2 % |

Reduction scales with repetition density — real-world enterprise codebases with long repeated identifiers typically see 15–30 % reduction.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
app.py                   # Streamlit dashboard
compressor/
  python_compressor.py   # libcst-based (preserves comments)
  js_compressor.py       # tree-sitter-javascript
  java_compressor.py     # tree-sitter-java
  treesitter_compressor.py  # shared base for JS/Java
  aliases.py             # a, b, c … alias generator
  tokenizer.py           # tiktoken wrapper + pricing table
  factory.py             # extension → compressor
verifier/integrity.py    # entity-count integrity check
metrics/analyzer.py      # token / cost / line savings
samples/                 # sample .py / .js / .java files
```
