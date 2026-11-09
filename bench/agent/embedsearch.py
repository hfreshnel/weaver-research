"""Embedding retrieval for the docs_embed lever: the user's request (as typed) is the query,
ranked against docsearch chunks by an embedding model (EmbeddingGemma 2, see bench/retrieval).
Run once per bench run, before the agent's server starts: a CPU llama-server encodes the
requests (the corpus vectors are cached in bench/retrieval/outputs/), then it stops.
"""
import operator
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench" / "retrieval"))
sys.path.insert(0, str(ROOT / "bench" / "lib"))
import docsearch  # noqa: E402
import eval_retrieval as er  # noqa: E402
from llama import LlamaServer  # noqa: E402

CACHE = ROOT / "bench" / "retrieval" / "outputs"
# CPU build: no VRAM taken from the agent's models (the CUDA build reserves some even at -ngl 0).
CPU_BIN = ROOT / "runtime" / "llamacpp" / "bin" / "cpu-b11887" / "llama-server"


def format_hits(docs, ids, budget=2500):
    """Same text layout as docsearch.search: '[title]' then at most 1000 chars per chunk."""
    out, used = [], 0
    for i in ids:
        title, _, text = docs[i]
        part = f"[{title}]\n{text.strip()[:1000]}"
        if used + len(part) > budget:
            break
        out.append(part)
        used += len(part)
    return "\n\n".join(out)


def retrieve(model, prompts, sources, log_path, k=3, budget=2500, server_bin=CPU_BIN):
    """{key: (docs text, [titles], latency s)} for prompts {key: request}. The latency is the
    query's share of the encoding plus its ranking (the corpus is encoded once, offline)."""
    docsearch._index(sources)
    docs = [(t, cmd, text) for t, cmd, text, _ in docsearch._INDEX[tuple(sorted(sources))][0]]
    extra = ["--embeddings", "--pooling", "mean", "-ub", "2048", "-b", "2048", "-np", "1"]
    with LlamaServer(str(server_bin), model, log_path, ngl=0, ctx=8192, extra=extra) as srv:
        vecs, _ = er.corpus_vectors(srv.base_url, docs, model, CACHE, 32)
        keys = list(prompts)
        t0 = time.perf_counter()
        qv = er.embed(srv.base_url, [f"task: search result | query: {prompts[c]}" for c in keys], 32)
        enc = (time.perf_counter() - t0) / max(1, len(keys))
    out = {}
    for c, q in zip(keys, qv):
        t0 = time.perf_counter()
        sims = [sum(map(operator.mul, q, v)) for v in vecs]
        ids = sorted(range(len(docs)), key=lambda i: -sims[i])[:k]
        out[c] = (format_hits(docs, ids, budget), [docs[i][0] for i in ids], round(enc + time.perf_counter() - t0, 2))
    return out
