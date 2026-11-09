"""Mallard help pages (.page) -> plain text: '# title', then '## section' blocks. Stdlib only.
Usage: extract.py <usr/share/help dir> <out dir>"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://projectmallard.org/1.0/}"
BLOCK = {"p", "item", "title", "screen", "code", "note", "td", "th", "desc"}
SKIP = {"info", "comment", "media", "links"}


def text(el):
    out = []
    top_titles = set(el.findall(NS + "title"))  # printed as the heading instead

    def walk(e):
        tag = e.tag.replace(NS, "") if isinstance(e.tag, str) else ""
        if tag in SKIP or tag == "section" or (tag == "title" and e in top_titles):
            if e.tail:
                out.append(e.tail)
            return
        if tag in BLOCK:
            out.append("\n")
        if tag == "gui":
            out.append("“")
        if tag == "key":
            out.append(" ")
        if e.text:
            out.append(e.text)
        for c in e:
            walk(c)
        if tag == "gui":
            out.append("”")
        if tag in BLOCK:
            out.append("\n")
        if e.tail:
            out.append(e.tail)

    for c in el:
        walk(c)
    lines = [" ".join(l.split()) for l in "".join(out).split("\n")]
    return "\n".join(l for l in lines if l)


def page(path):
    root = ET.parse(path).getroot()
    t = root.find(NS + "title")
    title = " ".join("".join(t.itertext()).split()) if t is not None else path.stem
    parts = [f"# {title}", text(root)]
    for sec in root.iter(NS + "section"):
        st = sec.find(NS + "title")
        head = " ".join("".join(st.itertext()).split()) if st is not None else ""
        body = text(sec)
        if head and body.startswith(head):
            body = body[len(head):].lstrip("\n")
        parts.append(f"## {head}\n{body}")
    return "\n\n".join(p for p in parts if p.strip())


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    for lang, out in (("C", "en"), ("fr", "fr")):
        (dst / out).mkdir(parents=True, exist_ok=True)
        for p in sorted((src / lang).glob("*/*.page")):  # gnome-help/ (ubuntu-docs overrides in place)
            try:
                (dst / out / f"{p.stem}.txt").write_text(page(p))
            except ET.ParseError as e:
                print(f"skip {p}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
