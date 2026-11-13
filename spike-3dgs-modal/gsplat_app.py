# Phuong an 3: pipeline COLMAP (da chay duoc) + train 3DGS bang gsplat
# (thu vien headless thuan CUDA, khong can Vulkan/viewer).
# Muc tieu: do thoi gian that tren input nho -> ngoai suy len bo 20GB anh drone.
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import modal

app = modal.App("s3dgs-gsplat")

DATA_URL = "https://github.com/colmap/colmap/releases/download/3.11.1/South-Building.zip"

# Image: COLMAP CUDA (conda-forge) + torch + gsplat. Tai gsplat tu wheel da
# build san cho torch/CUDA pho bien (pip gsplat), tranh compile source.
image = (
    # Python 3.10 — wheel gsplat san co chi co cp310
    modal.Image.from_registry("vulcanist/lichtfeld-studio:latest", add_python="3.10")
    .apt_install("bzip2", "git")
    .run_commands(
        "curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest "
        "| tar -xj -C /opt -f - bin/micromamba",
    )
    .env({"MAMBA_ROOT_PREFIX": "/opt/mamba", "CONDA_OVERRIDE_CUDA": "12.9"})
    .run_commands(
        "/opt/bin/micromamba create -y -p /opt/colmap-env -c conda-forge "
        "'colmap=4.2.1=cuda_129*'",
    )
    # Khong con can nvcc (gsplat copy file .py, khong compile). Chỉ pin lại
    # colmap để chắc chắn không bị ghi đè.
    .run_commands(
        "/opt/bin/micromamba install -y -p /opt/colmap-env -c conda-forge "
        "'colmap=4.2.1=cuda_129*'",
    )
    # PATH phai tro den colmap-env truoc, nhung pip phai dung python he thong
    # (conda env cua micromamba khong co pip).
    .env({"PATH": "/opt/colmap-env/bin:/usr/local/bin:/usr/bin:/bin",
          "PIP_PYTHON": "/usr/local/bin/python3",
          "CUDA_HOME": "/opt/colmap-env",
          "PATH_NVCC": "/opt/colmap-env/bin/nvcc"})
    .run_commands(
        "/usr/local/bin/python3 -m pip install --upgrade pip",
    )
    .run_commands(
        "/usr/local/bin/python3 -m pip install "
        "torch==2.4.1 torchvision==0.19.1 "
        "--extra-index-url https://download.pytorch.org/whl/cu121",
    )
    # Wheel gsplat san co cho torch 2.4 + cu121 (khong can JIT compile)
    .run_commands(
        "/usr/local/bin/python3 -m pip install ninja numpy jaxtyping rich && "
        "/usr/local/bin/python3 -m pip install "
        "gsplat==1.5.3 --index-url https://docs.gsplat.studio/whl/pt24cu121"
    )
    .run_commands("/usr/local/bin/python3 -m pip install pycolmap==4.2.1")
    .run_commands("/usr/local/bin/python3 -m pip install nerfview viser tyro "
                  "imageio imageio-ffmpeg opencv-python-headless scikit-image "
                  "tensorboard torchmetrics plyfile pyyaml piexif "
                  "scikit-learn matplotlib tqdm rich splines scipy")
)

volume = modal.Volume.from_name("s3dgs-spike", create_if_missing=True)

# Dua script train + loader vao container
image = image.add_local_file(
    str(Path(__file__).parent / "train_gsplat.py"), "/root/train_gsplat.py"
).add_local_file(
    str(Path(__file__).parent / "colmap_loader.py"), "/root/colmap_loader.py"
).add_local_file(
    str(Path(__file__).parent / "dbg_coords.py"), "/root/dbg_coords.py"
)


def sh(cmd: list[str], cwd: "str | None" = None, timeout: int = 7200) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, "\n".join(out.strip().splitlines()[-25:])


def run_colmap(work: Path, subset: int) -> dict:
    """COLMAP: extract -> match -> mapper -> undistort. Tra ve ready dir + timings."""
    timings = {}
    raw = work / "raw_images"
    raw.mkdir(parents=True, exist_ok=True)
    colmap = "/opt/colmap-env/bin/colmap"

    def stage(name: str, cmd: list[str], timeout: int = 7200):
        t0 = time.time()
        rc, out = sh(cmd, timeout=timeout)
        timings[name] = round(time.time() - t0, 1)
        print(f"TIMING {name}: {timings[name]}s rc={rc}")
        print(out)
        return rc

    rc = stage("download", ["curl", "-fL", DATA_URL, "-o", "/tmp/sb.zip"],
               timeout=1800)
    assert rc == 0, "download failed"
    import zipfile
    with zipfile.ZipFile("/tmp/sb.zip") as zf:
        zf.extractall("/tmp/data")
    src_imgs = sorted(set(
        list(Path("/tmp/data").rglob("*.JPG"))
        + list(Path("/tmp/data").rglob("*.jpg"))
        + list(Path("/tmp/data").rglob("*.png"))
    ))
    total = len(src_imgs)
    use = src_imgs[:subset] if subset < total else src_imgs
    for f in use:
        shutil.copy(f, raw / f.name)
    print(f"DATASET: total {total} images, using {len(use)}")

    db = str(work / "database.db")
    stage("feature_extractor", [
        colmap, "feature_extractor",
        "--database_path", db,
        "--image_path", str(raw),
        "--ImageReader.single_camera", "1",
        "--ImageReader.camera_model", "OPENCV",
        "--FeatureExtraction.use_gpu", "1",
        "--SiftExtraction.max_num_features", "8192",
    ], timeout=3600)

    stage("sequential_matcher", [
        colmap, "sequential_matcher",
        "--database_path", db,
        "--FeatureMatching.use_gpu", "1",
        "--SequentialMatching.overlap", "15",
    ], timeout=3600)

    sparse = work / "sparse"
    sparse.mkdir(parents=True, exist_ok=True)
    stage("mapper", [
        colmap, "mapper",
        "--database_path", db,
        "--image_path", str(raw),
        "--output_path", str(sparse),
    ], timeout=3 * 3600)

    models = sorted(sparse.glob("*")) if sparse.exists() else []
    if not models:
        return {"ready": None, "timings": timings, "registered": 0}

    def model_size(m: Path) -> int:
        ib = m / "images.bin"
        return ib.stat().st_size if ib.exists() else 0

    main_model = max(models, key=model_size)
    print(f"MAPPER: {len(models)} model(s), chon {main_model.name}")

    ready = work / "dataset_ready"
    stage("undistort", [
        colmap, "image_undistorter",
        "--image_path", str(raw),
        "--input_path", str(main_model),
        "--output_path", str(ready),
        "--output_type", "COLMAP",
        "--max_image_size", "2400",
    ], timeout=3600)

    reg = work / "registered.txt"
    reg.write_text(main_model.name)
    return {"ready": ready, "timings": timings,
            "registered": model_size(main_model)}


@app.function(image=image, gpu="T4", cpu=2, memory=8192, timeout=6 * 3600,
              volumes={"/vol": volume})
def run_pipeline(subset: int = 20, max_steps: int = 3000) -> dict:
    """COLMAP (da chay duoc) + gsplat simple_trainer mcmc."""
    t_all = time.time()
    work = Path("/tmp/work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    colmap_res = run_colmap(work, subset)
    timings = dict(colmap_res["timings"])
    ready = colmap_res["ready"]
    if ready is None:
        result = {"status": "FAIL_MAPPER", "timings": timings}
        print("RESULT " + json.dumps(result))
        Path("/vol/result_gsplat.json").write_text(json.dumps(result, indent=2))
        volume.commit()
        return result
    # gsplat: chay simple_trainer.py tu goi thu vien, khong can source tree.
    py = "/usr/local/bin/python3"
    result_dir = work / "gsplat_out"
    t0 = time.time()
    rc, out = sh([
        py, "-c", "import gsplat, torch; "
        "print('gsplat', gsplat.__version__, 'torch', torch.__version__, "
        "torch.cuda.is_available())"
    ], timeout=300)
    timings["gsplat_import"] = round(time.time() - t0, 1)
    print(f"gsplat import rc={rc}: {out}")
    if rc != 0:
        result = {"status": "FAIL_IMPORT", "timings": timings}
        print("RESULT " + json.dumps(result))
        Path("/vol/result_gsplat.json").write_text(json.dumps(result, indent=2))
        volume.commit()
        return result

    # Train bang script toi gian (khong can simple_trainer.py + deps phai compile)
    t0 = time.time()
    rc, out = sh([
        py, "/root/train_gsplat.py",
        "--data_dir", str(ready),
        "--result_dir", str(result_dir),
        "--max_steps", str(max_steps),
    ], timeout=5 * 3600)
    timings["gsplat_train"] = round(time.time() - t0, 1)
    print(f"TIMING gsplat_train: {timings['gsplat_train']}s rc={rc}")
    print(out)

    plys = sorted(result_dir.rglob("*.ply"))
    ply_info = None
    if plys:
        ply = max(plys, key=lambda p: p.stat().st_size)
        head = ply.read_bytes()[:2048]
        nverts = None
        for line in head.split(b"\n"):
            if line.startswith(b"element vertex"):
                nverts = int(line.split()[2])
        ply_info = {"path": str(ply.relative_to(work)),
                    "size_mb": round(ply.stat().st_size / 1e6, 1),
                    "vertices": nverts}

    dest = Path("/vol") / f"gsplat_s{subset}_i{max_steps}"
    dest.mkdir(parents=True, exist_ok=True)
    if ply_info:
        # ply_info["path"] co the la duong dan tuong doi -> gop voi work
        src_ply = Path(ply_info["path"])
        if not src_ply.is_absolute():
            src_ply = work / src_ply
        if src_ply.exists():
            shutil.copy(src_ply, dest / src_ply.name)

    result = {
        "status": "OK" if ply_info else "FAIL_TRAIN",
        "images_total": 128,
        "images_used": subset,
        "timings": timings,
        "wall_clock_s": round(time.time() - t_all, 1),
        "ply": ply_info,
    }
    print("RESULT " + json.dumps(result, indent=2))
    Path("/vol/result_gsplat.json").write_text(json.dumps(result, indent=2))
    volume.commit()
    return result


@app.function(image=image, gpu="T4", cpu=2, memory=8192, timeout=3600,
              volumes={"/vol": volume})
def dbg_raster():
    """Probe shapes dau vao rasterization (debug)."""
    import subprocess, sys
    for py in ["/usr/local/bin/python3", "/opt/colmap-env/bin/python"]:
        p = subprocess.run([py, "-c",
            "import torch, gsplat; print(torch.__version__, gsplat.__version__)"],
            capture_output=True, text=True)
        print(f"{py}: rc={p.returncode} out={(p.stdout or p.stderr).strip()[:200]}")
    print("this interpreter:", sys.executable, sys.version)
    import torch
    import gsplat
    from gsplat import rasterization
    print("gsplat", gsplat.__version__, "torch", torch.__version__)
    N = 100
    means = torch.randn(N, 3, device="cuda")
    quats = torch.zeros(N, 4, device="cuda")
    quats[:, 0] = 1.0
    scales = torch.rand(N, 3, device="cuda") * 0.1
    opacities = torch.rand(N, device="cuda") * 0.5
    colors = torch.rand(N, 3, device="cuda")
    viewmats = torch.eye(4, device="cuda")[None]
    Ks = torch.tensor([[[300.0, 0, 150], [0, 300.0, 100], [0, 0, 1.0]]], device="cuda")
    for packed in (False, True):
        try:
            r, a, m = rasterization(
                means=means, quats=quats, scales=scales, opacities=opacities,
                colors=colors, viewmats=viewmats, Ks=Ks, width=300, height=200,
                render_mode="RGB", sh_degree=None, packed=packed,
            )
            print(f"packed={packed} OK -> {r.shape} {a.shape}")
        except Exception as e:
            print(f"packed={packed} FAIL: {type(e).__name__} {e}")


@app.function(image=image, gpu="T4", cpu=2, memory=8192, timeout=3600,
              volumes={"/vol": volume})
def dbg_coords():
    """Kiem tra he truc toa do + render anh de so sanh."""
    import subprocess
    # Chay COLMAP truoc de co dataset_ready
    import sys
    sys.path.insert(0, "/root")
    from gsplat_app import run_colmap
    from pathlib import Path
    import shutil
    work = Path("/tmp/work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    res = run_colmap(work, 40)
    print("COLMAP ready:", res["ready"])
    p = subprocess.run(
        ["/usr/local/bin/python3", "/root/dbg_coords.py", str(res["ready"])],
        capture_output=True, text=True, timeout=1800)
    print(p.stdout[-4000:])
    print("STDERR:", p.stderr[-1500:])
    print("rc:", p.returncode)


@app.local_entrypoint()
def main(subset: int = 20, max_steps: int = 3000):
    result = modal.Function.from_name("s3dgs-gsplat", "run_pipeline").remote(
        subset, max_steps)
    print("RESULT " + json.dumps(result, indent=2))
