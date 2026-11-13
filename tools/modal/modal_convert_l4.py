# End-to-end SSOG conversion test on Modal: GPU (T4) vs CPU, same environment.
# Requires test_500k.ply in Modal volume "ssog-spike" (upload with `modal volume put`).

import json
import subprocess
import time
import zipfile
from pathlib import Path

import modal

app = modal.App("ssog-convert-l4")

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-runtime-ubuntu22.04", add_python="3.11")
    .env({
        "NVIDIA_DRIVER_CAPABILITIES": "compute,graphics,utility",
        "DEBIAN_FRONTEND": "noninteractive",
        "XDG_RUNTIME_DIR": "/tmp/xdg",
    })
    .apt_install("curl", "ca-certificates", "gnupg", "vulkan-tools", "libgl1", "libglvnd0", "libglx0", "libegl1", "libxext6")
    .run_commands(
        "curl -fsSL https://deb.nodesource.com/setup_22.x | bash -",
        "apt-get install -y --no-install-recommends nodejs",
        "npm install -g @playcanvas/splat-transform",
    )
)

volume = modal.Volume.from_name("ssog-spike", create_if_missing=True)


@app.function(gpu="l4", timeout=900, image=image, volumes={"/vol": volume}, cpu=4, memory=8192)
def convert(gpu: bool = True) -> str:
    dev = "0" if gpu else "cpu"
    tag = "gpu" if gpu else "cpu"
    ply = "/vol/test_500k.ply"
    outdir = f"/tmp/out_{tag}"
    t0 = time.time()
    # Step 1: decimate LOD levels (GPU-heavy on -g 0)
    for pct, name in (("50%", "lod1"), ("25%", "lod2"), ("10%", "lod3")):
        subprocess.run(
            ["splat-transform", "-g", dev, ply, "-d", pct, f"/tmp/{tag}_{name}.ply"],
            check=True, capture_output=True, text=True, timeout=600,
        )
    t1 = time.time()
    # Step 2: bundle into Streamed SOG
    subprocess.run(
        ["splat-transform", "-g", dev,
         ply, "-l", "0", f"/tmp/{tag}_lod1.ply", "-l", "1", f"/tmp/{tag}_lod2.ply",
         "-l", "2", f"/tmp/{tag}_lod3.ply", "-l", "3",
         f"{outdir}/lod-meta.json", "--filter-nan"],
        check=True, capture_output=True, text=True, timeout=600,
    )
    t2 = time.time()
    # Step 3: package .ssog (zip of bundle, lod-meta.json at root)
    ssog = f"/vol/test_500k_{tag}.ssog"
    with zipfile.ZipFile(ssog, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for p in sorted(Path(outdir).rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(outdir))
    t3 = time.time()
    volume.commit()
    return json.dumps({
        "device": dev, "decimate_s": round(t1 - t0, 1), "bundle_s": round(t2 - t1, 1),
        "zip_s": round(t3 - t2, 1), "total_s": round(t3 - t0, 1),
    })


@app.local_entrypoint()
def main():
    print("GPU result:", convert.remote(gpu=True))
