# Spike: verify splat-transform GPU (WebGPU/Vulkan) availability on Modal
#
# Usage:
#   pip install modal
#   modal token new          # one-time auth
#   modal run modal_app.py
#
# Reads probe results: if splat-transform --list-gpus shows an NVIDIA adapter,
# the GPU path is viable. If only llvmpipe or nothing -> GPU path dead on Modal,
# use the CPU-only variant (proven working in Docker node:22-slim).

import json

import modal

app = modal.App("splat-transform-gpu-probe")

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-runtime-ubuntu22.04", add_python="3.11")
    .env({
        "NVIDIA_DRIVER_CAPABILITIES": "compute,graphics,utility",
        "DEBIAN_FRONTEND": "noninteractive",
    })
    .apt_install(
        "curl", "ca-certificates", "gnupg",
        "vulkan-tools", "libgl1", "libglvnd0", "libglx0", "libegl1", "libxext6",
    )
    .run_commands(
        "curl -fsSL https://deb.nodesource.com/setup_22.x | bash -",
        "apt-get install -y --no-install-recommends nodejs",
        "npm install -g @playcanvas/splat-transform",
    )
)


@app.function(gpu="t4", timeout=300, image=image)
def probe() -> str:
    import subprocess

    def run(name: str, *args: str) -> dict:
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=120)
            return {"code": p.returncode, "stdout": p.stdout[-3000:], "stderr": p.stderr[-1500:]}
        except Exception as e:  # noqa: BLE001
            return {"code": -1, "stdout": "", "stderr": str(e)}

    results = {
        "nvidia_smi": run("nvidia-smi", "-L"),
        "vulkaninfo": run("vulkaninfo", "--summary"),
        "list_gpus": run("splat-transform", "--list-gpus"),
    }
    return json.dumps(results, indent=2)


@app.local_entrypoint()
def main():
    out = probe.remote()
    results = json.loads(out)
    verdict = "UNKNOWN"
    gpus = results["list_gpus"]["stdout"]
    if any(k in gpus for k in ("NVIDIA", "Tesla", "A10", "L4", "T4", "A100", "H100", "L40")):
        verdict = "GPU VIABLE - NVIDIA adapter visible to Dawn/WebGPU"
    elif "llvmpipe" in gpus:
        verdict = "CPU FALLBACK ONLY - no NVIDIA Vulkan ICD on Modal host"
    elif results["list_gpus"]["code"] != 0:
        verdict = f"FAILED: {results['list_gpus']['stderr'][:300]}"
    print(f"\n{'=' * 60}\nVERDICT: {verdict}\n{'=' * 60}")
    for k, v in results.items():
        print(f"\n----- {k} (exit {v['code']}) -----")
        print(v["stdout"][-1500:])
        if v["stderr"]:
            print("[stderr]", v["stderr"][-400:])
