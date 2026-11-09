# Qwen3.5-9B (Q4_K_M) — bigger-brain test

## Model
- File: `unsloth/Qwen3.5-9B-GGUF` / `Qwen3.5-9B-Q4_K_M.gguf`, 5.68 GB (vision projector not downloaded)
- sha256: `03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8` (matches HF)
- Downloaded 2026-10-26 in 131 s, after the owner granted +5 GB of budget.

## Offload probe (2026-10-26, llama.cpp b11887 CUDA 13.4, ctx 8192, 8 threads, seed 42)
One French prompt (28 tokens), 85 generated tokens, thinking off, temperature 0.

| Setting | VRAM used | RSS | Gen tok/s | Prompt tok/s |
|---|---|---|---|---|
| `-ngl auto` (`--fit` default, 1024 MiB margin) | 4155 MiB | 2.5 GB | 9.7 | 48.6 |
| `-ngl auto -fitt 256` | 4985 MiB | 1.7 GB | 23.3 | 82.0 |
| `-ngl all` | 5565 MiB | 1.1 GB | 48.7 | 145.8 |
| Qwen3.5-4B `-ngl all` (reference) | 3277 MiB | 1.0 GB | 75.1 | 137.6 |

- The whole 9B fits in the 6 GB GPU at ctx 8192 (Qwen3.5's hybrid attention keeps the KV
  cache small), so no CPU offload is needed. Margin is about 580 MiB.
- `--fit` cannot adjust `-ngl` when it is set explicitly; with `auto` it is too
  conservative here (4x slower than full offload).
- So the benches use the usual `run_matrix.sh` setting (`--ngl 99`).

## Benches
`runs-agent-v3c` and `runs-novice-v3c`, policy `tools_trashq_hard_pipes`, run together
with a fresh Qwen3.5-4B run on the same harness version.

Results (2026-10-26), see `bench/agent/NOTES.md` § "Bigger brain":
- v3: 19/26 (4B: 21/26); 3 of its failures are confirmations asked in the final answer
  instead of `ask_user`.
- novice: 10/18 outcomes (4B: 10/18), 10 full passes (4B: 8), 1 repeated call (4B: 18).
- Peak VRAM 5.6 GB, RSS 5.8 GB, load 49–56 s, novice latency 12.2 s/case (4B 9.2 s).
- **Verdict: not kept for now** (no outcome gain, higher cost). Re-test on the larger
  novice bench, where its lower looping rate might show.

## Re-test on the larger benches (2026-10-27 night)
Server settings: `-np 1 -ub 256 -b 256 --cache-ram 1024`. With the defaults, the model did
not fit (`failed to fit params`) and RSS reached 9.7 GB.
Measured: VRAM 5377 MiB, RSS 5.8 GB, load 70–130 s, 13.7–16 s per novice case (4B: 8.3–9.5 s).

| Bench | 9B | 4B | Note |
|---|---|---|---|
| v3 with chat turns (`runs-agent-v4b`) | 23/26 | 22/26 | differ on 3 cases |
| novice v4 kept (`runs-novice-v4c`) | 32/66 | 36/66 | 6 vs 10 discordant, p = 0.45 |
| novice v4.1 kept (`runs-novice-v4e`) | 33/66 | 35/66 | 6 vs 8, p = 0.79 |
| novice v4.1 `os_context` | 36/66 | 34/66 | 9 vs 7, p = 0.80 |

- Strengths:
  - far fewer loops (2–11 vs 38–74 repeated calls);
  - the only model that scans (`scan_to_pdf` 2/3);
  - holdout 16/27 with the OS line.
- Weaknesses:
  - loses `bluetooth_mouse` (0/3);
  - tries to read `/etc/*release` (`no_escape`);
  - one degenerate repetition up to max_tokens (HTTP 500, unparseable tool call).
- **Verdict: not kept.** No measurable gain over the 4B (all gaps are within the ±5-case
  noise floor), for +75 % VRAM and +70 % latency. Keep the file only if a 9B-specific test
  is planned. Otherwise it is a 5.3 GB deletion candidate.

## As the verifier of the 4B (2026-10-28, `bench/agent/NOTES.md` "Retry with verification")
- Role: one check-and-finish round after the 4B's first answer or step-budget exhaustion
  (`verify_all`, `--verify-model`). Served after the 4B in a second pass, never at the same
  time.
- Novice v4, simulator v4.2, 8 case orders: 38.0 vs 35.8/66 for the 4B alone (+2.25, 95 % CI
  [+0.4, +4.4], p = 0.039 over tasks). The same round run by the 4B gives +0.75 (noise).
- Memory: 5.8 GB RSS, 5.4 GB VRAM; it loads in about 30 s when cached.
- **Verdict: useful as a checker, not as the brain.** Deployment needs both models in
  memory, or a swap per task.
