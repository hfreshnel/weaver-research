# Bonsai 2 27B (PrismML), ternary, base Qwen3.8-27B

- **Weights deleted on 2026-10-30 (night, owner's yes): 7.63 GB refunded to the budget.**
  `expected.sha256` is kept to check a re-download.
- File: `models/bonsai-2-27b/Ternary-Bonsai-2-27B-Q2_0.gguf`, 7.63 GB, from
  `prism-ml/Ternary-Bonsai-2-27B-gguf-dev` (upstream file name
  `…-Q2_0-prism-fork-required.gguf`). SHA-256 checked against the Hugging Face LFS oid
  (`expected.sha256`). Downloaded 2026-10-28 with the owner's approval.
- Runtime: llama.cpp b11887 CUDA (upstream). PrismML documents upstream support for `Q2_0`
  from b11555.

## Coherence check (`coherence.py`, 2026-10-28)
`python3 -I llm/bonsai-2-27b/coherence.py models/bonsai-2-27b/Ternary-Bonsai-2-27B-Q2_0.gguf --extra -np 1 -ub 256 -b 256 --cache-ram 1024`
(`-ngl auto`, with `--fit` on by default)
- **Coherent, no gibberish** (the HF card's warning does not apply to b11887):
  - Canberra correct;
  - 17 × 23 = 391;
  - a clear two-sentence explanation of a system update for an elderly person;
  - a clean tool call `df -h /`.
- Memory: 4.2 GB VRAM (the fit puts part of the layers in RAM), 7.7 GB RSS. It loads in
  28–42 s.

## Speed (agent-like prompt of 3769 tokens, then a 24-token follow-up)
| Setting | First step | Prompt speed | Follow-up step | Generation |
|---|---|---|---|---|
| `-ub 256 -b 256` | 28.3 s | 212 tok/s | 13.7 s | 3.5–3.8 tok/s |
| `-ub 1024 -b 1024` | 22.7 s | 334 tok/s | 13.9 s | 3.4–3.5 tok/s |
| `--no-op-offload` | 551.9 s | 7 tok/s | 12.5 s | 3.9–4.0 tok/s |

- Every request pays about 5 s of fixed cost: small batches of the RAM-resident layers run
  on the CPU at about 5 tok/s.
- Generation runs at 3.5–4.5 tok/s.
- `--no-op-offload` is unusable.
- Estimate: a 4-step verify round takes about 1.5 min, and a novice v4 run with 52 rounds
  about 1 h 40.
- **Too slow as the brain on this machine** (every step pays it). As a checker, it is
  measured over 4 orders in `runs-novice-v7-o*`.

## As the checker (`verify_all`, novice v4, simulator v4.3, 2026-10-28)
- Order 0 only: 38/66, against 41 for the Qwen3.5-9B checker and 33 for the 4B alone.
  Order 1 was interrupted (killed by a double Ctrl-C at 14:09, not a crash).
- Rounds: 42 of 52 used the full 12-step budget, read-only exploration of `/proc` and
  `/usr/bin`. Latency 132.6 s per case, 2 h 28 per run. Memory: 4.3 GB VRAM, 8.6 GB RSS.
