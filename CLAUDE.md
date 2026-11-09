# CLAUDE.md — weaver

Exploratory project: find, through compared and measured tests, the best path to an "AI OS".
**Read `README.md` first**: it holds the owner's vision verbatim, the 8 working principles,
the platform hypothesis and the current best path. Every proposed step must tie back to
those principles.

## Working rules (set by the owner, non-negotiable)
- Quality of the result first; only then time, VRAM/RAM, compute.
- Keep a pipeline step **only if a measured gain** justifies it. Prefer the simpler/cheaper
  tool when it is equal or better, and say so explicitly.
- Compare with the same inputs and the same criteria. For each comparison, log in the
  relevant `NOTES.md`: what was tested, the result, the verdict (kept or ruled out, and why).
- One subfolder per tool/model/test, each with its own isolated env (venv or uv). **Never
  install anything globally.** So far everything is stdlib Python 3.14 (miniconda), so no
  venv has been needed. `uv` is not installed.
- Model weights, outputs and envs are gitignored. One `NOTES.md` per subfolder: model and
  version, exact command, run time, memory used, quality verdict.
- Test scripts: short, reproducible, fixed seed, parameters as arguments.
- Long runs go to the background (never block the foreground); report their duration.
- **Ask before** downloading a model > 2 GB or installing heavy deps (torch, CUDA, Docker,
  QEMU…): give the size and wait for a yes.
- **Download budget**: 40 GB granted in total (15 GB, +5 GB on 2026-10-26, +20 GB on
  2026-10-26 evening for the night's work, "each GB must be justified").
  - Owner rule (2026-10-27): **deleting a downloaded file gives its size back to the budget.**
  - Charged and still on disk, about 17.7 GB: CUDA build 0.60 + Qwen3.5-4B 2.74
    + Qwen3.5-9B 5.68 + docs corpora ~0.04 + Arch Wiki package 0.02
    + Bonsai 2 9B Q2_0 2.56 (2026-10-28, approved)
    + EmbeddingGemma 2 Q8_0 0.31 + Ornith-1.5-9B Q4_K_M 5.78 + Ubuntu help .debs 0.002
    (2026-10-30, approved; SHA-256 checked against the HF LFS oids).
  - Deleted and refunded: Granite 2.24, Gemma 4.98 (2026-10-27); Spark-X2.6-4B 3.54
    (2026-10-30); Bonsai 2 27B Q2_0 7.63 (2026-10-30 night, owner's yes). Qwen3.5-2B (1.28) was
    deleted too, but it was never charged (downloaded before the budget).
    Their NOTES and runs are kept.
  - **About 22.3 GB left.** Max 10 GB RAM per test (llama-server's prompt cache counts:
    use `--cache-ram 1024`).
- No `git init`, no commit unless asked.
- **Reply in French.** Code, file names, commits, NOTES and this file are in English.
  Exceptions: `research/*.md` are in French (reading documents for the owner).
- Report failures as they are, with the error output. Present as settled only what is verified.

## Machine
WSL2 Ubuntu 24.04, RTX 3060 Laptop **6 GB VRAM** (driver 592.82, CUDA 13.x OK), ~13 GB RAM,
i7-11800H (16 threads). The Windows host is licensed (Windows UI Automation tests are
possible there later). The prototype will run on native Linux, on a dedicated PC to buy later.

## Layout
```
README.md                vision, principles, platform hypothesis, current best path
research/                state-of-the-art.md, task-taxonomy.md, model-watch.md (FR)
runtime/llamacpp/        llama.cpp b11887 binaries in bin/ (cpu-b11887/, cuda13.4-b11887/), NOTES
models/<name>/*.gguf     qwen3.5-4b, qwen3.5-9b (Q4_K_M), bonsai-2-27b, bonsai-2-9b (Q2_0 ternary)
llm/<model>/NOTES.md     per-model verdicts; runs-*/ outputs (gitignored)
knowledge/{man,tldr,archwiki,ubuntuhelp}/ offline docs corpora (fetch.sh; data/ gitignored), NOTES.md
bench/toolcall/          v1 single-turn smoke test (frozen)
bench/lib/llama.py       llama-server lifecycle + memory peaks
bench/agent/             main harness (details and full history in bench/agent/NOTES.md)
bench/retrieval/         retrieval-only eval of the docs search (BM25 vs embeddings), NOTES
```

## bench/agent — how it works
- `run_agent.py`: multi-turn agent loop against llama-server (starts it, or uses `--server-url`).
  - Options: `--cases`, `--policy policies/<name>.json`, `--only ids`, `--max-steps`
    (default: the cases file's `max_steps`, else 8).
  - `--verify-model <gguf>` (with a `verify` policy): the verify round runs on that model,
    in two passes (all cases on the main model up to their round, one server swap, then all
    rounds on the verifier).
  - Outputs: `<out-dir>/<ts>/{summary.json,results.json,server.log[,server_verify.log]}`.
- `env.py`: sandbox with a fake `/home/user` per case.
  - Real file tools.
  - `run_shell` with an allowlist; no shell, so pipes are parsed by the harness.
  - Mocked services.
  - Safety layer: hard confirmation guard, freedesktop trash.
  - Checks and data-loss metric.
- `simsys.py`: simulated Linux machine for the novice bench: pactl, nmcli, lp/CUPS,
  scanimage, flatpak/apt/dpkg, timeshift, bluetoothctl, systemctl, xrandr/xinput (Wayland),
  … all acting on a JSON state. Nothing real is executed.
- `systree.py` (since v4.3, 2026-10-28): simulated Ubuntu system tree around the home
  (`/etc`, `/proc`, `/sys`, `/dev/input`, `/usr/bin`, `/boot`). It is consistent with the
  simulated machine and read-only except `/tmp`; sudo lifts that for one command. **The
  agent may read anywhere**: `no_escape` is no longer a check. Never expose the real host:
  every result goes through `Sandbox.unleak()`.
- `docsearch.py`: BM25 over `knowledge/` (man, tldr, Arch Wiki sections).
- Cases:
  - `cases.json` (v3: 16 dev + 10 holdout, files and shell, technical wording);
  - `cases.json` is version 4 since 2026-10-26: `chat_turns: 2` (a question in the final
    answer gets the case's scripted reply and counts as asking);
  - `cases_novice.json` (v3: 11 dev + 7 holdout, system and documents, novice wording,
    simulated machine, `chat_turns: 2`, outcome-aware simulated user, `max_steps: 12`);
  - **`cases_novice_v4.json`** (main novice bench since 2026-10-27): 22 tasks × 3 phrasings
    (p0 v3 wording, p1 terse, p2 verbose) = 66 cases (39 dev, 27 holdout). Generated by
    `make_novice_v4.py`; never edit the JSON by hand.
- Policies (levers), see `policies/`. **Current kept policy: `tools_trashq_hard_pipes`**:
  - `cwd` and actionable errors;
  - hard confirmation;
  - trash invisible to the agent;
  - safe pipes (grep/sort/head/…).
  - Optional: `docs_err` (pushes a command's docs when it fails).
  - `verify` / `verify_all`: kept policy + one check-and-finish round after the first
    answer (`verify_all`: also when the step budget runs out). Best with the 9B as verifier.
- Scripts:
  - `run_matrix.sh "<models>" "<policies>" [cases] [runs-subdir]` (env: `SERVER_EXTRA`,
    `MAX_STEPS`, `NO_PROMPT_CACHE=1`, `ORDER_SEED=N`, `VERIFY_MODEL=<model dir>` → results
    under `<policy>+<model>`);
  - `pooled.py LABEL=DIR,DIR… LABEL=…`: compare configs over several orders (use it now;
    `DIR:before` = the main model alone, from a two-model verify run);
  - `compare.py <runs-subdir> <models…>` (markdown table);
  - `show_run.py <run_dir> [ids]` (per-case traces);
  - `reliability.py <runs-subdir> <model>[/<policy>]…`: per-task k/3, per tag, per
    phrasing, paired sign tests (use it for novice v4).
- Server settings for every run since 2026-10-27:
  `SERVER_EXTRA="-np 1 -ub 256 -b 256 --cache-ram 1024"`. The 9B needs them to fit, and the
  default prompt cache pushed RSS to ~10 GB. Outcomes are unchanged for Qwen.
  If the server dies (WSL `CUDA error: unknown error`), the harness restarts it and replays
  the case (`server_restarts` in summary.json).
- **`python3 -I bench/agent/selftest.py` must print `selftest OK` before any model run.**
  It replays oracle and naive scripts through a mock server, under all safety policies,
  plus chat turns, pipes, simulated-write guard, docs probes and the verify lever (two
  models through `fake_llama_server.py`). Extend it whenever you change the harness.

Typical run (GPU; novice v4: about 10 min for the 4B, 18 min for the 9B, per policy):
```
python3 -I bench/agent/selftest.py
SERVER_EXTRA="-np 1 -ub 256 -b 256 --cache-ram 1024" bench/agent/run_matrix.sh "qwen3.5-4b" \
  "tools_trashq_hard_pipes" bench/agent/cases_novice_v4.json runs-novice-vX
python3 -I bench/agent/reliability.py runs-novice-vX qwen3.5-4b
# a config over several orders: ORDER_SEED=1..N with runs-novice-vX-oN, then
python3 -I bench/agent/pooled.py base=<dir>,<dir>,… lever=<dir>,<dir>,…
```

## Methodology lessons already paid for (do not relearn them)
- **Holdout split**: never tune on `split: holdout` cases. A lever that gains on dev but
  loses on holdout is overfitting (the `prompt` lever was caught this way).
- **Leakage**: never write knowledge (runbooks, docs) yourself for cases you know.
  Use external sources only.
- **Read traces before concluding.** Several "model failures" turned out to be harness or
  simulator bugs:
  - `move_path dir/`;
  - tar archiving into the folder being archived (timing race, fixed with an atomic write);
  - missing simulated subcommands;
  - absurd file sizes;
  - "(no answer)" user;
  - an agent that had already succeeded being sent back to work by the user;
  - `which`/`apt list --installed` not seeing a simulated `apt install` (a checker then
    reinstalled in a loop);
  - a keyword clash in `SimMachine.log(action, **kw)` (pass `op=`, not `action=`).
- **Valid run = `internal_errors == 0` and `llm_errors == 0`** in `summary.json`.
  `model_errors` (an unparseable tool call, HTTP 500 from llama-server; a context overflow,
  HTTP 400) is a model failure and does not invalidate the run.
- Qwen's chat template refuses a second system message (HTTP 500): put extra context into
  the single system message.
- Runs are deterministic at temperature 0 and seed 42 (two runs of the same config give
  66/66 identical traces since the clock fix), but only for an identical run sequence:
  llama-server reuses the KV cache left by the previous case, so any upstream change
  (a prompt, the step budget, the cache setting) flips about ±5 of 66 novice cases.
  Gaps of a few cases are noise. Compare over ≥ 4 case orders with `pooled.py`.
- Tool outputs must be time-independent: files created during a case get a case clock
  (`_freeze_clock`). Real mtimes leaked the run time and made traces diverge.
- Real commands run under a 10 s timeout: a timeout is a tool error, not an internal one.
- Per-command safety interception has holes: a simulated `pdfunite` overwrote its input.
  Robust protection must eventually live at the filesystem level (snapshots before each
  agent action).
- Tool outputs must not leak the real environment (temp paths, account name):
  `env.py` rewrites them.
- Simulated outputs must not leak hints either (2026-11-06): an internal state in a listing
  (`stuck` in `lpstat`), a long format where the real one is short, a "succeeded" no-op on a
  missing file (`xdg-open`), or a simulator-only "unsupported here" message. Each one either
  helps the model unrealistically or traps it in a loop. Mimic the real program's output and
  exit code; grep the traces for such messages after every simulator change.

## Current state (2026-10-28 morning; see the v4.5 section below for the latest)
- Brain: **Qwen3.5-4B Q4_K_M**, llama.cpp CUDA, all layers on GPU (3.1 GB VRAM, 3.0 GB RSS).
  - Qwen3.5-9B alone as the brain (5.4 GB VRAM, 5.8 GB RSS, +70 % latency): no measurable
    difference (novice v4 32–36 vs 34–36/66; v3 23 vs 22/26). It loops far less.
  - Gemma 4 E4B (16/66), Granite 4.2 3B, Qwen3.5-2B: ruled out, weights deleted 2026-10-27.
- **Best measured configuration: "4B acts, 9B checks and finishes"** (policy `verify_all`,
  `--verify-model` 9B, `bench/agent/NOTES.md` "Retry with verification").
  - The 4B runs the task. After its first answer, or when its 12-step budget runs out, the
    9B gets one round from the same state: check with read-only commands, fix, answer.
  - Novice v4, simulator v4.2, 8 case orders: **38.0 vs 35.8/66** (+2.25 per run, 95 % CI
    [+0.4, +4.4], tasks 8 vs 1, p = 0.039); holdout 17.1 vs 16.0/27 (63 %; target 80 %).
  - Control: the same round run by the 4B gives +0.75 (noise). So the gain is the stronger
    model's second look. Self-verification on the first answer only (`verify`): +0.
  - Cost: +79 % latency per case (8.0 → 14.3 s; every final answer gets a round). The 4B
    and the 9B do not fit together in 6 GB of VRAM: the bench swaps once per run (two
    passes). Interactive use here would swap per task.
  - Not yet adopted as the deployment pipeline (owner decision, see below).
- Novice v4 per task (kept 4B, 8 orders): still 0 on `print_duplex` and `safe_updates`;
  low on `no_sound`, `uninstall_app`, `h_find_letter`, `h_disk_full`, `h_printer_stuck`.
  These are knowledge gaps; the 9B round mostly fixes `scan_to_pdf`, `explain_letter`,
  `h_bigger_cursor`, `h_scam_mail`.
- Simulator v4.2 (2026-10-28): package state is consistent across `apt install`, `which`,
  `apt list --installed`, plus `dpkg -l/-s` and `apt-cache`. The earlier "kdenlive install
  looks absent" loop was a simulator bug.
- Levers tested on novice v4 and not kept: `docs_err` (equal), Arch Wiki pushed or as a tool
  (−3), OS line in the prompt (−1/−2 for the 4B), `--max-steps 20` (−4, more loops),
  `--no-prompt-cache` (2× latency), self-verification (`verify`, 4B).
- **Noise floor**: one config over case orders scores 35–39/66; two orders disagree on 7–12
  cases. Evaluate a config over ≥ 4 orders with `pooled.py` (task bootstrap CI, sign test
  over tasks). For a two-model verify run, `DIR:before` gives the paired 4B baseline for
  free (pass 1 is identical to a plain run, checked on 594 traces).

## Owner decisions (2026-10-28 morning)
1. "4B acts, 9B checks" (`verify_all` + 9B): **kept as an option**, not the pipeline. Keep
   looking for a cheaper alternative (a checker that fits next to the 4B, or a better brain).
2. Bonsai 2 27B Q2_0 (7.63 GB): **download approved**. It is in `models/bonsai-2-27b/`,
   SHA-256 checked against the Hugging Face LFS oid. Test it as a checker and as a brain;
   first a coherence check, since the HF card warns of gibberish on upstream builds.
3. **The agent and the PC are one**: the agent may go anywhere on the machine (reads
   anywhere). Context (conversation, memory) stays separate per user, but machine access is
   global by default. On the bench: `no_escape` no longer fails a case. System paths are
   served by a **simulated** Ubuntu tree, never the real host (no leak of the real WSL
   environment).
5. Bonsai 2 9B Q2_0 (2.56 GB): download approved (a checker that may fit next to the 4B).
6. Plan approved (2026-10-28): simulator v4.3 + `no_escape` change, then re-baseline (4B and
   4B + 9B checker, 4 orders), then Bonsai 2 27B and Bonsai 2 9B as checkers, then the
   27B as the brain.
4. Simulator gaps: **yes, simulate them** (`/dev/input`, `/sys`, `/proc` reads, `sudo`,
   `systemctl`, `xrandr`), faithfully and without hints. This needs a re-baseline.
7. (2026-10-28 evening) **Bonsai 2 27B dropped**, both as the checker and as the brain:
   "if it is that slow, it is not worth it".
   - As the checker: 132 s per case, 2 h 28 per run, 42 of 52 rounds used the full step
     budget, 38 vs 41/66 for the Qwen 9B on order 0.
   - Its weights (7.63 GB) were deleted on 2026-10-30 (owner's yes), budget refunded.
8. (2026-11-06) **Pipeline adopted: "4B acts, Bonsai 2 9B checks and finishes"**
   (policy `verify_all`, `--verify-model` Bonsai 2 9B Q2_0, `-c 8192` on both servers).
   - Why: v4.4, 8 orders, 37.8 vs 34.5/66 (p = 0.002); both models resident on the 6 GB GPU
     (5.8 GB at 8k context), no swap; 12.0 s per case.
   - Known limit, stated to the owner: the holdout gain is only +0.6 (15.5 vs 14.9/27).
   - It is now the reference config: compare new levers against it (and the 4B alone).
     The Qwen 9B checker stays the option for a GPU with ≥ 10 GB.

## State on simulator v4.5 (2026-11-07 night, `runs-novice-v9-o{0..7}`): the reference
- v4.5 fixes (details in `bench/agent/NOTES.md`): realistic `pdfinfo`, `ip -o`, `/run`,
  `/etc/NetworkManager` (root-only saved Wi-Fi keyfiles), sized fixture scans; apt needs root
  and stops at [Y/n] without `-y`, `-o` values parsed, `apt remove` no longer removes a Flatpak;
  `xdg-open` fails on a missing file; CUPS-faithful `lpstat`; real replies instead of most
  "unsupported here" messages (pactl, wpctl, nmcli, flatpak, bluetoothctl, lpadmin, qpdf, …).
- 8 orders: 4B alone 33.8/66 (holdout 13.9); **4B + Bonsai 2 9B checker 37.1** (holdout 15.0);
  pipeline − 4B **+3.4, CI [+1.4, +5.5], tasks 8 / 0, p = 0.008, holdout +1.1**.
- v4.4 → v4.5: −0.75 / −0.6, not significant. Two holdout tasks lost hints the old simulator
  gave (`h_printer_stuck`: job state in `lpstat -p`; `h_sound_muted`: long form for
  `pactl list sinks short`).
- Still 0: `print_duplex`, `safe_updates` (snapshot first + Flatpak updates); low:
  `h_find_letter`, `uninstall_app`, `h_printer_stuck`, `scan_to_pdf`.

## State on simulator v4.4 (2026-10-29 night, `runs-novice-v8-o{0..7}`)
- Simulator v4.4 fixes, from the v7 traces (details in `bench/agent/NOTES.md`):
  - `ip` (privileges, RF-kill), `xinput` props and usage, relative globs, real `lpadmin`
    options (printer defaults apply to jobs);
  - `pgrep`, `lspci`, `lsmod`;
  - `Sandbox.sudo` lets simulated commands check privileges.
- 8 orders:
  - 4B alone: 34.5/66;
  - **4B + Bonsai 2 9B checker: 37.8** (+3.25, CI [+1.4, +5.6], tasks 10 / 0, p = 0.002);
  - holdout only +0.6 (15.5 vs 14.9/27, 57 %): the gain is mostly on dev tasks.
- Bonsai 2 9B as the brain alone: 23.2/66 (−10.5 vs the 4B, p = 0.008). Ruled out.

## 2026-10-30: HF scan, Spark-X2.6-4B, EmbeddingGemma 2
- HF scan (Oct 2025 → Oct 2026), the candidate list is in `research/model-watch.md`.
- Spark-X2.6-4B as the brain: 12.5 vs 34.5/66 on orders 0–3 (p = 0.001). **Ruled out**
  (`llm/spark-x2.6-4b/NOTES.md`). Its weights (3.54 GB) can be deleted: ask first.
- EmbeddingGemma 2 (`models/embeddinggemma-2/`), retrieval-only eval in `bench/retrieval/`:
  - on French novice requests it beats BM25 (hit@10 0.44 vs 0.17), not significant;
  - hybrid is worse;
  - the corpus lacks Ubuntu/GNOME docs (Arch-centric).
  Next: an external offline Ubuntu/GNOME help corpus, then the same eval.
- Ubuntu desktop help corpus (`knowledge/ubuntuhelp/`, docsearch source `ubuntuhelp`): it
  finds the right topic from novice French wording, but gives GUI steps; the command-based
  retrieval labels cannot score it (`bench/retrieval/NOTES.md`).

## 2026-10-30 night
- Harness: a verify round whose verifier crashed is now **replayed** (main model's turns
  from a tape, conversation digest checked), instead of staying an `llm_error`.
- **Ornith-1.5-9B as the checker: ruled out** (`llm/ornith-1.5-9b/NOTES.md`). Orders 0–3:
  37.5 vs Bonsai 2 9B 37.2/66 (+0.25, CI [−0.8, +1.2]), but 1.6× slower, it cannot sit
  next to the 4B, and 17–20 rounds per run end without an answer (vs 4–7 for Bonsai).
  Its weights (5.78 GB) can be deleted: ask first.
- New lever `docs_ubuntu_embed` (`embedsearch.py`): the top 3 Ubuntu help chunks for the
  request, ranked by EmbeddingGemma 2 on CPU, pushed into the system message.
  `run_matrix.sh` takes `EMBED_MODEL=embeddinggemma-2`.
  - 4B alone, 8 orders: 34.1 vs 34.5/66 (p = 0.80), more loops. **Ruled out.**
  - With the Bonsai checker, 4 orders: 36.2 vs 37.2 (p = 0.61). **Not kept.** Both shift
    successes from dev to holdout tasks (not significant).
- Ornith-1.5-9B as the **brain alone**, 4 orders: 37.8 vs 34.5 for the 4B (CI [−3.8, +10.2],
  p = 0.65), holdout 17.0 vs 14.5. It solves knowledge-gap tasks (`h_find_letter`,
  `uninstall_app`, `h_disk_full`), but costs 23.9 s per case (3.2×). Not separated:
  orders 4–7 proposed to the owner.
- Simulator fidelity gap to fix next: `pdfinfo` prints `Producer: weaver-sim` and 3 fields.

## State on simulator v4.3 (2026-10-28 evening, `runs-novice-v7-o*`)
- Orders 0–3:
  - 4B alone: 33.8/66;
  - 4B + Qwen3.5-9B checker: 39.2 (+5.5, p = 0.002);
  - 4B + Bonsai 2 9B checker: 37.2 (+3.5, p = 0.008), 12.0 s per case;
  - 8 orders: Qwen checker 39.1, Bonsai checker 37.9, 4B alone 34.4. Both are significant
    vs the 4B (tasks 12 / 0). **Qwen − Bonsai: +1.25, CI [−1.8, +4.6], tasks 6 / 5, not
    separated.**
- **The 4B and Bonsai 2 9B fit together on the GPU**: 5804 / 6144 MiB, with no slowdown
  (`bench/coresidence/NOTES.md`). That means no swap per task. The Qwen 9B cannot sit
  next to the 4B.
  - Context sweep (2026-11-06): ~32 MiB per 1k tokens per model. The pair fits up to ~13k
    each; at 16k/32k it spills into WSL shared memory. The novice bench never exceeds 5.8k
    tokens per request: keep `-c 8192`.
- v6 → v7, 4B baseline: −2.25 (not significant). The new no-op `xrandr`/`xinput` under
  Wayland are dead ends for the 4B on `bigger_text` and `h_bigger_cursor`.
  - Small `xinput` fidelity gaps are noted in `bench/agent/NOTES.md`, not fixed yet: fix
    them with the next simulator change, then re-baseline.

## Pending decisions (proposal for the owner, updated 2026-11-07 morning)
**Start the next session here.** The night of 2026-11-06 → 07 is summed up in the
"State on simulator v4.5" section above; details in `bench/agent/NOTES.md` and
`llm/ornith-1.5-9b/NOTES.md`. Open questions, in the recommended order:
1. ~~Adopt "4B acts, checker finishes"~~: **adopted 2026-11-06 (owner), with Bonsai 2 9B
   as the checker** (see "Owner decisions", item 8).
2. ~~Delete the Bonsai 2 27B weights~~: done 2026-10-30 night (owner's yes), 7.63 GB refunded.
3. **Next lead, proposed 2026-10-29.** What is still low is knowledge gaps:
   - `print_duplex` and `safe_updates` at 0;
   - `no_sound`, `h_find_letter`, `h_disk_full`, `uninstall_app` low.
   The docs levers already tried (`docs_err`, Arch Wiki) did not help. Look for another way
   to make knowledge reachable, or a newer-generation brain that fits in 6 GB.
   - 2026-10-31: the Ubuntu help pushed by embeddings did not help either (34.1 vs 34.5,
     8 orders): the 4B finds the right page but recites the GUI steps instead of acting.
4. ~~Ornith-1.5-9B as the brain, orders 4–7~~: done 2026-11-06 night. 8 orders: 36.1 vs
   34.5/66 for the 4B (p = 0.65), vs 37.8 for the adopted pipeline (−1.6, p = 0.14), 25 s per
   case. **Ruled out** (`llm/ornith-1.5-9b/NOTES.md`). It still wins the knowledge-gap tasks.
5. **Ornith weights (5.78 GB)**: no further use planned; delete to refund the budget? (ask).
6. ~~Next simulator change~~: **simulator v4.5 done** (2026-11-06 night, see the v4.5 section).

Later, from `research/task-taxonomy.md`:
- an "external effect" (R3) confirmation guard for sending, paying and submitting;
- a local IMAP/SMTP mail bench;
- local replicas of administrative portals for web tasks;
- the accessibility tree vs screen vision channel;
- filesystem-level snapshots;
- a lay-user human baseline.
