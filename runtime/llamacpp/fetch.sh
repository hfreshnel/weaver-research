#!/usr/bin/env bash
# Fetch the llama.cpp b11887 prebuilt binaries into runtime/llamacpp/bin/ (gitignored).
# Usage: runtime/llamacpp/fetch.sh [cpu|cuda|all]   (default: all)
# Commands are the ones recorded in NOTES.md. SHA-256 of the archives: see NOTES.md.
set -euo pipefail
what="${1:-all}"
B=b11887
URL=https://github.com/ggml-org/llama.cpp/releases/download/$B
cd "$(dirname "$0")" && mkdir -p bin && cd bin

if [[ $what == cpu || $what == all ]] && [[ ! -d cpu-$B ]]; then
  curl -fsSL -o llama-cpu.tar.gz $URL/llama-$B-bin-ubuntu-x64.tar.gz
  tar xzf llama-cpu.tar.gz && mv llama-$B cpu-$B && rm llama-cpu.tar.gz
fi

if [[ $what == cuda || $what == all ]] && [[ ! -d cuda13.4-$B ]]; then
  mkdir -p cuda13.4-$B
  for f in llama-$B-bin-ubuntu-cuda-13.4-x64.tar.gz cudart-llama-$B-bin-ubuntu-cuda-13.4-x64.tar.gz; do
    curl -fsSL -o "$f" "$URL/$f" && tar xzf "$f" -C cuda13.4-$B && rm "$f"
  done
  # flatten: the cudart libs must sit next to llama-server
  cd cuda13.4-$B && mv cudart-*/* llama-$B/ && rmdir cudart-* && mv llama-$B/* . && rmdir llama-$B
fi
