# Spark-X2.6-4B (XHToken) — ruled out as the brain (2026-10-30)

- Weights: `XHToken/Spark-X2.6-4B-GGUF`, `Spark-X2.6-4B-Q4_K_M.gguf`, 3.54 GB, SHA-256
  `91cb2811…cbd9`, which matches the HF LFS oid. Owner approved the download on 2026-10-30.
- Card claims: a 4B "on-device agent", post-trained on top of Spark-X2.5. It says it matches
  ~9B models on tool use and planning. Upstream llama.cpp `spark2_5` arch, ≥ b10828.
- Runtime: llama.cpp CUDA b11887, all layers on GPU, thinking off
  (`enable_thinking: false`, as for Qwen).
  - 3.3 GB of VRAM, 3.7 GB RSS.
  - 68 tok/s generation.
  - Load in 26 s.
- Coherence check: fluent French answer. On a minimal prompt without the bench's system
  message, it answered "no sound" with a chat reply instead of a tool call.

## Novice v4, simulator v4.4, orders 0–3
Command (per order N):
```
ORDER_SEED=N SERVER_EXTRA="-np 1 -ub 256 -b 256 --cache-ram 1024" bench/agent/run_matrix.sh \
  "spark-x2.6-4b" "tools_trashq_hard_pipes" bench/agent/cases_novice_v4.json runs-novice-v8-oN
```
- About 18 min per order, 72 min in all.
- All runs valid: 0 internal errors, 0 LLM errors, 0 restarts, 0 data loss. There were 3
  model errors (unparseable tool calls).

| Config | Outcomes per run (o0–o3) | Mean | Dev | Holdout | Latency/case |
|---|---|---|---|---|---|
| Qwen3.5-4B (v8 `:before`) | 33 37 35 33 | 34.5 | 20.0 | 14.5 | ~7.4 s |
| Spark-X2.6-4B | 13 13 13 11 | **12.5** | 6.5 | 6.0 | 15.7 s |

- **4B − Spark: +22.0, CI [+13.8, +30.8], holdout +8.5, tasks 15 / 1, p = 0.001.**
- On order 0, 27 of 66 cases ran out of the 12-step budget.
- Traces (`show_run.py`, order 0):
  - It wanders instead of using the obvious tool:
    - "no internet": it explores `/etc`, `/proc` and `/run`, and never tries `nmcli`;
    - "sound muted": it inspects processes and wants to kill `tracker-miner-fs-3`, which it
      calls "malicious".
  - It ignores actionable errors: it keeps chaining with `;` and `2>/dev/null` after every
    refusal.
  - It misreads the confirmation guard: it tried `delete_path /proc/1530` after an unclear
    reply.
- Small simulator fidelity gaps seen in these traces: `ip -o` is unknown, `/run` is absent.
  They hit the 4B too and do not explain a 22-case gap. They are noted in
  `bench/agent/NOTES.md`.

## Verdict
**Ruled out.** It is far below the Qwen 4B on our bench, and 2× slower per case. The card's
agent claims do not carry over to novice desktop tasks. The weights (3.54 GB) can be
deleted for a budget refund: ask the owner first.
