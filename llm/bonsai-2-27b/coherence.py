#!/usr/bin/env python3
"""Coherence check of a GGUF before any bench: a few fixed prompts (French, arithmetic, an
instruction, one tool call), temperature 0, fixed seed. Prints answers, speed and memory.
Catches a model that loads but outputs gibberish (seen with ternary formats on old builds).

Usage: coherence.py <gguf> [--ngl auto] [--extra ...llama-server args]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench" / "lib"))
from llama import LlamaServer, http_json  # noqa: E402

TOOL = {"type": "function", "function": {
    "name": "run_shell", "description": "Run one shell command on the user's Linux computer.",
    "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}}
PROMPTS = [
    ("fr_fact", "Quelle est la capitale de l'Australie ? Réponds en une phrase.", False),
    ("arith", "Combien font 17 × 23 ? Donne seulement le nombre.", False),
    ("instruction", "Explique en deux phrases simples, pour une personne âgée, ce qu'est une mise à jour du système.", False),
    ("tool_call", "Combien d'espace disque reste-t-il sur mon ordinateur ?", True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--ngl", default="auto")
    ap.add_argument("--ctx", type=int, default=8192)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--extra", nargs=argparse.REMAINDER, default=[])
    a = ap.parse_args()
    log = Path(__file__).with_name("coherence-server.log")
    with LlamaServer(str(ROOT / "runtime/llamacpp/bin/cuda13.4-b11887/llama-server"), a.model, log,
                     a.ngl, a.ctx, 8, a.seed, a.extra) as srv:
        for name, prompt, tools in PROMPTS:
            body = {"messages": [{"role": "user", "content": prompt}], "temperature": 0, "seed": a.seed,
                    "max_tokens": 300, "chat_template_kwargs": {"enable_thinking": False}}
            if tools:
                body["tools"] = [TOOL]
            t = time.perf_counter()
            r = http_json(f"{srv.base_url}/v1/chat/completions", body)
            dt = time.perf_counter() - t
            msg, u, tm = r["choices"][0]["message"], r.get("usage", {}), r.get("timings", {})
            out = msg.get("content") or json.dumps(msg.get("tool_calls"), ensure_ascii=False)
            print(f"## {name} ({dt:.1f} s, prompt {tm.get('prompt_per_second', 0):.0f} tok/s, "
                  f"gen {tm.get('predicted_per_second', 0):.1f} tok/s, {u.get('completion_tokens')} tokens)\n{out}\n")
    print(f"load {srv.load_s} s, RSS peak {srv.rss_peak_mib} MiB, GPU peak delta {srv.gpu_peak_delta_mib} MiB")
    offload = [l.strip() for l in log.read_text(errors="replace").splitlines() if "offloaded" in l or "fit" in l.lower()][:6]
    print("\n".join(offload))


if __name__ == "__main__":
    main()
