#!/usr/bin/env bash
# Night 2026-11-06: Ornith-1.5-9B brain alone, orders 4..7, on a frozen copy of the v4.4 bench
# (so simulator edits in bench/agent cannot leak into these runs). Same args as run_matrix.sh.
set -u
cd "$(dirname "$0")/../.."
F=bench/agent-v44-frozen
for N in 4 5 6 7; do
  echo "### ornith order $N $(date +%T)"
  python3 -I $F/run_agent.py --server-bin runtime/llamacpp/bin/cuda13.4-b11887/llama-server \
    --model models/ornith-1.5-9b/Ornith-1.5-9B-Q4_K_M.gguf \
    --out-dir llm/ornith-1.5-9b/runs-novice-v8-o$N/tools_trashq_hard_pipes --ngl 99 --threads 8 --seed 42 \
    --cases $F/cases_novice_v4.json --policy $F/policies/tools_trashq_hard_pipes.json --order-seed $N \
    --extra -np 1 -ub 256 -b 256 --cache-ram 1024 | grep -E '^(PASS|FAIL|RESTART|REPLAY)' | wc -l
  echo "### done order $N $(date +%T)"
done
