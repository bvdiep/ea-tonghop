# Train 3DGS toi gian bang gsplat wheel (khong can simple_trainer.py,
# khong can fused_ssim/lib_bilagrid/nerfview/viser — cac thu phai compile).
# Chi dung: gsplat (rasterization, MCMCStrategy) + torch + pycolmap.
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import Tensor

sys.path.insert(0, str(Path(__file__).parent))
from colmap_loader import Dataset, Parser

import gsplat
from gsplat import rasterization
from gsplat.strategy import DefaultStrategy, MCMCStrategy


def seed_all(seed: int = 42):
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _ssim(img0, img1):
    """SSIM don gian (cu so 3DGS), de noi rong thanh hinh chu nhat."""
    # img: [H,W,3]
    C1 = 0.01 ** 2
    C2 = 0.03 ** 2
    mu0 = img0.mean(dim=(0, 1))
    mu1 = img1.mean(dim=(0, 1))
    d0 = img0 - mu0
    d1 = img1 - mu1
    cov = (d0 * d1).mean(dim=(0, 1))
    return ((2 * mu0 * mu1 + C1) * (2 * cov + C2)) / (
        (mu0 ** 2 + mu1 ** 2 + C1) * (d0.var(dim=(0, 1)) + d1.var(dim=(0, 1)) + C2)
    )


def _write_ply(path, means, scales, quats, opacities, sh0, sh_rest):
    """Ghi PLY binary_little_endian: x,y,z, f_dc_0..2, f_rest_*, opacity, scale_0..2, rot_0..3.

    PHAI la binary, khong duoc ASCII:
    - ASCII + "%.6f" mat precision cua float32 (7 chu so co nghia), lam sai lech
      scale/opacity nho va hong appearance khi viewer tinh SH.
    - ASCII phinh file ~2.4x (127MB vs ~54MB cho 218k gaussians) va load cham
      hon nhieu trong moi viewer (SuperSplat, antimatter15, nerfstudio).
    """
    means = means.detach().cpu().numpy().astype(np.float32)
    scales = torch.exp(scales).detach().cpu().numpy().astype(np.float32)
    quats = quats.detach().cpu().numpy().astype(np.float32)
    opacities = torch.sigmoid(opacities).detach().cpu().numpy().astype(np.float32)
    sh0 = sh0.detach().cpu().numpy().astype(np.float32)
    sh_rest = sh_rest.detach().cpu().numpy().astype(np.float32)
    n = means.shape[0]
    n_rest = sh_rest.shape[1] if sh_rest.ndim == 3 else 0
    sh_all = np.concatenate([sh0[:, None, :], sh_rest], axis=1)  # [N,K,3]

    # Thu tu property theo chuan 3DGS (INRIA/gsplat): x y z nx ny nz f_dc f_rest opacity scale rot
    props = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"]
    props += [f"f_rest_{i}" for i in range(n_rest * 3)]
    props += ["opacity", "scale_0", "scale_1", "scale_2",
              "rot_0", "rot_1", "rot_2", "rot_3"]

    with open(path, "wb") as f:
        header = ["ply", "format binary_little_endian 1.0", f"element vertex {n}"]
        header += [f"property float {p}" for p in props]
        header.append("end_header")
        f.write(("\n".join(header) + "\n").encode("ascii"))

        # Dung numpy structured array de ghi 1 lan, khong loop tung dong.
        rec = np.empty(n, dtype=[(p, "<f4") for p in props])
        rec["x"], rec["y"], rec["z"] = means[:, 0], means[:, 1], means[:, 2]
        rec["nx"] = rec["ny"] = rec["nz"] = 0.0
        rec["f_dc_0"], rec["f_dc_1"], rec["f_dc_2"] = (
            sh_all[:, 0, 0], sh_all[:, 0, 1], sh_all[:, 0, 2])
        for i in range(n_rest * 3):
            rec[f"f_rest_{i}"] = sh_all[:, 1:, :].reshape(n, -1)[:, i]
        rec["opacity"] = opacities
        rec["scale_0"], rec["scale_1"], rec["scale_2"] = scales[:, 0], scales[:, 1], scales[:, 2]
        rec["rot_0"], rec["rot_1"], rec["rot_2"], rec["rot_3"] = (
            quats[:, 0], quats[:, 1], quats[:, 2], quats[:, 3])
        f.write(rec.tobytes())


def train(
    data_dir: str,
    result_dir: "str | Path",
    max_steps: int = 3000,
    factor: int = 1,
    eval_every: int = 500,
    save_ply: bool = True,
    ply_steps: tuple = (),
    white_background: bool = False,
):
    seed_all()
    device = torch.device("cuda")
    result_dir = Path(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)
    # Ghi log ra file de theo doi tien do that (subprocess capture_output buffer
    # hoan toan, khong thay gi cho den khi process ket thuc).
    log_path = result_dir / "train.log"
    _log = open(log_path, "w")

    def log(msg):
        print(msg, flush=True)
        _log.write(msg + "\n")
        _log.flush()

    print(f"gsplat {gsplat.__version__} | torch {torch.__version__} | "
          f"cuda {torch.cuda.is_available()}")
    print(f"data_dir={data_dir} factor={factor} max_steps={max_steps}")

    t0 = time.time()
    parser = Parser(data_dir=data_dir, factor=factor, normalize=True, test_every=8)
    print(f"Parser: {len(parser)} images in {time.time()-t0:.1f}s, "
          f"scene_scale={parser.scene_scale:.3f}, points={parser.points.shape[0]}")

    train_ds = Dataset(parser, split="train", batch_size=1)
    val_ds = Dataset(parser, split="val", batch_size=1)
    print(f"train={len(train_ds)} val={len(val_ds)}")

    # init gaussians from points3D — GIU NGUYEN toa do goc.
    # Camera cung giu toa do goc; neu chi chia means cho scene_scale thi lech ti le.
    pts = parser.points
    rgb = parser.points_rgb
    if pts.shape[0] == 0:
        n = 100_000
        pts = np.random.randn(n, 3).astype(np.float32) * parser.scene_scale
        rgb = np.random.rand(n, 3).astype(np.float32)

    center = np.asarray(parser.scene_center, dtype=np.float32)
    means = torch.from_numpy(pts).to(device)
    colors = torch.from_numpy(rgb / 255.0).to(device).clamp(1e-6, 1.0 - 1e-6)
    n = means.shape[0]

    # khoi tao scale bang khoang cach toi lan can gan nhat (gsplat chuan)
    try:
        from scipy.spatial import cKDTree
        tree = cKDTree(pts)
        d, _ = tree.query(pts, k=4)
        nn = np.maximum(d[:, 1:].min(axis=1), 1e-6)
    except Exception:
        nn = np.maximum(np.linalg.norm(pts, axis=1), 1e-6)
    # BUG TRUOC: nn dang [N] nen `.repeat(1, 3)` lam thanh [1, 3N] (repeat them chieu).
    # Phai dung `.repeat(3, 1)` roi chuyen vei, hoac dung [N,1].repeat(1,3).
    scales = torch.log(torch.from_numpy(nn).float().to(device))[:, None].repeat(1, 3)

    quats = torch.rand((n, 4), device=device)  # [N,4] — san phong gsplat
    quats[:, 0] = 1.0  # chuẩn hoá: quats[:,0]=1 -> identity rotation
    quats = quats / quats.norm(dim=1, keepdim=True)
    opacities = torch.full((n,), 0.1, device=device)

    # SH degree: 3 la mac dinh cua gsplat (16 bases). Bat SH giup mau theo goc nhin,
    # PSNR tang bien do (khoang 24-30 dB thay vi ~14 dB khi chi dung RGB).
    sh_degree = 3
    n_sh_bases = (sh_degree + 1) ** 2  # 16
    sh0 = (colors - 0.5) / 0.28209479177387814  # [N,3] DC term
    sh_rest = torch.zeros((n, n_sh_bases - 1, 3), device=device)

    means.requires_grad_(True)
    scales.requires_grad_(True)
    quats.requires_grad_(True)
    opacities.requires_grad_(True)
    sh0.requires_grad_(True)
    sh_rest.requires_grad_(True)

    # gsplat Strategy.check_sanity() yeu cau: moi optimizer co DUNG 1 param_group,
    # va params/optimizers phai cung key. Nen phai tach optimizer rieng cho tung tensor.
    # LR lay dung theo simple_trainer.py (means_lr = 1.6e-4 * scene_scale).
    def make_opt(tensor, lr):
        return torch.optim.Adam([{"params": [tensor], "lr": lr}], betas=(0.9, 0.99),
                                eps=1e-15)

    # params la NGUON SU THAT duy nhat: DefaultStrategy grow se THAY THE
    # nn.Parameter trong dict, nen moi lan render phai doc tu day, khong dung
    # bien local (se bi stale sau lan densify dau tien).
    params = {
        "means": torch.nn.Parameter(means),
        "scales": torch.nn.Parameter(scales),
        "quats": torch.nn.Parameter(quats),
        "opacities": torch.nn.Parameter(opacities),
        "sh0": torch.nn.Parameter(sh0),
        "shN": torch.nn.Parameter(sh_rest),
    }
    opts = {
        "means": make_opt(params["means"], 1.6e-4 * parser.scene_scale),
        "scales": make_opt(params["scales"], 5e-3),
        "quats": make_opt(params["quats"], 1e-3),
        "opacities": make_opt(params["opacities"], 5e-2),
        "sh0": make_opt(params["sh0"], 2.5e-3),
        "shN": make_opt(params["shN"], 2.5e-3 / 20),
    }

    # San phong gsplat: lr_means giam dan dan ve 0.01*initial sau max_steps.
    sched = torch.optim.lr_scheduler.ExponentialLR(
        opts["means"], gamma=0.01 ** (1.0 / max_steps))

    # DefaultStrategy = split/duplicate theo gradient (3DGS goc). Day la co che
    # densify THAT SU: MCMC chi teleport gaussian chet nen so luong dung yen.
    refine_stop = min(int(max_steps * 0.5), 15_000)
    strategy = DefaultStrategy(
        prune_opa=0.005,
        grow_grad2d=0.0002,
        grow_scale3d=0.01,
        grow_scale2d=0.05,
        prune_scale3d=0.1,
        refine_start_iter=500,
        refine_stop_iter=refine_stop,
        reset_every=3000,
        refine_every=100,
        verbose=False,
    )
    strategy.check_sanity(params, opts)
    strategy_state = strategy.initialize_state(scene_scale=float(parser.scene_scale))
    log(f"strategy=DefaultStrategy refine_stop={refine_stop} "
        f"scene_scale={parser.scene_scale:.3f}")

    bg = torch.ones(3, device=device) if white_background else torch.zeros(3, device=device)
    # near plane: cat sau khoang 0.01 * scene_scale (san phong gsplat)
    near_plane = 0.01 * float(parser.scene_scale)

    def render_one(item):
        K = item["K"].to(device)[None]  # (1,3,3)
        c2w = item["cam_from_world"].to(device)[None]  # (1,4,4)
        H, W = item["image"].shape[:2]
        img = item["image"].to(device)
        viewmats = torch.linalg.inv(c2w)  # w2c
        # Doc tu params dict (DefaultStrategy co the da thay Parameter moi).
        sh0_ = params["sh0"]
        shN_ = params["shN"]
        # SH coefficients: [N, K, 3] voi K = (sh_degree+1)^2. gsplat tu tinh
        # view-dependent color + clamp(-0.5, 0.5)+0.5 -> RGB.
        colors = torch.cat([sh0_[:, None, :], shN_], dim=1)  # [N, K, 3]
        # QUAN TRONG: gsplat mong `scales` la LINEAR space, `opacities` la PROBABILITY.
        # Optimizer luu log-scale va logit-opacity (de tranh exp/sigmoid ngoai range).
        renders, alphas, info = rasterization(
            means=params["means"], quats=params["quats"],
            scales=torch.exp(params["scales"]),
            opacities=torch.sigmoid(params["opacities"]),
            colors=colors,
            viewmats=viewmats,
            Ks=K, width=W, height=H,
            render_mode="RGB", sh_degree=sh_degree,
            # packed=True: backgrounds chi can [channels] (khong kem H,W).
            backgrounds=bg.contiguous(),
            packed=True,  # tieu thu VRAM, bat buoc voi scene lon
            near_plane=near_plane,
        )
        return renders[0, ..., :3], alphas[0, ..., 0], img, info

    t_train = time.time()
    psnr_log = []
    step = 0
    while step < max_steps:
        item = train_ds[step % len(train_ds)]
        render, alpha, target, info = render_one(item)
        # San phong gsplat dung: (1-lambda)*L1 + lambda*(1-SSIM), lambda=0.2.
        ssim = _ssim(render, target).mean()
        loss = 0.8 * F.l1_loss(render, target) + 0.2 * (1 - ssim)

        # DefaultStrategy can retain_grad tren means2d TRUOC backward.
        strategy.step_pre_backward(
            params=params, optimizers=opts, state=strategy_state,
            step=step, info=info)

        for o in opts.values():
            o.zero_grad(set_to_none=True)
        loss.backward()
        for o in opts.values():
            o.step()
        sched.step()

        step += 1
        try:
            strategy.step_post_backward(
                params=params, optimizers=opts, state=strategy_state,
                step=step, info=info, packed=True)
        except RuntimeError as e:
            log(f"WARN step {step}: strategy fail ({e})")
        if step % eval_every == 0:
            with torch.no_grad():
                render, alpha, target, _ = render_one(train_ds[0])
                mse = F.mse_loss(render, target).item()
                psnr = -10 * math.log10(max(mse, 1e-10))
                psnr_log.append(psnr)
            log(f"step {step:5d}/{max_steps} loss={loss.item():.5f} "
                f"psnr={psnr:.2f} n_gaussians={params['means'].shape[0]} "
                f"opacity_mean={torch.sigmoid(params['opacities']).mean().item():.3f}")

    train_time = time.time() - t_train
    log(f"TRAIN time: {train_time:.1f}s, steps={step}, "
        f"n_gaussians={params['means'].shape[0]}")

    # save checkpoint
    ckpt = {
        "means": params["means"].detach().cpu(),
        "scales": params["scales"].detach().cpu(),
        "quats": params["quats"].detach().cpu(),
        "opacities": params["opacities"].detach().cpu(),
        "sh0": params["sh0"].detach().cpu(),
        "sh_rest": params["shN"].detach().cpu(),
        "scene_scale": parser.scene_scale,
        "scene_center": center,
    }
    torch.save(ckpt, result_dir / "ckpt.pt")

    ply_path = None
    if save_ply:
        # Mac dinh luu o step cuoi cung (khong phai moc 500 cu).
        out = result_dir / f"point_cloud_{step}.ply"
        _write_ply(out, params["means"], params["scales"], params["quats"],
                   params["opacities"], params["sh0"], params["shN"])
        ply_path = out
        log(f"saved {out} ({params['means'].shape[0]} gaussians)")

    summary = {
        "train_time_s": round(train_time, 1),
        "wall_clock_s": round(time.time() - t0, 1),
        "steps": step,
        "n_gaussians": int(params["means"].shape[0]),
        "psnr_log": psnr_log,
        "ply": str(ply_path) if ply_path else None,
        "ckpt": str(result_dir / "ckpt.pt"),
    }
    print("RESULT " + json.dumps(summary, indent=2))
    (result_dir / "train_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data_dir", required=True)
    p.add_argument("--result_dir", required=True)
    p.add_argument("--max_steps", type=int, default=3000)
    p.add_argument("--factor", type=int, default=1)
    p.add_argument("--eval_every", type=int, default=500)
    args = p.parse_args()
    train(args.data_dir, args.result_dir, args.max_steps, args.factor, args.eval_every)
