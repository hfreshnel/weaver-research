#!/usr/bin/env python3
"""Can two models stay loaded together on the GPU without slowing down? Measures each model
alone, then both servers loaded at once: VRAM, load time, prompt and generation speed on a
fixed agent-sized prompt (temperature 0, fixed seed). On WSL the driver may spill VRAM into
system RAM silently, so speed is the real check, not only whether both servers start.

Usage: coresident.py <main.gguf> <checker.gguf> [--ngl 99] [--prompt-tokens 3500] [--reps 3]
                     [--extra ...llama-server args]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench" / "lib"))
from llama import LlamaServer, gpu_used_mib, http_json  # noqa: E402

BIN = str(ROOT / "runtime/llamacpp/bin/cuda13.4-b11887/llama-server")
PARA = ("L'utilisateur demande de l'aide pour son ordinateur. L'assistant lit l'état du système, "
        "choisit une commande sûre, vérifie le résultat et répond en français simple. ")


def measure(srv, n_tokens, reps, seed):
    """Fresh prompt each rep (a rep number up front defeats the prompt cache)."""
    out = []
    for i in range(reps):
        body = {"messages": [{"role": "system", "content": f"[{i}] " + PARA * (n_tokens // 30)},
                             {"role": "user", "content": "Résume la consigne en trois phrases."}],
                "temperature": 0, "seed": seed, "max_tokens": 128, "cache_prompt": False,
                "chat_template_kwargs": {"enable_thinking": False}}
        t = time.perf_counter()
        r = http_json(f"{srv.base_url}/v1/chat/completions", body)
        tm = r.get("timings", {})
        out.append({"wall_s": round(time.perf_counter() - t, 2), "prompt_n": tm.get("prompt_n"),
                    "prompt_tps": round(tm.get("prompt_per_second", 0)), "gen_tps": round(tm.get("predicted_per_second", 0), 1)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("main")
    ap.add_argument("checker")
    ap.add_argument("--ngl", default="99")
    ap.add_argument("--prompt-tokens", type=int, default=3500)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--extra", nargs=argparse.REMAINDER, default=[])
    a = ap.parse_args()
    here = Path(__file__).parent
    res = {"base_gpu_mib": gpu_used_mib()}
    srv = lambda m, tag: LlamaServer(BIN, m, here / f"server-{tag}.log", a.ngl, 8192, 8, a.seed, a.extra)
    for tag, model in (("main", a.main), ("checker", a.checker)):
        with srv(model, tag) as s:
            res[f"{tag}_alone"] = {"load_s": s.load_s, "gpu_mib": gpu_used_mib(),
                                   "runs": measure(s, a.prompt_tokens, a.reps, a.seed)}
    with srv(a.main, "main-co") as m, srv(a.checker, "checker-co") as c:
        res["both_loaded_gpu_mib"] = gpu_used_mib()
        res["main_co"] = {"load_s": m.load_s, "runs": measure(m, a.prompt_tokens, a.reps, a.seed)}
        res["checker_co"] = {"load_s": c.load_s, "runs": measure(c, a.prompt_tokens, a.reps, a.seed)}
        res["main_co_again"] = {"runs": measure(m, a.prompt_tokens, a.reps, a.seed)}
    res["rss_mib"] = {"main_co": m.rss_peak_mib, "checker_co": c.rss_peak_mib}
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
