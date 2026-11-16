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


def _colmap_cache_dir(subset: int) -> Path:
    return Path("/vol") / f"colmap_cache_s{subset}"


def _colmap_cache_valid(subset: int, work: Path) -> "Path | None":
    """COLMAP output da co trong volume -> dung lai, bo qua stage extract/match/mapper.

    TNG-002: moi lan Modal preempt va restart, COLMAP chay lai tu dau (~50s voi 40 anh,
    nhung ~5-12h voi 2500 anh). Cache nay bien restart thanh gan nhu mien phi.
    """
    cache = _colmap_cache_dir(subset)
    ready = cache / "dataset_ready"
    sparse = ready / "sparse"
    if not (sparse.is_dir() and (ready / "images").is_dir()):
        return None
    n_img = len(list((ready / "images").glob("*")))
    # dataset_ready trong volume chi co 1 model (undistort chi xuat model chinh)
    if n_img < 2:
        return None
    print(f"COLMAP cache HIT: {n_img} undistorted images in {ready}")
    # copy sang work de train doc duong dan nhu cu
    dest = work / "dataset_ready"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ready, dest)
    return dest


def _colmap_cache_save(subset: int, work: Path):
    cache = _colmap_cache_dir(subset)
    cache.mkdir(parents=True, exist_ok=True)
    src = work / "dataset_ready"
    dst = cache / "dataset_ready"
    if src.is_dir() and not dst.is_dir():
        shutil.copytree(src, dst)
        print(f"COLMAP cache SAVED -> {dst}")


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


def _pipeline_impl(subset: int, max_steps: int, resume: bool,
                   ckpt_every: int, data_factor: int,
                   refine_stop: "int | None" = None,
                   grow_grad2d: float = 0.0002,
                   grow_scale3d: float = 0.01) -> dict:
    t_all = time.time()
    work = Path("/tmp/work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    timings = {}

    # ---- Stage 1: COLMAP, uu tien cache trong volume ----------------------
    cached = _colmap_cache_valid(subset, work)
    if cached is not None:
        ready = cached
        timings["colmap_cached"] = 0.0
    else:
        colmap_res = run_colmap(work, subset)
        timings.update(colmap_res["timings"])
        ready = colmap_res["ready"]
        if ready is None:
            result = {"status": "FAIL_MAPPER", "timings": timings}
            print("RESULT " + json.dumps(result))
            Path("/vol/result_gsplat.json").write_text(json.dumps(result, indent=2))
            volume.commit()
            return result
        _colmap_cache_save(subset, work)
        volume.commit()  # commit ngay: neu preempt o stage train, cache van con
    # ----------------------------------------------------------------------

    py = "/usr/local/bin/python3"
    # TNG-002: result_dir PHAI nam tren volume, khong phai /tmp. Neu de /tmp thi
    # checkpoint + metrics.json + train.log deu mat khi container restart.
    # KHONG dua max_steps vao ten thu muc: neu co, lan chay 1000 steps va 2000 steps
    # ghi vao 2 thu muc khac nhau -> resume khong bao gio tim thay ckpt cu.
    # TNG-005: densify config khac nhau cung la scene khac nhau (refine_stop doi
    # thi so gaussian va chat luong doi) nen phai tach thu muc, neu khong resume
    # se load ckpt cua cau hinh khac.
    tag = ""
    if refine_stop is not None:
        tag += f"_rs{refine_stop}"
    if grow_grad2d != 0.0002:
        tag += f"_gg{grow_grad2d}"
    result_dir = Path("/vol") / f"gsplat_s{subset}_f{data_factor}{tag}"
    result_dir.mkdir(parents=True, exist_ok=True)

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

    # ---- Stage 2: train --------------------------------------------------
    cmd = [
        py, "/root/train_gsplat.py",
        "--data_dir", str(ready),
        "--result_dir", str(result_dir),
        "--max_steps", str(max_steps),
        "--factor", str(data_factor),
        "--ckpt_every", str(ckpt_every),
        "--grow_grad2d", str(grow_grad2d),
        "--grow_scale3d", str(grow_scale3d),
    ]
    if refine_stop is not None:
        cmd += ["--refine_stop", str(refine_stop)]
    if not resume:
        cmd.append("--no_resume")
    t0 = time.time()
    rc, out = sh(cmd, timeout=5 * 3600)
    timings["gsplat_train"] = round(time.time() - t0, 1)
    print(f"TIMING gsplat_train: {timings['gsplat_train']}s rc={rc}")
    print(out)
    volume.commit()  # day ckpt/metrics/train.log ra volume ngay
    # ----------------------------------------------------------------------

    plys = sorted(result_dir.rglob("*.ply"))
    ply_info = None
    if plys:
        ply = max(plys, key=lambda p: p.stat().st_size)
        head = ply.read_bytes()[:2048]
        nverts = None
        for line in head.split(b"\n"):
            if line.startswith(b"element vertex"):
                nverts = int(line.split()[2])
        ply_info = {"path": str(ply),
                    "size_mb": round(ply.stat().st_size / 1e6, 1),
                    "vertices": nverts}

    # metrics + train summary doc tu volume (khong copy, da o dung cho)
    metrics, summary = [], {}
    mpath = result_dir / "metrics.json"
    if mpath.exists():
        try:
            metrics = json.loads(mpath.read_text())
        except Exception:
            metrics = []
    spath = result_dir / "train_summary.json"
    if spath.exists():
        try:
            summary = json.loads(spath.read_text())
        except Exception:
            summary = {}

    # PLY copy vao subdir rieng cho de lay; ckpt giu nguyen trong result_dir
    dest = result_dir / "ply"
    dest.mkdir(parents=True, exist_ok=True)
    ply_out = None
    if ply_info:
        src_ply = Path(ply_info["path"])
        if src_ply.is_absolute() and src_ply.exists():
            target = dest / src_ply.name
            if not target.exists():
                shutil.copy(src_ply, target)
            ply_out = str(target)
            ply_info["path"] = ply_out

    result = {
        "status": "OK" if ply_info else "FAIL_TRAIN",
        "images_total": 128,
        "images_used": subset,
        "timings": timings,
        "wall_clock_s": round(time.time() - t_all, 1),
        "ply": ply_info,
        "metrics": metrics,
        "train_summary": summary,
        "colmap_cached": bool(cached is not None),
        "result_dir": str(result_dir),
    }
    print("RESULT " + json.dumps(result, indent=2))
    Path("/vol/result_gsplat.json").write_text(json.dumps(result, indent=2))
    volume.commit()
    return result


# TNG-004: profile tai nguyen theo quy mau, khong hard-code mot cau hinh cho moi
# quy mo. 8GB du cho 40 anh nhung OOM voi 2500 anh (mapper + undistort giu nhieu
# anh trong RAM). Doc: docs/ke-hoach-3dgs-production.md muc 3.4.
RESOURCE_PROFILES = {
    "small":  {"gpu": "T4", "cpu": 2, "memory": 8192},    # <= 100 anh
    "medium": {"gpu": "L4", "cpu": 8, "memory": 32768},   # 100 - 1000 anh
    "large":  {"gpu": "L4", "cpu": 16, "memory": 65536},  # > 1000 anh
}


def pick_profile(subset: int) -> dict:
    if subset <= 100:
        return RESOURCE_PROFILES["small"]
    if subset <= 1000:
        return RESOURCE_PROFILES["medium"]
    return RESOURCE_PROFILES["large"]


@app.function(image=image, gpu="T4", cpu=2, memory=8192, timeout=6 * 3600,
              volumes={"/vol": volume})
def run_pipeline(subset: int = 20, max_steps: int = 3000, resume: bool = True,
                 ckpt_every: int = 1000, data_factor: int = 1,
                 refine_stop: "int | None" = None,
                 grow_grad2d: float = 0.0002,
                 grow_scale3d: float = 0.01) -> dict:
    """COLMAP (co cache) + gsplat train (co checkpoint/resume). Profile nho."""
    return _pipeline_impl(subset, max_steps, resume, ckpt_every, data_factor,
                          refine_stop, grow_grad2d, grow_scale3d)


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


@app.function(image=image, gpu="L4", cpu=8, memory=32768, timeout=4 * 3600,
              volumes={"/vol": volume})
def run_pipeline_scaled(subset: int = 500, max_steps: int = 30000,
                        resume: bool = True, ckpt_every: int = 1000,
                        data_factor: int = 2,
                        refine_stop: "int | None" = None,
                        grow_grad2d: float = 0.0002,
                        grow_scale3d: float = 0.01) -> dict:
    """Wrapper cho du lieu vua/lon: tai nguyen theo profile, timeout ngan hon.

    Timeout ngan (4h) co chu dich: function cang dai cang de bi preempt giua chung.
    Orchestrator goi lai nhieu lan; moi lan resume tu checkpoint (TNG-002).
    """
    return _pipeline_impl(subset, max_steps, resume, ckpt_every, data_factor,
                          refine_stop, grow_grad2d, grow_scale3d)


@app.local_entrypoint()
def main(subset: int = 20, max_steps: int = 3000, resume: bool = True,
         ckpt_every: int = 1000, data_factor: int = 1, auto_scale: bool = False,
         refine_stop: int = 0, grow_grad2d: float = 0.0002,
         grow_scale3d: float = 0.01):
    prof = pick_profile(subset)
    fn_name = "run_pipeline_scaled" if (auto_scale or subset > 100) else "run_pipeline"
    rs = refine_stop if refine_stop > 0 else None
    print(f"profile={prof} fn={fn_name} subset={subset} max_steps={max_steps} "
          f"resume={resume} data_factor={data_factor} refine_stop={rs} "
          f"grow_grad2d={grow_grad2d} grow_scale3d={grow_scale3d}")
    fn = modal.Function.from_name("s3dgs-gsplat", fn_name)
    result = fn.remote(subset, max_steps, resume, ckpt_every, data_factor,
                       rs, grow_grad2d, grow_scale3d)
    print("RESULT " + json.dumps(result, indent=2))
