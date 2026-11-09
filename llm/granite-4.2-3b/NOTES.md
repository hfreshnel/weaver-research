# Granite 4.2 3B (Q4_K_M) — shortlist candidate #2

## Model
- File: `ibm-granite/granite-4.2-3b-GGUF` / `granite-4.2-3b-Q4_K_M.gguf`, 2.24 GB
- sha256: `e0406663965846ae22a403456eb826ccce5f450840491f71952f18a7cb78e7d5`
- License: Apache 2.0

## Command (agent bench v2, GPU)
```
bench/agent/run_series.sh runtime/llamacpp/bin/cuda13.4-b11887 99 granite-4.2-3b
# = python3 -I bench/agent/run_agent.py --server-bin runtime/llamacpp/bin/cuda13.4-b11887/llama-server \
#     --model models/granite-4.2-3b/granite-4.2-3b-Q4_K_M.gguf --out-dir llm/granite-4.2-3b/runs-agent \
#     --ngl 99 --threads 8 --seed 42      (ctx 8192, thinking flag off)
```

## Results (2026-10-26, llama.cpp b11887 CUDA 13.4, all layers on GPU)
| Pass | Partial | Safety | Steps/ref | Latency/step | Latency/case | Load | Peak RSS | Peak VRAM delta |
|---|---|---|---|---|---|---|---|---|
| **6/16** | 0.831 | **0/3** | 0.77 | 0.78 s | 1.32 s | 19–22 s | 2484 MiB | 2857 MiB |

Two runs gave identical traces (deterministic).

## Analysis
- **Main failure: it does not act.** In 7 cases it answers in plain text in the very
  first step, and asks for information it could get with its tools ("où sont stockées
  vos factures ?", "le chemin exact de Téléchargements ?").
  - Steps/ref < 1 is the signature of this behaviour.
  - When it does call a tool (list_dir, get_system_status, web_search, open_app), the
    calls are correct. So the template and tool parsing work; the problem is the decision to act.
- It asks questions in text instead of through `ask_user` → 0/3 on safety cases.
- Reminders: it explains the ISO format instead of computing the date.
- No path escape, no repeated calls, a single tool error.

## Verdict
**Ruled out** as the agent brain: 6/16 against 13/16 for Qwen3.5-4B, with the same inputs.
It is not faster either (1.32 s/case vs 1.09 s for Qwen3.5-2B, which scores 9/16).
Possible bias: no per-model prompt tuning (same system prompt for everyone, by design).

## Weights deleted (2026-10-27)
Owner cleanup: the GGUF in `models/` was deleted (ruled out). Notes and run outputs are kept.
