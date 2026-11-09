# Ornith-1.5-9B (ornith-ai, 2026-08-18), Q4_K_M

- File: `models/ornith-1.5-9b/Ornith-1.5-9B-Q4_K_M.gguf`, 5.78 GB, from the official repo
  `ornith-ai/Ornith-1.5-9B`. SHA-256 checked against the Hugging Face LFS oid. Downloaded
  2026-10-30 with the owner's approval.
- Card (self-reported, not measured here): base Qwen3.5 / Gemma 4 + agentic RL;
  Terminal-Bench 2.1 46.2 vs 21.3 for Qwen3.5-9B, MCP-Atlas 54.2 vs 46.8.
- Why: a **checker** candidate in place of the Qwen3.5-9B (same footprint, so it cannot sit
  next to the 4B on this GPU; the bench swaps once per run).
- Runtime: llama.cpp b11887 CUDA, `-ngl 99`, `-np 1 -ub 256 -b 256 --cache-ram 1024`.
  llama-server warns that the chat template "supports preserving reasoning"; thinking stays
  off (`enable_thinking: false`), as for every model on the bench.
- Memory as the verifier: 5327 MiB VRAM delta, 5.9 GB RSS; loads in ~59 s (cold).

## Checker on novice v4, simulator v4.4 (`verify_all`, 4B acts)
Command (one order):
```
ORDER_SEED=N VERIFY_MODEL=ornith-1.5-9b SERVER_EXTRA="-np 1 -ub 256 -b 256 --cache-ram 1024" \
  bench/agent/run_matrix.sh "qwen3.5-4b" "verify_all" bench/agent/cases_novice_v4.json runs-novice-v8-oN
```
Results under `llm/qwen3.5-4b/runs-novice-v8-oN/verify_all+ornith-1.5-9b/`.

- No separate coherence script: the order-1 run is a coherent checker (rounds fixed 4,
  broke 0; its answers are well-formed French, e.g. on `h_printer_stuck__p1`).
- Order 0, 20:44 run (`20261030-204434`): **invalid**, 3 verifier crashes (WSL
  `CUDA error: unknown error` in `create_checkpoint`) left 3 `llm_errors`. It scored 34/66.
  This led to the replayable verify round (`bench/agent/NOTES.md`, 2026-10-30 night).
- Order 1 (`20261030-211042`): valid, **37/66** vs 39 for the Bonsai 2 9B checker on the same
  order; 19.2 s per case vs 10.7 s.
- Order 2, 21:34 run: stopped mid-run (the session ended), no summary. Not used.
- Orders 0, 2, 3 rerun on 2026-10-30 night with the replay fix (`20261030-231647`,
  `-233740`, `-235935`): all valid, 0 verifier crash this time (so no replay was needed).
  20–23 min per order.

### Result, orders 0–3 (`pooled.py`, outcome = every check except "answered")
| Config | Outcomes per run | Mean | Holdout | Latency/case | Pass (outcome + answered) |
|---|---|---|---|---|---|
| 4B alone (`:before` of the Bonsai runs) | 33 37 35 33 | 34.5 | 14.5 | ~7.4 s | – |
| 4B + Bonsai 2 9B checker | 36 40 37 36 | 37.2 | 15.0 | 11.6 s | 36 39 37 36 = 37.0 |
| **4B + Ornith-1.5-9B checker** | 36 41 37 36 | **37.5** | 15.0 | **18.3 s** | 35 37 35 34 = **35.2** |

- Ornith − 4B: +3.0, CI [+0.8, +5.5], tasks 6 / 0, p = 0.031.
- **Ornith − Bonsai: +0.25, CI [−0.8, +1.2], tasks 3 / 2, p = 1.0; holdout +0.0.** Equal.
- But Ornith often fixes the state and then keeps checking until its 12-step round runs out,
  **without answering the user**: 17–20 rounds per run end with no answer, vs 4–7 for
  Bonsai. On `pass` (the state is right *and* the user got an answer) it is 1.8 below
  Bonsai.
  - Example: `bluetooth_mouse__p1`, order 1. It pairs and connects the mouse, then
    re-checks with `xinput list`, `/dev/input`, `lsmod`… for 12 steps. Under Wayland
    `xinput` only shows XWayland's virtual devices, which is faithful, not a simulator bug.
- Cost: 1.6× Bonsai's latency per case, 5.3 GB VRAM. It cannot sit next to the 4B, so
  interactive use would mean a model swap per task.
- **Verdict: ruled out as the checker.** It is not better than Bonsai 2 9B on outcomes, it is
  worse on answering, and it costs more. More orders were not run: the CI is already within
  ±1.2 of Bonsai. Its weights (5.78 GB) can be deleted to refund the budget: ask first.
- Ornith as the brain alone was not tested.

## Brain alone on novice v4, simulator v4.4 (kept policy `tools_trashq_hard_pipes`), orders 0–3
Command (one order):
```
ORDER_SEED=N SERVER_EXTRA="-np 1 -ub 256 -b 256 --cache-ram 1024" \
  bench/agent/run_matrix.sh "ornith-1.5-9b" "tools_trashq_hard_pipes" bench/agent/cases_novice_v4.json runs-novice-v8-oN
```
- 27–30 min per order (2026-10-31 03:25–05:20). 5.3 GB VRAM, 5.9 GB RSS. All runs valid; one
  server crash on order 0 (`h_wifi_daughter`) was restarted and replayed by the harness.
- Outcomes 37 35 42 37 = **37.8 vs 34.5/66 for the 4B** (Δ +3.25, CI [−3.8, +10.2], tasks
  11 / 8, p = 0.65). Holdout **17.0 vs 14.5** (+2.5), dev 20.8 vs 20.0. Not significant: the
  tasks move a lot in both directions.
  - Better than every other config on knowledge-gap tasks: `h_find_letter` 0.58 (0 for the
    4B, with or without a checker), `uninstall_app` 0.50 (0), `h_disk_full` 0.42 (0.17),
    `h_wifi_daughter` 1.00 (0.75), `no_sound` 0.42 (0.25).
  - Worse on `h_merge_scans` 0.67 (1.00), `h_sound_muted` 0.42 (0.67), `slow_pc` 0.75
    (1.00), `h_printer_stuck` 0.17 (0.25).
  - It still exhausts the budget: 26–28 cases per run end at `max_steps`, 5–7 of them with
    the state right but no answer to the user. Pass (outcome + answer): 32 30 35 32.
- Cost: **23.9 s per case, 3.2× the 4B (7.4 s)**, 5.3 GB VRAM; no checker fits next to it.
- vs the 4B + Bonsai 2 9B checker (37.2): Δ +0.5, CI [−6.0, +7.2], p = 1.0. Equal, at twice
  the latency.
- **Verdict: not adopted on 4 orders.** Its holdout (17.0/27) is level with the best seen
  (17.1, 4B + Qwen 9B checker on simulator v4.2, 8 orders) without any checker. Separating it
  from the 4B needs orders 4–7 (~2 h). Proposal for the owner.

### Orders 4–7 (2026-11-06 night) and the 8-order verdict
- Run on a **frozen copy of the v4.4 bench** (`bench/agent-v44-frozen/`, removed afterwards),
  so that the simulator v4.5 work done the same night could not leak into these runs. Script
  kept as `run_ornith_night_20261106.sh` (same arguments as `run_matrix.sh`), log as
  `runs-novice-v8-night-20261106.log`. 2 h 05 for the 4 orders (28–34 min each).
- All valid: 0 internal / 0 LLM errors; model errors 1 1 0 0; one server crash on order 7
  restarted and replayed by the harness. 24.6–27.7 s per case.
- Outcomes orders 4–7: 35 33 36 34 (orders 0–3 were 37 35 42 37).

`pooled.py` over orders 0–7 (4B = `:before` of the `verify_all+bonsai-2-9b` v8 runs):

| Config | Outcomes per run | Mean | Dev | Holdout | Latency/case |
|---|---|---|---|---|---|
| 4B alone | 33 37 35 33 35 33 38 32 | 34.5 | 19.6 | 14.9 | ~7.4 s |
| Ornith-1.5-9B alone | 37 35 42 37 35 33 36 34 | 36.1 | 20.2 | 15.9 | 25.2 s |
| 4B + Bonsai 2 9B checker (adopted) | 36 40 37 36 38 39 39 37 | 37.8 | 22.2 | 15.5 | 12.1 s |

- Ornith − 4B: **+1.6, CI [−4.6, +8.0], tasks 8 for Ornith / 11 for the 4B, p = 0.65.**
- Ornith − pipeline: **−1.6, CI [−7.5, +4.6], tasks 5 / 12, p = 0.14.** Holdout +0.4.
- Its profile is unchanged: much better on knowledge-gap tasks (`h_find_letter` 0.54 vs 0.08,
  `uninstall_app` 0.50 vs 0.00–0.08, `h_disk_full` 0.46 vs 0.17–0.21, `no_sound` 0.38 vs
  0.12–0.17), much worse on `bluetooth_mouse` (0.00 vs 0.42–0.54), `slow_pc` (0.75 vs 1.00),
  `h_merge_scans` (0.62 vs 0.88).
- **Verdict: ruled out as the brain.** Not separated from the 4B, below the adopted pipeline
  (not significant), twice its latency, 5.3 GB VRAM with no room for a checker. The +3.25 of
  orders 0–3 was mostly order noise. Its knowledge-gap wins are the one thing worth keeping
  in mind: a brain that knows more Ubuntu would lift those tasks, if it did not lose others.
- Weights (5.78 GB) can now be deleted to refund the budget: **ask the owner first.**
