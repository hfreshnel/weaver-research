#!/usr/bin/env bash
# Re-baseline on simulator v4.5 (2026-11-06 night): the adopted pipeline (4B acts, Bonsai 2 9B
# checks, verify_all), orders 0..7. Pass 1 of each run is the 4B alone (pooled.py DIR:before).
# Waits for the Ornith night runs (same GPU) to finish first.
set -u
cd "$(dirname "$0")/../.."
while pgrep -f run_ornith_night.sh > /dev/null; do sleep 30; done
echo "### start $(date +%T)"
python3 -I bench/agent/selftest.py | tail -1
for N in 0 1 2 3 4 5 6 7; do
  echo "### order $N $(date +%T)"
  ORDER_SEED=$N VERIFY_MODEL=bonsai-2-9b SERVER_EXTRA="-np 1 -ub 256 -b 256 --cache-ram 1024" \
    bench/agent/run_matrix.sh "qwen3.5-4b" "verify_all" bench/agent/cases_novice_v4.json runs-novice-v9-o$N | wc -l
done
echo "### end $(date +%T)"
