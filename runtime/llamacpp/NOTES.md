# llama.cpp — inference runtime

## Why this runtime
- Prebuilt binaries: nothing to compile, no global install (no cmake or nvcc on this machine).
- GGUF format: the widest choice of quantized models (Q4/Q5/Q8), with fine control
  of CPU/GPU offload (`-ngl`, `--n-cpu-moe`).
- `llama-server` exposes an OpenAI-compatible API with native tool calling (`--jinja`)
  and multimodal input (`--mmproj`). It is the same interface for every candidate.
- Ollama and LM Studio are wrappers around the same engine: they add no quality and
  add a layer. Ruled out unless a measured gain (e.g. model swap time) shows up.
- vLLM / SGLang: designed for multi-user throughput with VRAM pre-allocation. Too heavy
  for 6 GB and a single user. Ruled out.

## Installed builds
| Build | File | Size | Use |
|---|---|---|---|
| b11887 CPU | `llama-b11887-bin-ubuntu-x64.tar.gz` (sha256 `5e5e9c72…6d5c`) | 22.5 MB | smoke tests |
| b11887 CUDA 13.4 | `llama-b11887-bin-ubuntu-cuda-13.4-x64.tar.gz` (sha256 `52796ff0…0a54`) + `cudart-llama-b11887-bin-ubuntu-cuda-13.4-x64.tar.gz` (sha256 `c73b4143…ae91`) | 164 + 440 MB download, 793 MB on disk | GPU runs |

The CUDA 13.4 build works with driver 592.82 (Windows side, WSL2) and needs no toolkit.
Verified 2026-10-26 with `llama-server --list-devices`:
`CUDA0: NVIDIA GeForce RTX 3060 Laptop GPU (6143 MiB, 5118 MiB free)`.

## Fetch command (CUDA)
```
cd runtime/llamacpp/bin && mkdir -p cuda13.4-b11887
for f in llama-b11887-bin-ubuntu-cuda-13.4-x64.tar.gz cudart-llama-b11887-bin-ubuntu-cuda-13.4-x64.tar.gz; do
  curl -sL -o $f https://github.com/ggml-org/llama.cpp/releases/download/b11887/$f && tar xzf $f -C cuda13.4-b11887 && rm $f
done
# flatten: the cudart libs must sit next to llama-server
cd cuda13.4-b11887 && mv cudart-*/* llama-b11887/ && rmdir cudart-* && mv llama-b11887/* . && rmdir llama-b11887
```

## Fetch command (CPU)
```
cd runtime/llamacpp/bin
curl -sL -o llama-cpu.tar.gz https://github.com/ggml-org/llama.cpp/releases/download/b11887/llama-b11887-bin-ubuntu-x64.tar.gz
tar xzf llama-cpu.tar.gz && mv llama-b11887 cpu-b11887 && rm llama-cpu.tar.gz
```
