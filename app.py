"""Streamlit dashboard for the lossless token compressor."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import streamlit as st

from compressor import get_compressor, supported_extensions
from compressor.tokenizer import PRICE_PER_TOKEN_USD
from metrics import analyze


st.set_page_config(
    page_title="Lossless Token Compressor",
    page_icon="🧬",
    layout="wide",
)

st.title("Lossless Token Compressor")
st.caption(
    "Identifier renaming + whitespace normalization for LLM context. "
    "Supported: " + ", ".join(f".{e}" for e in supported_extensions())
)

with st.sidebar:
    st.header("Settings")
    cost_model = st.selectbox(
        "Cost model for savings estimate",
        options=list(PRICE_PER_TOKEN_USD.keys()),
        index=1,
    )
    context_window = st.number_input(
        "LLM context window (tokens)",
        min_value=1000,
        max_value=2_000_000,
        value=200_000,
        step=10_000,
    )
    use_samples = st.checkbox("Use bundled samples instead of uploading", value=False)


def _load_samples() -> list[tuple[str, bytes]]:
    sample_dir = Path(__file__).parent / "samples"
    files = []
    if sample_dir.exists():
        for p in sorted(sample_dir.iterdir()):
            if p.suffix.lstrip(".") in supported_extensions():
                files.append((p.name, p.read_bytes()))
    return files


if use_samples:
    inputs = _load_samples()
    st.info(f"Loaded {len(inputs)} bundled sample file(s) from `samples/`.")
else:
    uploaded = st.file_uploader(
        "Drop source files here",
        accept_multiple_files=True,
        type=supported_extensions(),
    )
    inputs = [(f.name, f.read()) for f in (uploaded or [])]


if not inputs:
    st.stop()


# Run compression for each file.
results = []
for filename, raw in inputs:
    ext = filename.rsplit(".", 1)[-1]
    try:
        compressor = get_compressor(ext)
        source = raw.decode("utf-8", errors="replace")
        compression = compressor.compress(source)
        metrics = analyze(source, compression.compressed, compression.language)
        results.append((filename, source, compression, metrics, None))
    except Exception as e:
        results.append((filename, raw.decode("utf-8", errors="replace"), None, None, str(e)))


# ---------- Aggregate summary ----------
ok_results = [r for r in results if r[2] is not None]

total_orig_tokens = sum(r[3].original["tokens"] for r in ok_results)
total_comp_tokens = sum(r[3].compressed["tokens"] for r in ok_results)
total_saved = total_orig_tokens - total_comp_tokens
pct_total = (total_saved / total_orig_tokens * 100.0) if total_orig_tokens else 0.0
cost_saved = total_saved * PRICE_PER_TOKEN_USD[cost_model]

st.subheader("Aggregate savings")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Original tokens", f"{total_orig_tokens:,}")
c2.metric("Compressed tokens", f"{total_comp_tokens:,}", delta=f"-{pct_total:.1f}%")
c3.metric("Tokens saved", f"{total_saved:,}")
c4.metric(f"Cost saved ({cost_model})", f"${cost_saved:.6f}")

ctx_before = total_orig_tokens / context_window * 100
ctx_after = total_comp_tokens / context_window * 100
st.write(
    f"Context window utilization: **{ctx_before:.2f}%** → **{ctx_after:.2f}%** "
    f"of {context_window:,}-token budget"
)
st.progress(min(1.0, ctx_after / 100.0))

# ---------- Per-file detail ----------
st.subheader("Per-file results")
for filename, source, compression, metrics, err in results:
    with st.expander(f"{filename}", expanded=len(results) == 1):
        if err is not None:
            st.error(f"Compression failed: {err}")
            continue

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Tokens", f"{metrics.original['tokens']:,}",
                  delta=f"-{metrics.savings['tokens_saved']:,}")
        m2.metric("Compressed tokens", f"{metrics.compressed['tokens']:,}")
        m3.metric("Reduction", f"{metrics.savings['pct_reduction']:.1f}%")
        m4.metric("Lines",
                  f"{metrics.original['lines']:,} → {metrics.compressed['lines']:,}")
        m5.metric("Bytes",
                  f"{metrics.original['bytes']:,} → {metrics.compressed['bytes']:,}")

        # Verification badge
        if metrics.savings["integrity_ok"]:
            st.success(
                f"Integrity verified — score {metrics.savings['integrity_score']:.3f}. "
                f"Functions: {metrics.original['functions']} ↔ {metrics.compressed['functions']}, "
                f"Classes: {metrics.original['classes']} ↔ {metrics.compressed['classes']}, "
                f"Imports: {metrics.original['imports']} ↔ {metrics.compressed['imports']}."
            )
        else:
            err_text = metrics.savings["integrity_error"] or (
                f"Entity drift: {metrics.savings['mismatches']}"
            )
            st.error(f"Integrity check failed — {err_text}")

        st.caption(
            f"Renamed {len(compression.legend)} identifier(s). "
            f"Strategy: {compression.notes.get('strategy', '')}"
        )

        left, right = st.columns(2)
        with left:
            st.markdown("**Original**")
            st.code(source, language=compression.language)
        with right:
            st.markdown("**Compressed**")
            st.code(compression.compressed, language=compression.language)

        if compression.legend:
            with st.popover("View legend (alias → original)"):
                st.table(
                    [
                        {"alias": v, "original": k, "occurrences": "—"}
                        for k, v in compression.legend.items()
                    ]
                )

# ---------- Export ----------
if ok_results:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        bundle_parts = []
        for filename, _, compression, _, _ in ok_results:
            zf.writestr(f"compressed/{filename}", compression.compressed)
            bundle_parts.append(
                f"// ===== FILE: {filename} =====\n{compression.compressed}"
            )
        zf.writestr("bundle.txt", "\n\n".join(bundle_parts))
    st.download_button(
        "Download compressed bundle (.zip)",
        data=buf.getvalue(),
        file_name="compressed_bundle.zip",
        mime="application/zip",
    )
