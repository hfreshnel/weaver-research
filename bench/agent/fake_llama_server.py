#!/usr/bin/env -S python3 -I
"""Stand-in for llama-server in the selftest: takes the same arguments, serves mock_server.
The "model" is a JSON file {"script": ..., "cases": ...} naming the scripted turns."""
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mock_server  # noqa: E402

args = sys.argv[1:]
model = json.loads(Path(args[args.index("-m") + 1]).read_text())
mock_server.start(model["script"], model["cases"], int(args[args.index("--port") + 1]), model.get("crash_marker"))
print("fake llama-server ready", flush=True)
threading.Event().wait()
