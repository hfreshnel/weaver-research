#!/usr/bin/env bash
# Run the agent bench for every (model, policy) pair on GPU.
# Usage: run_matrix.sh "<model dirs>" "<policy names>" [cases.json] [runs subdir]
#   e.g. run_matrix.sh "qwen3.5-4b qwen3.5-2b" "baseline tools"
#        run_matrix.sh "qwen3.5-4b" "tools_trashq_hard" bench/agent/cases_novice.json runs-novice-v1
# Results go to llm/<model>/<runs subdir, default runs-agent-v3>/<policy>/<timestamp>/.
# SERVER_EXTRA="..." adds llama-server args to every run (e.g. "-np 1 -ub 256 -b 256 --cache-ram 1024").
# MAX_STEPS=N overrides the cases file's max_steps. NO_PROMPT_CACHE=1 passes --no-prompt-cache.
# ORDER_SEED=N shuffles the case order (noise sampling).
# VERIFY_MODEL=<model dir> runs the verify round on that model (results under <policy>+<model>);
# VERIFY_NGL=auto lets llama-server fit a verifier that does not fit in VRAM. NGL=auto idem for
# the main model (default 99: all layers on GPU).
# EMBED_MODEL=<model dir> gives the embedding model of a docs_embed policy (run on CPU before the agent).
set -u
bin=runtime/llamacpp/bin/cuda13.4-b11887
cases=${3:-bench/agent/cases.json}
sub=${4:-runs-agent-v3}
for name in $1; do
  gguf=$(ls models/"$name"/*.gguf | head -1)
  for pol in $2; do
    echo "### $name policy=$pol $(date +%T)"
    python3 -I bench/agent/run_agent.py --server-bin "$bin/llama-server" --model "$gguf" \
      --out-dir "llm/$name/$sub/$pol${VERIFY_MODEL:++$VERIFY_MODEL}" --ngl ${NGL:-99} --threads 8 --seed 42 --cases "$cases" \
      --policy "bench/agent/policies/$pol.json" ${MAX_STEPS:+--max-steps $MAX_STEPS} ${NO_PROMPT_CACHE:+--no-prompt-cache} ${ORDER_SEED:+--order-seed $ORDER_SEED} ${VERIFY_MODEL:+--verify-model $(ls models/$VERIFY_MODEL/*.gguf | head -1)} ${VERIFY_NGL:+--verify-ngl $VERIFY_NGL} ${EMBED_MODEL:+--embed-model $(ls models/$EMBED_MODEL/*.gguf | head -1)} ${SERVER_EXTRA:+--extra $SERVER_EXTRA} | grep -E '^(PASS|FAIL|RESTART|REPLAY|EMBED)'
  done
done
