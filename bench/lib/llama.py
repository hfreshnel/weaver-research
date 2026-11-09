"""Shared helpers: start/stop llama-server, call it, and track memory peaks. Stdlib only."""
import json
import socket
import subprocess
import threading
import time
import urllib.request
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


class LlamaServer:
    """Context manager running llama-server; exposes base_url, load_s and memory peaks."""

    def __init__(self, server_bin, model, log_path, ngl=0, ctx=8192, threads=8, seed=42, extra=()):
        self.port = free_port()
        self.cmd = [server_bin, "-m", model, "--jinja", "--port", str(self.port), "-c", str(ctx),
                    "-ngl", str(ngl), "-t", str(threads), "--seed", str(seed), *extra]
        self.log_path = log_path
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.load_s = self.rss_peak_mib = self.gpu_peak_delta_mib = None

    def __enter__(self):
        self.gpu_base = gpu_used_mib()
        self.gpu = GpuPeak()
        self.gpu.start()
        self.log = open(self.log_path, "w")
        self.restarts = 0
        self._start()
        return self

    def alive(self):
        return self.proc.poll() is None

    def healthy(self, wait=10):
        """False if the server died or stopped answering. A crashing server can still be alive
        for a few seconds (writing its backtrace) after it dropped the connection."""
        try:
            self.proc.wait(timeout=wait)
            return False
        except subprocess.TimeoutExpired:
            pass
        try:
            return http_json(f"{self.base_url}/health", timeout=5).get("status") == "ok"
        except Exception:
            return False

    def restart(self):
        """Start the server again after a crash (same command, same log file)."""
        if self.alive():
            self.proc.terminate()
            self.proc.wait(timeout=30)
        self.restarts += 1
        self.log.write(f"\n=== weaver: server restart {self.restarts} ===\n")
        self.log.flush()
        load_s = self.load_s
        self._start()
        self.load_s = load_s  # keep the first load time

    def _start(self):
        t0 = time.perf_counter()
        self.proc = subprocess.Popen(self.cmd, stdout=self.log, stderr=subprocess.STDOUT)
        while True:
            if self.proc.poll() is not None:
                raise SystemExit(f"llama-server exited with code {self.proc.returncode}, see {self.log_path}")
            try:
                if http_json(f"{self.base_url}/health", timeout=2).get("status") == "ok":
                    break
            except Exception:
                pass
            time.sleep(0.3)
        self.load_s = round(time.perf_counter() - t0, 1)

    def __exit__(self, *exc):
        try:
            self.rss_peak_mib = rss_peak_mib(self.proc.pid)
        except OSError:
            pass
        self.proc.terminate()
        self.proc.wait(timeout=30)
        self.gpu.stop.set()
        self.log.close()
        if self.gpu.peak is not None and self.gpu_base is not None:
            self.gpu_peak_delta_mib = self.gpu.peak - self.gpu_base
