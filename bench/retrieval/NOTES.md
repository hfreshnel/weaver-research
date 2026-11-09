# bench/retrieval — retrieval-only eval of the docs search

Question: does an embedding model find the right documentation better than the BM25 of
`bench/agent/docsearch.py`, before spending a full novice v4 run on it?

## Setup (2026-10-30)
- Script: `eval_retrieval.py` (stdlib; starts llama-server in embedding mode).
- Corpus: same chunks as the bench. `docsearch._chunks` over `archwiki`, `man` and `tldr`
  gives 48 641 chunks, 29 M chars. Arch Wiki makes 79 % of them.
- Queries: the 66 novice v4 user requests, in French, as typed. 54 are kept (18 tasks); the
  4 tasks whose oracle runs no shell command are skipped: `explain_letter`,
  `h_find_letter`, `h_scam_mail`, `termination_letter`.
- Relevance: automatic, from the oracle scripts (`mock_scripts/oracle_novice*.json`), never
  hand-written.
  - `strict`: the chunk's page is an oracle command (man/tldr page name, Arch Wiki page).
  - `mention`: `strict`, or the chunk names an oracle command as a word. Names that are
    common words are excluded (`ps du lp kill cancel`).
- Methods:
  - `bm25`: `docsearch.rank`, the bench's own code. `docsearch.search` was split into
    `rank()` + `search()` with no behaviour change; selftest OK.
  - `embed`: cosine similarity, prefixes `task: search result | query: …` for queries and
    `title: … | text: …` for documents, as the model card says. Chunks are cut at 2400 chars.
  - `hybrid`: RRF (k = 60) of the two top-100 lists. Untuned.
- Model: EmbeddingGemma 2 Q8_0 (`ggml-org/embeddinggemma-2-GGUF`, 0.31 GB, SHA-256 OK),
  llama.cpp CUDA b11887, `--embeddings --pooling mean -ub 2048 -b 2048 -np 1 -c 8192`.

Command:
```
python3 -I bench/retrieval/eval_retrieval.py --model models/embeddinggemma-2/embeddinggemma-2-Q8_0.gguf
```
- Cost: encoding the corpus took 1276 s on the GPU, once; it is cached in `outputs/`.
  Search took 70 s for 54 queries in pure Python.
- Memory: 0.5 GB of VRAM, 0.9–1.0 GB RSS. It fits next to the 4B + Bonsai 2 9B? Tight:
  5804 + 515 > 6144 MiB. On CPU it would be fine for queries only.

## Result (54 queries; hit@k = a relevant chunk in the top k; the agent sees k = 3)
| Method | Criterion | hit@1 | hit@3 | hit@10 | MRR@10 | dev hit@10 | holdout hit@10 |
|---|---|---|---|---|---|---|---|
| bm25 | strict | 0.00 | 0.00 | 0.00 | 0.000 | 0.00 | 0.00 |
| embed | strict | 0.02 | 0.04 | 0.26 | 0.061 | 0.18 | 0.38 |
| hybrid | strict | 0.00 | 0.00 | 0.06 | 0.008 | 0.06 | 0.05 |
| bm25 | mention | 0.00 | 0.06 | 0.17 | 0.041 | 0.03 | 0.38 |
| embed | mention | 0.04 | 0.11 | **0.44** | **0.122** | 0.27 | 0.71 |
| hybrid | mention | 0.02 | 0.07 | 0.28 | 0.080 | 0.12 | 0.52 |

- Per task (mean MRR, `mention`): embed beats bm25 on 10 tasks and loses on 4. Sign test
  p = 0.18, **not significant over 18 tasks**. Embed vs hybrid: 10 / 3, p = 0.09.
- Traces (top 3, phrasing 0):
  - BM25 on French novice wording returns off-topic pages (MariaDB, xmonad, Kubeadm…): it
    matches stray French words.
  - Embed returns on-topic pages that the strict label counts as wrong: "Bluetooth mouse >
    Mouse always disconnects", "CUPS/Troubleshooting > All jobs are stopped", "FAQ > Où est
    passé mon espace disque ?", "ImageMagick > Limit the storage size".
- Zero for every method on `install_video_editor`, `safe_updates`, `no_internet`,
  `slow_pc`. The corpus is Arch-centric (pacman); the Ubuntu answers (apt, flatpak,
  GNOME's gsettings) are barely there.

## Verdict
- **Embeddings > BM25 on novice wording, but not significant and low in absolute terms**:
  hit@3 is 0.11, so 89 % of the time the agent's 3 snippets would miss.
- **Hybrid (RRF) is worse than embed alone**: BM25 adds noise on this wording. Ruled out
  in this form.
- Not worth a novice v4 run yet. Pushing these snippets into the prompt is the pattern that
  already failed (`docs_err`, Arch Wiki −3).
- What the traces point to: the corpus matters more than the ranker. Ubuntu/GNOME
  documentation would be the missing piece: for example the Ubuntu desktop help (offline,
  `gnome-user-docs`/`ubuntu-docs`). External source only, never written by us (leakage rule).
- EmbeddingGemma 2 is kept on disk as the ranker for that next test.
- Limits of this eval:
  - one oracle solution per task;
  - the query is the user's request, not a query written by the agent;
  - 18 tasks.

## 2026-10-30 (evening): + Ubuntu desktop help (`knowledge/ubuntuhelp/`)
- Corpus: Ubuntu 24.04 packages `gnome-user-docs` 46.0-1ubuntu1 (C), `gnome-user-docs-fr`,
  and `ubuntu-docs` 24.04.2. The `ubuntu-docs` pages override the GNOME pages of the same
  name, as on a real Ubuntu desktop.
  - 363 en + 363 fr pages, 1174 chunks, 3.0 MB.
  - Mallard → text by `knowledge/ubuntuhelp/extract.py` (stdlib).
  - Fetched by `knowledge/ubuntuhelp/fetch.sh`; nothing installed, 2.45 MB of .deb, deleted
    after extraction.
  - New docsearch source: `ubuntuhelp`. Selftest OK.
- Cache: one vector file per source now. The existing cache was split and the 3-source
  numbers re-run identically. The 1174 new chunks took 22 s to encode.

| Sources | Method | hit@3 (mention) | hit@10 (mention) | MRR@10 (mention) | hit@10 (strict) |
|---|---|---|---|---|---|
| archwiki, man, tldr | embed | 0.11 | 0.44 | 0.122 | 0.26 |
| + ubuntuhelp | embed | 0.06 | 0.26 | 0.078 | 0.13 |
| + ubuntuhelp | bm25 | 0.02 | 0.07 | 0.020 | 0.00 |

- Why the numbers drop: Ubuntu help takes 81 of the 162 embed top-3 slots, and it describes
  the GUI without naming commands, so the automatic labels never count it.
- Traces (embed top 3, phrasing 0): its top hits are on topic and Ubuntu-correct:
  - `no_sound`: "L'ordinateur n'émet aucun son";
  - `print_duplex`: "Impression recto verso et agencement multi-pages";
  - `bigger_text`: "Changement de la taille du texte à l'écran";
  - `h_sound_muted`: "… Assurez-vous que le son n'est pas mis en sourdine";
  - `h_printer_stuck`: "Annulation, pause ou déblocage d'une impression";
  - `h_disk_full`: "Vérification de l'espace disque libre > En cas de disque trop plein".
  Misses: `slow_pc` (suspend pages), `uninstall_app`, `safe_updates`, `h_bigger_cursor`.
- Verdict: **not measurable with command labels.** Ubuntu help finds the right topic from
  novice French wording, which the other corpora did not. But it gives GUI steps, and the
  agent acts through a shell.
  - Whether "right topic + GUI steps" helps the agent can only be measured on the bench (a
    docs lever).
  - Not run yet: the docs levers already tried were −3 to 0.
