#!/usr/bin/env python3
"""Compare configs over several runs each (e.g. several --order-seed runs): pooled rates.

A config is LABEL=DIR[,DIR...]; each DIR is a run dir (with results.json) or a policy dir
(its latest run is used). Prints, per config, the totals per run (mean, sd, range); then,
for each pair, per-task pooled success rates and:
- a sign test over tasks whose pooled rate differs (tasks, not cases: the 3 phrasings of a
  task are not independent);
- a 95 % bootstrap interval of the difference in mean outcomes per run, resampling tasks
  (fixed seed).

A DIR ending in ":before" reads a two-model verify run as its main model alone: each case
takes its outcome before the verify round (pass 1 is identical to a plain run of the main
model, checked on 528 traces), so the paired baseline costs no extra run.

Usage: pooled.py LABEL=DIR[,DIR...] LABEL=DIR[,DIR...] [--cases-per-row]
  e.g. pooled.py base=llm/qwen3.5-4b/runs-novice-v4f-a/tools_trashq_hard_pipes,... verify=...
"""
import json
import random
import statistics
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reliability import sign_test  # noqa: E402


def load_run(d):
    d, before = (d[:-len(":before")], True) if d.endswith(":before") else (d, False)
    d = Path(d)
    if not (d / "results.json").exists():
        d = sorted(p for p in d.iterdir() if (p / "results.json").exists())[-1]
    s = json.loads((d / "summary.json").read_text())
    if s["internal_errors"] or s["llm_errors"]:
        print(f"WARNING {d}: invalid run, internal={s['internal_errors']} llm={s['llm_errors']}")
    res = {r["id"]: r for r in json.loads((d / "results.json").read_text())}
    if before:
        res = {c: {**r, "outcome": r["verify"]["outcome_before"] if r.get("verify") else r["outcome"]}
               for c, r in res.items()}
    return d, s, res


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    per_case = "--cases-per-row" in sys.argv
    configs = {}
    for arg in args:
        label, _, dirs = arg.partition("=")
        configs[label] = [load_run(d) for d in dirs.split(",")]
    first = configs[next(iter(configs))][0][2]
    tasks = defaultdict(list)
    for cid in first:
        tasks[cid.split("__")[0]].append(cid)
    split = {t: first[ids[0]]["split"] for t, ids in tasks.items()}

    print("### Per config (outcomes per run)\n")
    print("| Config | Runs | Outcomes per run | Mean | sd | Dev mean | Holdout mean | Latency/case | Data loss |")
    print("|---|---|---|---|---|---|---|---|---|")
    rate = {}
    for label, runs in configs.items():
        tot = [sum(r["outcome"] for r in res.values()) for _, _, res in runs]
        dev = [sum(r["outcome"] for r in res.values() if r["split"] == "dev") for _, _, res in runs]
        hold = [sum(r["outcome"] for r in res.values() if r["split"] == "holdout") for _, _, res in runs]
        lat = statistics.mean(s["latency_case_mean_s"] for _, s, _ in runs)
        loss = sum(s["cases_with_data_loss"] for _, s, _ in runs)
        sd = statistics.stdev(tot) if len(tot) > 1 else 0.0
        print(f"| {label} | {len(runs)} | {' '.join(map(str, tot))} | {statistics.mean(tot):.1f} | {sd:.1f} | "
              f"{statistics.mean(dev):.1f} | {statistics.mean(hold):.1f} | {lat:.1f} s | {loss} |")
        rate[label] = {c: sum(res[c]["outcome"] for _, _, res in runs) / len(runs) for c in first}
        vs = [s for _, s, _ in runs if "verify_rounds" in s]
        if vs:
            print(f"|  ↳ verify | | rounds {sum(s['verify_rounds'] for s in vs)}, fixed {sum(s['verify_fixed'] for s in vs)}, "
                  f"broke {sum(s['verify_broke'] for s in vs)}, steps after {statistics.mean(s['verify_steps_mean'] for s in vs):.1f} | | | | | | |")
    labels = list(configs)

    print("\n### Per task (pooled share of phrasings × runs reached)\n")
    print("| Task | Split | " + " | ".join(labels) + " |")
    print("|---|---|" + "---|" * len(labels))
    for t, ids in tasks.items():
        print(f"| {t} | {split[t]} | " + " | ".join(f"{statistics.mean(rate[n][c] for c in ids):.2f}" for n in labels) + " |")
        if per_case:
            for c in ids:
                print(f"|  {c} | | " + " | ".join(f"{rate[n][c]:.2f}" for n in labels) + " |")

    rng = random.Random(0)
    print("\n### Paired comparisons (A − B)\n")
    print("| A | B | Δ mean outcomes/run | 95 % CI (task bootstrap) | Δ holdout | Tasks A better / B better | p (sign, tasks) |")
    print("|---|---|---|---|---|---|---|")
    for a, b in combinations(labels, 2):
        dtask = {t: sum(rate[a][c] - rate[b][c] for c in ids) for t, ids in tasks.items()}
        names = list(dtask)
        boot = sorted(sum(dtask[rng.choice(names)] for _ in names) for _ in range(10000))
        lo, hi = boot[249], boot[9749]
        dh = sum(v for t, v in dtask.items() if split[t] == "holdout")
        wa, wb = sum(v > 1e-9 for v in dtask.values()), sum(v < -1e-9 for v in dtask.values())
        print(f"| {a} | {b} | {sum(dtask.values()):+.2f} | [{lo:+.1f}, {hi:+.1f}] | {dh:+.2f} | {wa} / {wb} | {sign_test(wa, wb):.3f} |")


if __name__ == "__main__":
    main()
