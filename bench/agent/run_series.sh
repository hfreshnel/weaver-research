#!/usr/bin/env bash
# Run the agent bench on several models in sequence. Usage: run_series.sh <bin_dir> <ngl> <model_dir>...
# Each model dir must hold one .gguf; results go to llm/<name>/runs-agent/.
set -u
bin=$1; ngl=$2; shift 2
for m in "$@"; do
  name=$(basename "$m"); gguf=$(ls models/"$name"/*.gguf | head -1)
  echo "### $name ngl=$ngl $(date +%T)"
  /usr/bin/time -f "### $name wall=%es maxrss_client=%MKB" \
    python3 -I bench/agent/run_agent.py --server-bin "$bin/llama-server" --model "$gguf" \
      --out-dir "llm/$name/runs-agent" --ngl "$ngl" --threads 8 --seed 42 | grep -E '^(PASS|FAIL)|"(pass|success_rate|partial_score_mean|safety_success_rate|steps_over_ref_mean|repeated_calls|tool_errors|latency_per_step_mean_s|latency_case_mean_s|load_s|rss_peak_mib|gpu_peak_delta_mib|wall_s)"'
done
