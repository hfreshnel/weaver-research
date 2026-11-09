#!/usr/bin/env python3
"""Markdown table of the latest run for each (model, policy) under llm/<model>/<runs_subdir>/<policy>/.

Usage: compare.py <runs_subdir> <model>...   e.g. compare.py runs-agent-v3 qwen3.5-4b qwen3.5-2b
"""
import json
import sys
from pathlib import Path

sub, models = sys.argv[1], sys.argv[2:]
print("| Model | Policy | Outcome (dev/holdout) | Dev pass | Holdout pass | Partial (dev/holdout) | Safety (all) | Unconsented loss | Any loss | Blocked | Repeated | Think steps | Latency/case |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for m in models:
    for pol_dir in sorted(Path("llm", m, sub).iterdir()):
        runs = sorted(p for p in pol_dir.iterdir() if (p / "summary.json").exists())
        if not runs:
            continue
        s = json.loads((runs[-1] / "summary.json").read_text())
        d, h = s["by_split"]["dev"], s["by_split"]["holdout"]
        oc = f"{d.get('outcome', '?')}/{d['total']} · {h.get('outcome', '?')}/{h['total']}"
        print(f"| {m} | {pol_dir.name} | {oc} | {d['pass']}/{d['total']} | {h['pass']}/{h['total']} | "
              f"{d['partial_score_mean']:.3f} / {h['partial_score_mean']:.3f} | {s['safety_success_rate']:.2f} | "
              f"{s.get('cases_with_unconsented_loss', '?')} | {s.get('cases_with_data_loss', '?')} | {s.get('blocked_actions', '?')} | "
              f"{s['repeated_calls']} | {s['think_steps']} | {s['latency_case_mean_s']} s |")
