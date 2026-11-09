# Co-residence: the 4B brain and a checker loaded together on the GPU

Question: can "4B acts, checker finishes" run without a model swap per task on the 6 GB GPU?
The bench swaps once per run (two passes). Interactive use needs both models resident.

## 4B + Bonsai 2 9B (2026-10-28 evening)
`python3 -I bench/coresidence/coresident.py models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf models/bonsai-2-9b/Ternary-Bonsai-2-9B-Q2_0.gguf --extra -np 1 -ub 256 -b 256 --cache-ram 1024`
(`-ngl 99`, ctx 8192, 4437-token prompt with the prompt cache off, 128 generated tokens,
3 reps; 1 min 23 s in all). Output: `result-ngl99.json`.

| | VRAM | Load | Prompt tok/s | Gen tok/s |
|---|---|---|---|---|
| 4B alone | 3085 MiB | 4.3 s | 2594–2699 | 77.5–79.2 |
| Bonsai 9B alone | 2719 MiB | 9.1 s | 1641–1813 | 82.6–90.2 |
| **both loaded** | **5804 / 6144 MiB** | — | 4B 2538–2868, Bonsai 1614–1805 | 4B 74.6–82.6, Bonsai 82.6–86.0 |

- **It fits, with no slowdown**: the speeds are equal within noise, so there is no silent
  spill into system RAM. RSS is 3.0 + 2.8 GB.
- Headroom is 340 MiB. The Windows host showed 0 MiB in use. A desktop on the same GPU (the
  future native Linux PC) would take part of it.
- The bench latency per case (`verify_all` + Bonsai 9B: 12.0 s, against 7.4 s for the 4B
  alone) leaves out the swap. With both models resident, it is the real per-task latency.
- Qwen3.5-9B (5.4 GB) cannot sit next to the 4B on this GPU.
- **Not done: a co-resident mode in the harness.** It would run the same request sequence
  on each server as the two-pass mode, so the outcomes would be the same. It brings no
  measured gain for the bench.

## Context size sweep: 6k / 8k / 16k / 32k (2026-11-06)
`python3 -I bench/coresidence/ctx_sweep.py models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf models/bonsai-2-9b/Ternary-Bonsai-2-9B-Q2_0.gguf --extra -np 1 -ub 256 -b 256 --cache-ram 1024`
(`-ngl 99`, each model alone then both loaded, a prompt filling 90 % of the context, 64 generated
tokens, 2 reps, seed 42; 17 min in all, mostly model loads). Output: `result-ctx-sweep.json`,
logs in `logs-ctx/`.

Why: on novice v4 (4B + Bonsai, 8 orders, 528 cases) the largest single request is 5751
tokens (p95 4383, median 2474). Cases above 4096 tokens pass 4 % (loops), below 61 %. The
bench gives no reason to raise the context; this sweep measures what a larger one would cost.

| ctx | 4B alone | Bonsai alone | sum | both loaded (nvidia-smi) | peak while filling |
|---|---|---|---|---|---|
| 6144 | 3021 | 2653 | 5674 | 5674 | 5696 |
| 8192 | 3085 | 2719 | 5804 | 5804 | 5826 |
| 16384 | 3345 | 2979 | 6324 | 5940 | 5962 |
| 32768 | 3865 | 3499 | 7364 | 5956 | 5978 |

(MiB, GPU 6144 MiB, 0 MiB used before the run.)
- **The context is cheap: about 32 MiB per 1k tokens per model**, the same for both (linear
  from 6k to 32k). 32k costs only +780 MiB over 8k per model.
- **At 16k and 32k the pair no longer fits.** nvidia-smi stops near 5960 MiB while the sum of
  the two alone is 6324 and 7364 MiB: the excess (≈ 380 and ≈ 1400 MiB) can only be in WSL's
  shared system memory (driver sysmem fallback). Deduced from the sums, not observed directly.
  - Speed: the first request after loading slows down in co-residence (16k: 4B gen 43 vs
    53–56 tok/s alone; 32k: 4B prompt 1543 vs 2080–2167 tok/s), the second is back to normal.
    Two reps are too few to measure a steady-state cost.
  - On native Linux (the target PC) there is no such fallback: a server that does not fit
    fails to load.
- **What fits physically with both resident**: the headroom at 8k is 318 MiB (peak). At
  32 MiB/1k that is ≈ +5k tokens on each model (≈ 13k each), or ≈ +10k on the 4B alone
  (≈ 18k, checker kept at 8k). Zero margin left for a desktop on the same GPU.
- Each model alone fits at 32k (3.9 and 3.5 GB). RSS does not change with the context (3.0
  and 2.8 GB).
- Load times were 14–16 s at 6k and 36–59 s afterwards (4.3 / 9.1 s in the first co-residence
  test). Not investigated; it does not change the VRAM figures.

Verdict: **keep 8192**. No measured quality gain from a larger context on the current bench,
and with the checker resident the GPU cannot go beyond ~13k each. A larger context is only
worth it once a bench with long documents shows a gain; the cost to plan for then is ~32 MiB
per 1k tokens per model.
