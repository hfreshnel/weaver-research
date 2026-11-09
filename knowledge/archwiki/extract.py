#!/usr/bin/env python3
"""Arch Wiki offline (arch-wiki-docs package) -> plain text, en + fr pages, Category pages skipped.

Reads the .pkg.tar.zst directly (no extraction to disk; output names are sanitized).
Output: <out>/<lang>/<Page__Sub>.txt, first line "# <title>", headings as "## ...".
Usage: python3 -I extract.py <arch-wiki-docs.pkg.tar.zst> <out_dir>
"""
import re
import sys
import tarfile
from html.parser import HTMLParser
from pathlib import Path

LANGS = ("en", "fr")
PREFIX = "usr/share/doc/arch-wiki/html/"
SKIP_CLASSES = ("mw-editsection", "toc", "noprint", "navbox", "archwiki-template-meta-related-articles-start")


class WikiText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.title = [], ""
        self.depth = 0          # div depth inside mw-parser-output (0 = outside)
        self.skip = 0           # depth of a skipped subtree
        self.stack = []
        self.pre = 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "title":
            self.in_title = True
        if self.depth == 0:
            if tag == "div" and "mw-parser-output" in cls:
                self.depth = 1
            return
        if tag in ("br", "img", "hr", "meta", "link", "input"):
            if tag == "br":
                self.out.append("\n")
            return
        self.stack.append(tag)
        if self.skip or tag in ("style", "script") or any(c in cls.split() for c in SKIP_CLASSES):
            self.skip += 1
            return
        if tag in ("h2", "h3", "h4", "h5"):
            self.out.append("\n\n## ")
        elif tag == "pre":
            self.pre += 1
            self.out.append("\n```\n")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in ("p", "div", "table", "tr", "dl", "dd", "dt", "ul", "ol"):
            self.out.append("\n")
        elif tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if self.depth == 0 or tag in ("br", "img", "hr", "meta", "link", "input"):
            return
        if not self.stack:  # closing the mw-parser-output div
            self.depth = 0
            return
        while self.stack:
            t = self.stack.pop()
            if self.skip:
                self.skip -= 1
            elif t == "pre":
                self.pre -= 1
                self.out.append("\n```\n")
            if t == tag:
                break

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.depth and not self.skip:
            self.out.append(data if self.pre else re.sub(r"\s+", " ", data))

    def text(self):
        t = "".join(self.out)
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    n, chars = 0, 0
    with tarfile.open(src, "r:zst") as tar:
        for m in tar:
            if not (m.isfile() and m.name.startswith(PREFIX) and m.name.endswith(".html")):
                continue
            rel = m.name[len(PREFIX):-len(".html")]
            lang, _, page = rel.partition("/")
            if lang not in LANGS or page.startswith(("Category:", "ArchWiki:", "Help:", "Template:")):
                continue
            p = WikiText()
            p.feed(tar.extractfile(m).read().decode("utf-8", "replace"))
            text = p.text()
            if len(text) < 200:  # redirects and stubs
                continue
            title = re.sub(r"\s+-\s+ArchWiki\s*$", "", p.title.strip()) or page
            name = re.sub(r"[^\w.,()+-]", "_", page.replace("/", "__"))[:150]
            dst = out / lang / f"{name}.txt"
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(f"# {title}\n\n{text}\n")
            n += 1
            chars += len(text)
    print(f"{n} pages, {chars / 1e6:.1f} M characters")


if __name__ == "__main__":
    main()
