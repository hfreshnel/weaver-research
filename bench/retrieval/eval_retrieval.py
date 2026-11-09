"""Retrieval-only eval: BM25 (bench/agent/docsearch.py) vs an embedding model vs hybrid (RRF).

Queries: the novice v4 user requests (French, as typed by the user), 66 cases.
Relevance (automatic, no hand labels), two criteria, both from the task's oracle script:
- strict: the chunk's command (man/tldr page, Arch Wiki page name) is one the oracle runs;
- mention: strict, or the chunk's text names an oracle command as a word (except names that
  are common words or too short: AMBIGUOUS).
One valid solution only, so the labels are conservative, but the same for every method.

Usage:
  python3 -I bench/retrieval/eval_retrieval.py --model models/embeddinggemma-2/embeddinggemma-2-Q8_0.gguf
Embeddings of the corpus are cached in bench/retrieval/outputs/ (gitignored).
"""
import argparse
import array
import hashlib
import json
import math
import operator
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench" / "agent"))
sys.path.insert(0, str(ROOT / "bench"))
import docsearch  # noqa: E402
from lib.llama import LlamaServer, http_json  # noqa: E402

SOURCES = ("archwiki", "man", "tldr")  # --sources overrides
TRIVIAL = {"ls", "cat", "echo", "head", "tail", "grep", "sort", "wc", "uniq", "cd", "true", "test"}
AMBIGUOUS = {"ps", "du", "lp", "kill", "cancel"}
EMBED_CHARS = 2400  # the model reads at most this much of a chunk (~800 tokens)


def oracle_commands():
    cmds = {}
    for fn in ("oracle_novice.json", "oracle_novice_v4_new.json"):
        for task, steps in json.loads((ROOT / "bench/agent/mock_scripts" / fn).read_text()).items():
            s = cmds.setdefault(task, set())
            for step in steps:
                for name, args in step.get("tool_calls", []):
                    if name != "run_shell":
                        continue
                    for part in re.split(r"\||&&|;", args["command"]):
                        words = [w for w in part.split() if "=" not in w or w.startswith("-")]
                        while words and words[0] in ("sudo", "env", "nohup"):
                            words = words[1:]
                        if words and words[0].split("/")[-1] not in TRIVIAL:
                            s.add(words[0].split("/")[-1].lower())
    return cmds


def queries():
    d = json.loads((ROOT / "bench/agent/cases_novice_v4.json").read_text())
    return [(c["id"], c["task"], c.get("split", "dev"), c["prompt"]) for c in d["cases"]]


def corpus():
    docsearch._index(SOURCES)  # same chunking as the bench
    return [(t, cmd, text) for t, cmd, text, _ in docsearch._INDEX[tuple(sorted(SOURCES))][0]]


def embed(url, texts, batch):
    out = []
    for i in range(0, len(texts), batch):
        r = http_json(f"{url}/v1/embeddings", {"input": texts[i:i + batch]})
        for item in sorted(r["data"], key=lambda x: x["index"]):
            v = item["embedding"]
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
    return out


def corpus_vectors(url, docs, model, cache_dir, batch):
    """One cache file per source (chunks of a source are contiguous, titled '<source> …')."""
    vecs, enc_s, start = [], 0.0, 0
    while start < len(docs):
        src = docs[start][0].split(" ", 1)[0]
        end = start
        while end < len(docs) and docs[end][0].split(" ", 1)[0] == src:
            end += 1
        part = docs[start:end]
        key = hashlib.sha256((Path(model).name + "\0" + "\0".join(t + "\0" + x[:EMBED_CHARS] for t, _, x in part)).encode()).hexdigest()[:16]
        path = cache_dir / f"{src}-{Path(model).stem}-{key}.f32"
        if path.is_file():
            a = array.array("f")
            a.frombytes(path.read_bytes())
            dim = len(a) // len(part)
            vecs += [a[i * dim:(i + 1) * dim] for i in range(len(part))]
        else:
            t0 = time.time()
            new = []
            for i in range(0, len(part), 512):
                texts = [f"title: {t} | text: {x[:EMBED_CHARS]}" for t, _, x in part[i:i + 512]]
                new += embed(url, texts, batch)
                print(f"  {src}: embedded {len(new)}/{len(part)} ({time.time() - t0:.0f} s)", file=sys.stderr, flush=True)
            path.write_bytes(array.array("f", [x for v in new for x in v]).tobytes())
            vecs += [array.array("f", v) for v in new]
            enc_s += time.time() - t0
        start = end
    return vecs, enc_s


def rrf(*rankings, k=60):
    score = {}
    for r in rankings:
        for pos, i in enumerate(r):
            score[i] = score.get(i, 0.0) + 1.0 / (k + pos + 1)
    return sorted(score, key=lambda i: -score[i])


def metrics(ranked, rel):
    first = next((p for p, i in enumerate(ranked[:10]) if i in rel), None)
    return {"hit@1": first == 0, "hit@3": first is not None and first < 3,
            "hit@10": first is not None, "mrr@10": 0.0 if first is None else 1.0 / (first + 1)}


def main():
    global SOURCES
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--server-bin", default=str(ROOT / "runtime/llamacpp/bin/cuda13.4-b11887/llama-server"))
    ap.add_argument("--ngl", type=int, default=99)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--depth", type=int, default=100, help="list depth fused by RRF")
    ap.add_argument("--sources", default=",".join(SOURCES), help="comma-separated docsearch sources")
    ap.add_argument("--out", default=str(ROOT / "bench/retrieval/outputs"))
    a = ap.parse_args()
    SOURCES = tuple(a.sources.split(","))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    cmds = oracle_commands()
    docs = corpus()
    idx_of = {}
    for i, (t, cmd, x) in enumerate(docs):
        idx_of.setdefault(cmd.lower(), set()).add(i)
    rel = {task: set().union(*(idx_of.get(c, set()) for c in cs)) if cs else set() for task, cs in cmds.items()}
    mention = {}
    for task, cs in cmds.items():
        pats = [re.compile(r"(?<![\w-])" + re.escape(c) + r"(?![\w-])") for c in cs if c not in AMBIGUOUS]
        mention[task] = rel[task] | {i for i, (_, _, x) in enumerate(docs) if any(p.search(x) for p in pats)}
    qs = [q for q in queries() if rel.get(q[1])]
    skipped = sorted({q[1] for q in queries()} - {q[1] for q in qs})
    print(f"corpus {len(docs)} chunks; {len(qs)} queries over {len({q[1] for q in qs})} tasks; "
          f"skipped (no oracle command in the corpus): {skipped}")
    for task in sorted({q[1] for q in qs}):
        print(f"  {task}: {sorted(c for c in cmds[task] if c in idx_of)}")

    extra = ["--embeddings", "--pooling", "mean", "-ub", "2048", "-b", "2048", "-np", "1"]
    with LlamaServer(a.server_bin, a.model, out / "server.log", ngl=a.ngl, ctx=8192, extra=extra) as srv:
        vecs, enc_s = corpus_vectors(srv.base_url, docs, a.model, out, a.batch)
        qv = embed(srv.base_url, [f"task: search result | query: {p}" for *_, p in qs], a.batch)
        mem = {"load_s": srv.load_s}
    mem.update(rss_peak_mib=srv.rss_peak_mib, gpu_peak_delta_mib=srv.gpu_peak_delta_mib)

    rows = {f"{m}/{c}": [] for c in ("strict", "mention") for m in ("bm25", "embed", "hybrid")}
    per_case = []
    t0 = time.time()
    for (cid, task, split, prompt), q in zip(qs, qv):
        bm = [i for i in _bm25_ids(prompt, docs)[:a.depth]]
        sims = [sum(map(operator.mul, q, v)) for v in vecs]
        em = sorted(range(len(docs)), key=lambda i: -sims[i])[:a.depth]
        hy = rrf(bm, em)
        res = {f"{m}/{c}": metrics(lst, r) for c, r in (("strict", rel[task]), ("mention", mention[task]))
               for m, lst in (("bm25", bm), ("embed", em), ("hybrid", hy))}
        for k, m in res.items():
            rows[k].append((split, m))
        per_case.append({"id": cid, "task": task, "split": split, **{k: m["mrr@10"] for k, m in res.items()},
                         "top3": {k: [docs[i][0] for i in lst[:3]] for k, lst in (("bm25", bm), ("embed", em), ("hybrid", hy))}})
    search_s = time.time() - t0

    print(f"\nencode corpus {enc_s:.0f} s (0 = cached); search {search_s:.0f} s for {len(qs)} queries; memory {mem}")
    print("| method | split | n | hit@1 | hit@3 | hit@10 | MRR@10 |\n|---|---|---|---|---|---|---|")
    for k, lst in rows.items():
        for split in ("all", "dev", "holdout"):
            ms = [m for s, m in lst if split == "all" or s == split]
            avg = {x: sum(m[x] for m in ms) / len(ms) for x in ("hit@1", "hit@3", "hit@10", "mrr@10")}
            print(f"| {k} | {split} | {len(ms)} | {avg['hit@1']:.2f} | {avg['hit@3']:.2f} | {avg['hit@10']:.2f} | {avg['mrr@10']:.3f} |")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (out / f"results-{Path(a.model).stem}-{stamp}.json").write_text(json.dumps(
        {"model": a.model, "sources": SOURCES, "memory": mem, "encode_s": enc_s, "search_s": search_s, "cases": per_case}, ensure_ascii=False, indent=1))


_POS = {}


def _bm25_ids(query, docs):
    if not _POS:  # rank() returns the index's own text objects: map them back by identity
        _POS.update({id(x): i for i, (_, _, x) in enumerate(docs)})
    return [_POS[id(x)] for *_, x in docsearch.rank(query, SOURCES)]


if __name__ == "__main__":
    main()
