#!/usr/bin/env python3
"""VRAM cost of the context size, with the main model and the checker loaded together.
For each context size: each model alone, then both loaded. VRAM after load, peak VRAM while
a prompt fills ~90 % of the context, prompt and generation speed (a co-resident speed drop
against the same model alone means a silent spill into system RAM on WSL).

Usage: ctx_sweep.py <main.gguf> <checker.gguf> [--ctx 6144 8192 16384 32768] [--fill 0.9]
                    [--reps 2] [--seed 42] [--extra ...llama-server args]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench" / "lib"))
from llama import GpuPeak, LlamaServer, gpu_used_mib, http_json  # noqa: E402

BIN = str(ROOT / "runtime/llamacpp/bin/cuda13.4-b11887/llama-server")
PARA = ("L'utilisateur demande de l'aide pour son ordinateur. L'assistant lit l'état du système, "
        "choisit une commande sûre, vérifie le résultat et répond en français simple. ")


def fill(srv, ctx, frac, reps, seed):
    """Prompt sized to frac * ctx tokens (calibrated with /tokenize); fresh prompt each rep."""
    per = len(http_json(f"{srv.base_url}/tokenize", {"content": PARA})["tokens"])
    n_rep = max(1, int(ctx * frac) // per)
    out = []
    for i in range(reps):
        body = {"messages": [{"role": "system", "content": f"[{i}] " + PARA * n_rep},
                             {"role": "user", "content": "Résume la consigne en trois phrases."}],
                "temperature": 0, "seed": seed, "max_tokens": 64, "cache_prompt": False,
                "chat_template_kwargs": {"enable_thinking": False}}
        t = time.perf_counter()
        try:
            r = http_json(f"{srv.base_url}/v1/chat/completions", body)
        except Exception as e:  # context overflow or server crash: record, go on
            out.append({"error": str(e)[:200]})
            continue
        tm = r.get("timings", {})
        out.append({"wall_s": round(time.perf_counter() - t, 2), "prompt_n": tm.get("prompt_n"),
                    "prompt_tps": round(tm.get("prompt_per_second", 0)),
                    "gen_tps": round(tm.get("predicted_per_second", 0), 1)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("main")
    ap.add_argument("checker")
    ap.add_argument("--ctx", type=int, nargs="+", default=[6144, 8192, 16384, 32768])
    ap.add_argument("--fill", type=float, default=0.9)
    ap.add_argument("--ngl", default="99")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--extra", nargs=argparse.REMAINDER, default=[])
    a = ap.parse_args()
    logs = Path(__file__).parent / "logs-ctx"
    logs.mkdir(exist_ok=True)
    res = {"base_gpu_mib": gpu_used_mib(), "total_mib": 6144, "sizes": {}}
    for ctx in a.ctx:
        srv = lambda m, tag: LlamaServer(BIN, m, logs / f"{tag}-{ctx}.log", a.ngl, ctx, 8, a.seed, a.extra)
        row = {}
        try:
            for tag, model in (("main", a.main), ("checker", a.checker)):
                peak = GpuPeak(0.2)
                with srv(model, tag) as s:
                    loaded = gpu_used_mib()
                    peak.start()
                    runs = fill(s, ctx, a.fill, a.reps, a.seed)
                    peak.stop.set()
                row[f"{tag}_alone"] = {"gpu_loaded_mib": loaded, "gpu_peak_mib": peak.peak,
                                       "load_s": s.load_s, "rss_mib": s.rss_peak_mib, "runs": runs}
            peak = GpuPeak(0.2)
            with srv(a.main, "main-co") as m, srv(a.checker, "checker-co") as c:
                row["both_loaded_mib"] = gpu_used_mib()
                peak.start()
                row["main_co"] = fill(m, ctx, a.fill, a.reps, a.seed)
                row["checker_co"] = fill(c, ctx, a.fill, a.reps, a.seed)
                peak.stop.set()
            row["both_peak_mib"] = peak.peak
            row["rss_co_mib"] = {"main": m.rss_peak_mib, "checker": c.rss_peak_mib}
        except SystemExit as e:  # a server refused to start (e.g. out of VRAM)
            row["error"] = str(e)
        res["sizes"][ctx] = row
        print(json.dumps({ctx: row}), flush=True)
    out = Path(__file__).parent / "result-ctx-sweep.json"
    out.write_text(json.dumps(res, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
