#!/usr/bin/env python3
"""Reliability over phrasings (novice v4): per task, per skill tag, and paired sign tests.

A case id is <task> or <task>__p<i>; a task's reliability is the share of its phrasings
whose outcome was reached. Uses the latest run of each (model, policy).

Usage: reliability.py <runs_subdir> <model>[/<policy>]...
  e.g. reliability.py runs-novice-v4 qwen3.5-4b qwen3.5-9b/docs_err
"""
import json
import sys
from collections import defaultdict
from itertools import combinations
from math import comb
from pathlib import Path


def latest_runs(sub, label):
    model, _, pol = label.partition("/")
    for pol_dir in sorted(Path("llm", model, sub).iterdir()):
        if pol and pol_dir.name != pol:
            continue
        runs = sorted(p for p in pol_dir.iterdir() if (p / "results.json").exists())
        if runs:
            yield f"{model}/{pol_dir.name}", runs[-1]


def sign_test(wins, losses):
    """Exact two-sided binomial test on discordant pairs (p = 0.5)."""
    n, k = wins + losses, min(wins, losses)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def main():
    sub, labels = sys.argv[1], sys.argv[2:]
    configs = {}
    for label in labels:
        for name, run in latest_runs(sub, label):
            s = json.loads((run / "summary.json").read_text())
            if s["internal_errors"] or s["llm_errors"]:
                print(f"WARNING {name} ({run.name}): invalid run, internal={s['internal_errors']} llm={s['llm_errors']}")
            configs[name] = {r["id"]: r for r in json.loads((run / "results.json").read_text())}
    names = list(configs)
    first = configs[names[0]]
    tasks = defaultdict(list)
    for cid, r in first.items():
        tasks[cid.split("__")[0]].append(cid)

    print("### Summary\n")
    print("| Config | Outcomes (all) | Dev | Holdout | Tasks 3/3 | Tasks ≥1/3 | Tasks 0/3 |")
    print("|---|---|---|---|---|---|---|")
    for n in names:
        res = configs[n]
        dev = [r for r in res.values() if r["split"] == "dev"]
        hold = [r for r in res.values() if r["split"] == "holdout"]
        per_task = [sum(res[c]["outcome"] for c in ids) for ids in tasks.values()]
        full = sum(k == len(ids) for k, ids in zip(per_task, tasks.values()))
        print(f"| {n} | {sum(r['outcome'] for r in res.values())}/{len(res)} | "
              f"{sum(r['outcome'] for r in dev)}/{len(dev)} | {sum(r['outcome'] for r in hold)}/{len(hold)} | "
              f"{full}/{len(tasks)} | {sum(k > 0 for k in per_task)}/{len(tasks)} | {sum(k == 0 for k in per_task)}/{len(tasks)} |")

    print("\n### Per task (phrasings reached: p0 p1 p2)\n")
    print("| Task | Split | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    for t, ids in tasks.items():
        cells = []
        for n in names:
            marks = "".join("●" if configs[n][c]["outcome"] else "·" for c in ids)
            cells.append(f"{marks} {sum(configs[n][c]['outcome'] for c in ids)}/{len(ids)}")
        print(f"| {t} | {first[ids[0]]['split']} | " + " | ".join(cells) + " |")

    print("\n### Per skill tag (share of cases reached)\n")
    tags = sorted({tag for r in first.values() for tag in r["tags"]})
    print("| Tag | Cases | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    for tag in tags:
        ids = [c for c, r in first.items() if tag in r["tags"]]
        print(f"| {tag} | {len(ids)} | " + " | ".join(
            f"{sum(configs[n][c]['outcome'] for c in ids) / len(ids):.2f}" for n in names) + " |")

    print("\n### Per phrasing axis (p0 v3 wording, p1 terse, p2 verbose)\n")
    print("| Phrasing | " + " | ".join(names) + " |")
    print("|---|" + "---|" * len(names))
    for i in range(3):
        ids = [c for c in first if (c.split("__p")[1] if "__p" in c else "0") == str(i)]
        print(f"| p{i} | " + " | ".join(f"{sum(configs[n][c]['outcome'] for c in ids)}/{len(ids)}" for n in names) + " |")

    if len(names) > 1:
        print("\n### Paired comparison on outcomes (sign test on discordant cases)\n")
        print("| A | B | A only | B only | p (two-sided) |")
        print("|---|---|---|---|---|")
        for a, b in combinations(names, 2):
            wa = sum(configs[a][c]["outcome"] and not configs[b][c]["outcome"] for c in first)
            wb = sum(configs[b][c]["outcome"] and not configs[a][c]["outcome"] for c in first)
            print(f"| {a} | {b} | {wa} | {wb} | {sign_test(wa, wb):.3f} |")


if __name__ == "__main__":
    main()
