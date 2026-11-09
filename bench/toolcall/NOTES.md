# Bench: single-turn tool calling

The same fixed inputs for every LLM candidate: `cases.json` (versioned through the
`version` field). It has 8 OS-style tools (files, shell, apps, reminders, system
metrics, web) and 10 FR/EN prompts, including one that needs no tool.

## Scoring
- The first reply must call the expected tool with arguments that match the rules
  (`equals` / `contains` / `any`, case-insensitive). Several valid answers are allowed
  per case.
- Settings: temperature 0, fixed seed, thinking off by default (`--think` to compare).
- Measured: pass rate, latency per case, generation speed (tok/s), model load time,
  peak RSS of llama-server (`VmHWM`), peak GPU memory delta (polling `nvidia-smi`).

## Usage
```
python3 -I bench/toolcall/run_toolcall.py --server-bin <llama-server> --model <file.gguf> \
  --out-dir llm/<name>/runs [--ngl N] [--threads 8] [--seed 42] [--think] [--extra <server args>]
```
Outputs go to `<out-dir>/<timestamp>/{summary.json,results.json,server.log}` (gitignored).

## History
- v1 (2026-10-25): Qwen3.5-2B on CPU gets 9/10 (see `llm/qwen3.5-2b/NOTES.md`).
  **Too easy** to tell 4B-class models apart. Superseded by the multi-turn bench in
  `bench/agent/` (v2). It is kept frozen as a quick smoke test.
