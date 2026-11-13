# Convert a PLY on Modal into a Streamed SOG (.ssog) bundle.
# Usage:
#   modal deploy modal_ssog_convert.py
#   modal run modal_ssog_convert.py --ply toancanh.ply --out toancanh.ssog
# The job runs server-side; the local process only waits for the result.

import json
import subprocess
import time
import zipfile
from pathlib import Path

import modal

app = modal.App("ssog-convert")

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


@app.function(gpu="l4", timeout=14400, image=image, volumes={"/vol": volume}, cpu=8, memory=16384)
def convert(ply_name: str, out_name: str) -> str:
    ply = f"/vol/{ply_name}"
    outdir = "/tmp/out"
    t0 = time.time()
    steps = []

    # Step 1: decimate LOD levels (uniform; use --decimate-adaptive for sky-heavy scenes)
    for pct, name in (("50%", "lod1"), ("25%", "lod2"), ("10%", "lod3")):
        ts = time.time()
        subprocess.run(
            ["splat-transform", "-g", "0", "-w", ply, "-d", pct, f"/tmp/{name}.ply"],
            check=True, capture_output=True, text=True, timeout=3600,
        )
        steps.append(f"decimate {pct}: {time.time() - ts:.1f}s")

    # Step 2: bundle into Streamed SOG (output filename must be lod-meta.json)
    ts = time.time()
    subprocess.run(
        ["splat-transform", "-g", "0", "-w",
         ply, "-l", "0", "/tmp/lod1.ply", "-l", "1", "/tmp/lod2.ply",
         "-l", "2", "/tmp/lod3.ply", "-l", "3",
         f"{outdir}/lod-meta.json", "--filter-nan"],
        check=True, capture_output=True, text=True, timeout=7200,
    )
    steps.append(f"bundle: {time.time() - ts:.1f}s")

    # Step 3: verify + package .ssog (zip of the bundle, lod-meta.json at root)
    info = subprocess.run(
        ["splat-transform", f"{outdir}/lod-meta.json", "--info", "null"],
        check=True, capture_output=True, text=True, timeout=900,
    )
    ts = time.time()
    ssog = f"/vol/{out_name}"
    with zipfile.ZipFile(ssog, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for p in sorted(Path(outdir).rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(outdir))
    steps.append(f"zip: {time.time() - ts:.1f}s")

    volume.commit()
    return json.dumps({
        "total_s": round(time.time() - t0, 1),
        "steps": steps,
        "ssog_size_mb": round(Path(ssog).stat().st_size / 1e6, 1),
        "info": info.stdout.strip()[-600:],
    })


@app.local_entrypoint()
def main(ply: str, out: str):
    result = convert.remote(ply, out)
    print("RESULT:", result)
