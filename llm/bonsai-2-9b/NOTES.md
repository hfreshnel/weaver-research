# Bonsai 2 9B (PrismML), ternary, base Qwen3.5-9B

- File: `models/bonsai-2-9b/Ternary-Bonsai-2-9B-Q2_0.gguf`, 2.56 GB, from
  `prism-ml/Ternary-Bonsai-2-9B-gguf` (`Q2_0`, the packing that upstream llama.cpp runs).
  SHA-256 checked. Downloaded 2026-10-28 with the owner's approval.
- Why: a checker that could fit **next to** the 4B in 6 GB of VRAM. The "4B acts, 9B checks"
  configuration otherwise needs a model swap.

## Coherence check (`coherence.py`, 2026-10-28, `--ngl all`)
- **Coherent**: Canberra, 391, a clear explanation, and a clean tool call `df -h`.
- **Fast**: 79–88 tok/s generation, 145–1052 tok/s prompt.
- Memory: **2.75 GB VRAM**, 2.8 GB RSS; it loads in 9.7 s.
- The 4B (3.1 GB) plus Bonsai 2 9B (2.75 GB) = 5.85 GB of the 6 GB (6144 MiB): co-residence
  is borderline and not tested yet.
- As a checker: `runs-novice-v7-o*/verify_all+bonsai-2-9b`. On v4.4 (8 orders, `runs-novice-v8-o*`): 37.8 vs 34.5 for the 4B alone, p = 0.002; holdout +0.6 only.

## As the checker (`verify_all`, novice v4, simulator v4.3, orders 0–3, 2026-10-28)
- Outcomes 37 41 35 36, mean 37.2/66, against 33.8 for the 4B alone: +3.5, CI [+1.5, +6.0],
  p = 0.008. The Qwen3.5-9B checker gets 39.2 (+2.0 over Bonsai, not significant yet).
- Latency 12.0 s per case (Qwen 9B: 14.3 s). 2.75 GB VRAM.
- Details: `bench/agent/NOTES.md`, "Results on simulator v4.3".

## As the brain (kept policy, novice v4, v4.3, orders 0–3, 2026-10-29)
- 25 19 24 25, mean 23.2/66, against 33.8 for the 4B: −10.5, p = 0.008. **Ruled out as the
  brain.** It answers too early and repeats failed commands. Details: `bench/agent/NOTES.md`.
