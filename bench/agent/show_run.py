#!/usr/bin/env python3
"""Print a per-case digest of an agent bench run: status, failed checks, tool trace, answer."""
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
only = set(sys.argv[2:])
for r in json.loads((run_dir / "results.json").read_text()):
    if only and r["id"] not in only:
        continue
    print(f"== {'PASS' if r['pass'] else 'FAIL'} {r['id']} score={r['score']} steps={r['n_steps']}/{r['ref_steps']} "
          f"term={r['termination']} failed={r['failed_checks']} {r['latency_total_s']}s")
    for s in r["steps"]:
        for c in s["tool_calls"]:
            print(f"   {c['name']} {json.dumps(c['args'], ensure_ascii=False)} -> {c['result'][:140]!r}")
    print(f"   answer: {(r['answer'] or '')[:200]!r}")
