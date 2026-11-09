#!/usr/bin/env python3
"""Single-turn tool-calling benchmark for a GGUF model served by llama-server.

Starts llama-server, runs every case of a cases file at temperature 0 with a
fixed seed, scores the first reply, and records latency and memory peaks.
Stdlib only: no environment to install.
"""
import argparse
import json
import os
import socket
import subprocess
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_json(url, payload=None, timeout=600):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def gpu_used_mib():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return int(out.splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


class GpuPeak(threading.Thread):
    def __init__(self, interval=0.5):
        super().__init__(daemon=True)
        self.interval, self.peak, self.stop = interval, None, threading.Event()

    def run(self):
        while not self.stop.is_set():
            v = gpu_used_mib()
            if v is not None:
                self.peak = v if self.peak is None else max(self.peak, v)
            self.stop.wait(self.interval)


def rss_peak_mib(pid):
    # VmHWM is the peak resident set size of the process.
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1]) // 1024
    return None


def match_value(value, rule):
    s = json.dumps(value, ensure_ascii=False).lower() if not isinstance(value, str) else value.lower()
    if "equals" in rule:
        return s == str(rule["equals"]).lower()
    if "contains" in rule:
        return all(k.lower() in s for k in rule["contains"])
    if "any" in rule:
        return any(k.lower() in s for k in rule["any"])
    raise ValueError(f"unknown rule {rule}")


def score(message, expects):
    calls = message.get("tool_calls") or []
    content = message.get("content") or ""
    for exp in expects:
        if exp["tool"] is None:
            rule = exp.get("content")
            if not calls and (rule is None or match_value(content, rule)):
                return True, None
            continue
        if not calls:
            continue
        fn = calls[0]["function"]
        try:
            args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
        except json.JSONDecodeError:
            return False, "invalid_json_args"
        if fn["name"] == exp["tool"] and all(
            k in args and match_value(args[k], r) for k, r in exp["args"].items()
        ):
            return True, None
    return False, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-bin", required=True, help="Path to llama-server")
    ap.add_argument("--model", required=True, help="Path to the .gguf file")
    ap.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    ap.add_argument("--out-dir", required=True, help="Run outputs go to <out-dir>/<timestamp>/")
    ap.add_argument("--ngl", type=int, default=0, help="Layers offloaded to GPU")
    ap.add_argument("--ctx", type=int, default=4096)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--think", action="store_true", help="Enable the model's thinking mode")
    ap.add_argument("--extra", nargs=argparse.REMAINDER, default=[], help="Extra llama-server args")
    a = ap.parse_args()

    spec = json.loads(Path(a.cases).read_text())
    run_dir = Path(a.out_dir) / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    port = free_port()
    cmd = [a.server_bin, "-m", a.model, "--jinja", "--port", str(port), "-c", str(a.ctx),
           "-ngl", str(a.ngl), "-t", str(a.threads), "--seed", str(a.seed), *a.extra]

    gpu_base = gpu_used_mib()
    gpu = GpuPeak()
    gpu.start()
    log = open(run_dir / "server.log", "w")
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    try:
        while True:
            if proc.poll() is not None:
                raise SystemExit(f"llama-server exited with code {proc.returncode}, see {run_dir/'server.log'}")
            try:
                if http_json(f"{base}/health", timeout=2).get("status") == "ok":
                    break
            except Exception:
                pass
            time.sleep(0.3)
        load_s = time.perf_counter() - t0

        results = []
        for case in spec["cases"]:
            body = {
                "messages": [{"role": "system", "content": spec["system"]},
                             {"role": "user", "content": case["prompt"]}],
                "tools": spec["tools"], "temperature": 0, "seed": a.seed,
                "max_tokens": a.max_tokens,
                "chat_template_kwargs": {"enable_thinking": a.think},
            }
            t = time.perf_counter()
            try:
                resp = http_json(f"{base}/v1/chat/completions", body)
                err = None
            except Exception as e:
                resp, err = None, f"{type(e).__name__}: {e}"
            dt = time.perf_counter() - t
            if resp:
                msg = resp["choices"][0]["message"]
                for c in msg.get("tool_calls") or []:
                    c.pop("id", None)  # random per call, would break run-to-run diffs
                ok, why = score(msg, case["expect"])
                timings = resp.get("timings", {})
                usage = resp.get("usage", {})
            else:
                msg, ok, why, timings, usage = None, False, err, {}, {}
            r = {"id": case["id"], "pass": ok, "fail_reason": why, "latency_s": round(dt, 2),
                 "completion_tokens": usage.get("completion_tokens"),
                 "gen_tok_s": round(timings["predicted_per_second"], 1) if "predicted_per_second" in timings else None,
                 "message": msg}
            results.append(r)
            print(f"{'PASS' if ok else 'FAIL'} {case['id']:<18} {dt:6.2f}s {r['gen_tok_s']} tok/s")
        rss = rss_peak_mib(proc.pid)
    finally:
        proc.terminate()
        proc.wait(timeout=30)
        gpu.stop.set()
        log.close()

    n_pass = sum(r["pass"] for r in results)
    lat = [r["latency_s"] for r in results]
    summary = {
        "model": os.path.basename(a.model), "cmd": cmd, "think": a.think, "seed": a.seed,
        "cases_version": spec["version"], "pass": n_pass, "total": len(results),
        "load_s": round(load_s, 1), "latency_mean_s": round(sum(lat) / len(lat), 2),
        "latency_max_s": max(lat), "rss_peak_mib": rss,
        "gpu_peak_delta_mib": (gpu.peak - gpu_base) if gpu.peak is not None and gpu_base is not None else None,
    }
    (run_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
