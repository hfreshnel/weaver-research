#!/usr/bin/env python3
"""OpenAI-compatible mock that replays scripted agent turns, to test the bench harness
without a model. The case is found from the user prompt, the turn from the number of
assistant messages already in the conversation.

Script format: {case_id: [{"tool_calls": [[name, {args}], ...]} | {"content": "..."}
                          | {"http_error": code, "body": "..."}, ...]}
A turn with "crash_once": true kills the process without answering, the first time only
(crash_marker: a file recording that the crash happened, so a restarted server goes on).
"""
import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FALLBACK = {"content": "Je ne sais pas."}


def make_handler(script, prompt_to_id, crash_marker=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, obj):
            data = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send({"status": "ok"})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            msgs = body["messages"]
            user = next(m["content"] for m in msgs if m["role"] == "user")
            turn = sum(m["role"] == "assistant" for m in msgs)
            turns = script.get(prompt_to_id.get(user), [])
            t = turns[turn] if turn < len(turns) else FALLBACK
            if t.get("crash_once") and crash_marker and not Path(crash_marker).exists():
                Path(crash_marker).write_text("crashed")
                os._exit(1)  # like llama-server's CUDA abort: the connection drops
            if "http_error" in t:
                data = t.get("body", "").encode()
                self.send_response(t["http_error"])
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            msg = {"role": "assistant", "content": t.get("content", "")}
            if "tool_calls" in t:
                msg["tool_calls"] = [
                    {"id": f"call_{turn}_{k}", "type": "function",
                     "function": {"name": n, "arguments": json.dumps(args, ensure_ascii=False)}}
                    for k, (n, args) in enumerate(t["tool_calls"])]
            self._send({"choices": [{"message": msg, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0}})

    return Handler


def start(script_path, cases_path, port=0, crash_marker=None):
    script = json.loads(Path(script_path).read_text())
    cases = json.loads(Path(cases_path).read_text())["cases"]
    prompt_to_id = {c["prompt"]: c["id"] for c in cases}
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(script, prompt_to_id, crash_marker))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    ap.add_argument("--port", type=int, default=8099)
    a = ap.parse_args()
    srv = start(a.script, a.cases, a.port)
    print(f"mock server on http://127.0.0.1:{srv.server_port}")
    threading.Event().wait()
