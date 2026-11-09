# Knowledge corpora (offline documentation for the agent)

Goal: test whether the procedures that small models lack can be supplied by **documentation
that ships with a real Linux system**, instead of a bigger model. Examples of missing
procedures: duplex printing, snapshot before updating, unblocking a CUPS queue.

**Leakage rule**: only external sources. I do not write how-to notes myself, because I know
the bench cases, holdout included.

## Corpora
| Corpus | Source | Version | Size | License | Fetch |
|---|---|---|---|---|---|
| man | Official Ubuntu 24.04 packages, `usr/share/man/man{1,8}` only, rendered with `groff -man -Tutf8 \| col -bx` | see `man/packages.txt` (23 packages) | 447 pages, 3.5 MB | per package (as shipped by Ubuntu) | `knowledge/man/fetch.sh` |
| archwiki | Arch Linux package `arch-wiki-docs` `20261003-1` (offline HTML dump of the wiki), en + fr pages, Category/Help/Template pages and stubs < 200 chars dropped, HTML → text by `knowledge/archwiki/extract.py` (stdlib) | pkg sha256 `1824753d…7d76e` | 19.5 MB download; 2142 en + 168 fr pages, 21.9 M chars, 26 MB on disk | GFDL 1.3+ | `knowledge/archwiki/fetch.sh` |
| tldr | tldr-pages release `v2.3` (2025-03-07), `common` + `linux` platforms, en + fr | zips sha256 `e60d117c…5853` (en), `22dbe06b…a57` (fr) | 6774 en + 900 fr pages, 31 MB | CC BY 4.0 | `knowledge/tldr/fetch.sh` |
| ubuntuhelp | Ubuntu 24.04 desktop help: packages `gnome-user-docs` + `gnome-user-docs-fr` 46.0-1ubuntu1, overridden by `ubuntu-docs` 24.04.2 (as installed on Ubuntu); Mallard → text by `knowledge/ubuntuhelp/extract.py` (stdlib), C → en, fr | sha256 in `ubuntuhelp/packages.txt` | 2.45 MB download; 363 en + 363 fr pages, 3.0 MB | CC BY-SA 3.0 (GNOME/Ubuntu docs) | `knowledge/ubuntuhelp/fetch.sh` |

- Nothing is installed: `apt-get download` (no root) followed by `dpkg-deb --fsys-tarfile`,
  extracting only the man pages, all in temporary directories. The downloaded `.deb` files
  are deleted after extraction.
- Pages for the simulated tools are present: lp, lpstat, cancel, cupsenable, timeshift,
  snapper, nmcli, pactl, scanimage, bluetoothctl, gsettings, pdfunite, flatpak… `wpctl`
  has no man page, but has a tldr page.
- Checked content:
  - `man lp` documents `-o sides=two-sided-long-edge`; `tldr lp` does not;
  - `tldr timeshift` gives `sudo timeshift --create`;
  - `tldr cupsenable` gives `cupsenable -c` (cancel all jobs).
- The data is gitignored (`knowledge/*/data/`). Run the fetch scripts to rebuild it.

## Search (`bench/agent/docsearch.py`)
- BM25 over chunks, stdlib only, no embeddings. A tldr page is one chunk. A man page is
  split into paragraph groups of about 1200 characters. A query that names the command
  gets a bonus.
- Index build: 0.26 s (man), 0.58 s (tldr), 0.87 s (both); about 10k chunks.
- Results: top 3 chunks, 2500 characters in all.
- **Known limitation**: French queries find nothing for these commands (the French tldr
  pages do not cover them). The tool asks for English keywords. A multilingual (embedding)
  search would be the next step, only if the measurements justify it.
- Probes covered by `selftest.py`:
  - man, "print both sides duplex lp" → `two-sided-long-edge`;
  - tldr, "create system snapshot timeshift" → `timeshift --create`;
  - tldr, "printer disabled resume" → `cupsenable`.

## Agent interface (policy `docs`: `[]`, `["tldr"]`, `["man"]`, `["man","tldr"]`)
- `search_docs(query)` tool.
- `man CMD` / `tldr CMD` through `run_shell`: the natural reflex on Linux.

## Arch Wiki (task-oriented knowledge, added 2026-10-26)
- Why: the two never-solved novice tasks (`safe_updates`, `h_printer_stuck`) need *task*
  procedures ("snapshot before upgrading", "re-enable a stopped CUPS queue"), which man and
  tldr pages, organised by command, do not give. The Arch Wiki is organised by task and
  topic (`CUPS/Troubleshooting`, `System maintenance`, `Timeshift`, `Bluetooth mouse`).
- Distribution caveat: the wiki targets Arch (pacman). Most procedures (CUPS, NetworkManager,
  PipeWire, bluetoothctl, Timeshift) are distribution-neutral; package commands are not.
- Extraction: 15.9 s for the whole package, read in memory from the `.pkg.tar.zst` (Python
  3.14 `tarfile` zstd support), never extracted to disk.
- Search: one chunk per section, prefixed with the page title (about 1200 characters). Index
  build 4.2 s, once per process.
- Sanity probes (written by me, knowing the answer, so they only check the corpus, not the
  lever): "printer stuck jobs cups resume printer disabled" → `CUPS > cups*` section
  (cupsenable); "system update safely snapshot before upgrade timeshift" → `Timeshift >
  Usage` (`timeshift --create`). The lever is measured with the model's own keywords
  (`wiki_auto`) or its own searches (`wiki_tool`).
- Result (novice v4, `runs-novice-v4c`, details in `bench/agent/NOTES.md`): **no gain, not
  kept**.
  - 4B kept 36/66, `wiki_auto` 33/66, `wiki_tool` 33/66.
  - Gemma `wiki_auto` collapses to 2/66: it writes the commands in prose instead of calling
    tools.
  - With their own keywords, the models do not reach the useful sections: `safe_updates`
    gets `pacman/Rosetta` (the 4B then runs `pacman -Syu` on Ubuntu), and
    `h_printer_stuck` gets `CUPS/Printer sharing`.
  - Offered as a tool, the wiki is searched 1–2 times in 66 cases (Qwen).
  - Kept on disk (26 MB) for a later retrieval with better queries (e.g. a reformulation
    step or multilingual embeddings), only if one is proposed.

- 2026-10-30: `ubuntuhelp` added. It is GUI-oriented: only 8 en pages name a bench command. Eval in `bench/retrieval/NOTES.md`.
