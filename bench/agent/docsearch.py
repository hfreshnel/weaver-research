"""Offline documentation search (knowledge lever): BM25 over man pages, tldr pages, the
Arch Wiki and the Ubuntu desktop help.

Corpora are fetched by knowledge/{man,tldr,archwiki}/fetch.sh. A tldr page is one chunk; a man
page is split into paragraph groups; a wiki page into sections. Stdlib only, no embeddings: keywords first, measure later.
"""
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "knowledge"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TOKEN = re.compile(r"[a-z0-9]+")
CHUNK_CHARS = 1200
K1, B = 1.2, 0.75
_INDEX = {}


def fold(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def tokens(s):
    return [t for t in TOKEN.findall(fold(s)) if len(t) >= 2]


def man_text(cmd):
    p = ROOT / "man" / "data" / f"{cmd}.txt"
    return ANSI.sub("", p.read_text(errors="replace")) if p.is_file() else None


def tldr_text(cmd):
    for lang in ("en", "fr"):
        p = ROOT / "tldr" / "data" / lang / f"{cmd}.md"
        if p.is_file():
            return p.read_text(errors="replace")
    return None


def _chunks(source):
    if source == "tldr":
        for lang in ("en", "fr"):
            for p in sorted((ROOT / "tldr" / "data" / lang).glob("*.md")):
                yield f"tldr {p.stem}" + (" (fr)" if lang == "fr" else ""), p.stem, p.read_text(errors="replace")
    elif source == "archwiki":
        yield from _wiki_chunks()
    elif source == "ubuntuhelp":
        yield from _wiki_chunks("ubuntuhelp", page_cmd=lambda p: p.stem)
    elif source == "man":
        for p in sorted((ROOT / "man" / "data").glob("*.txt")):
            text = ANSI.sub("", p.read_text(errors="replace"))
            buf = ""
            for para in re.split(r"\n\s*\n", text):
                if buf and len(buf) + len(para) > CHUNK_CHARS:
                    yield f"man {p.stem}", p.stem, buf
                    buf = ""
                buf += para.strip("\n") + "\n\n"
            if buf.strip():
                yield f"man {p.stem}", p.stem, buf


def _wiki_chunks(corpus="archwiki", page_cmd=lambda p: p.stem.split("__")[0].lower()):
    """Arch Wiki (or the Ubuntu help, same text layout): one chunk per section ("## "),
    prefixed with the page title; long sections are split by paragraphs. page_cmd gives the
    page's command name (Arch Wiki: its first path segment)."""
    for lang in ("en", "fr"):
        for p in sorted((ROOT / corpus / "data" / lang).glob("*.txt")):
            text = p.read_text(errors="replace")
            title = text.split("\n", 1)[0].lstrip("# ").strip()
            cmd = page_cmd(p)
            label = f"{corpus} {title}" + (" (fr)" if lang == "fr" else "")
            for sec in re.split(r"\n(?=## )", text):
                head = sec.split("\n", 1)[0].lstrip("# ").strip() if sec.startswith("## ") else ""
                name = f"{label} > {head}" if head else label
                buf = ""
                for para in re.split(r"\n\s*\n", sec):
                    if buf and len(buf) + len(para) > CHUNK_CHARS:
                        yield name, cmd, f"{title}\n{buf}"
                        buf = ""
                    buf += para.strip("\n") + "\n\n"
                if len(buf.strip()) > 80:
                    yield name, cmd, f"{title}\n{buf}"


def _index(sources):
    key = tuple(sorted(sources))
    if key not in _INDEX:
        docs = [(title, cmd, text, Counter(tokens(text))) for s in key for title, cmd, text in _chunks(s)]
        df = Counter(t for *_, tf in docs for t in tf)
        avg = sum(sum(tf.values()) for *_, tf in docs) / max(1, len(docs))
        _INDEX[key] = (docs, df, avg)
    return _INDEX[key]


def rank(query, sources):
    """BM25 ranking: [(score, title, cmd, text)], best first (only chunks with score > 0)."""
    docs, df, avg = _index(sources)
    q = set(tokens(query))
    n = len(docs)
    scored = []
    for title, cmd, text, tf in docs:
        length = sum(tf.values())
        s = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * length / avg))
        if cmd.lower() in q:
            s += 3.0  # the query names this command
        if s > 0:
            scored.append((s, title, cmd, text))
    scored.sort(key=lambda x: -x[0])
    return scored


def search(query, sources, k=3, budget=2500):
    if not _index(sources)[0]:
        return "documentation not available (run knowledge/*/fetch.sh)"
    out, used = [], 0
    for _, title, _, text in rank(query, sources)[:k]:
        part = f"[{title}]\n{text.strip()[:1000]}"
        if used + len(part) > budget:
            break
        out.append(part)
        used += len(part)
    return "\n\n".join(out) if out else "no documentation found; try other English keywords or a command name"
