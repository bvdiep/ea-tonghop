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


def _ckpt_payload(params, opts, strategy_state, step, psnr_log, parser, center):
    """Gom toan bo trang thai can de resume trung thuc.

    Giu ca optimizer state (Adam moments) va strategy_state (grad2d/count cho
    DefaultStrategy) — thieu chung thi resume se train lai tu trinh trang thai
    optimizer rong, chat luong tut so voi chay lien mach.
    """
    return {
        "step": int(step),
        "params": {k: v.detach().cpu() for k, v in params.items()},
        "opts": {k: o.state_dict() for k, o in opts.items()},
        "strategy_state": strategy_state,
        "psnr_log": psnr_log,
        "scene_scale": float(parser.scene_scale),
        "scene_center": center,
        "n_gaussians": int(params["means"].shape[0]),
    }


def _save_ckpt(ckpt, result_dir: Path, step: int, keep_last: int, log):
    """Luu ckpt_{step}.pt + con tro ckpt_latest.pt, giu toi da keep_last ban."""
    result_dir.mkdir(parents=True, exist_ok=True)
    path = result_dir / f"ckpt_{step}.pt"
    tmp = path.with_suffix(".pt.tmp")
    torch.save(ckpt, tmp)
    tmp.replace(path)  # atomic: khong bao gio de lai ckpt nua ghi
    (result_dir / "ckpt_latest.pt").write_text(str(path.name))
    log(f"CKPT saved step={step} n_gaussians={ckpt['n_gaussians']} "
        f"-> {path.name} ({path.stat().st_size / 1e6:.1f}MB)")
    olds = sorted(result_dir.glob("ckpt_[0-9]*.pt"),
                  key=lambda p: int(p.stem.split("_")[1]))
    for old in olds[:-keep_last] if keep_last > 0 else []:
        old.unlink(missing_ok=True)
        log(f"CKPT pruned {old.name}")
    return path


def _find_resume(result_dir: Path, max_steps: int):
    """Tim ckpt moi nhat con dung duoc. Tra ve (ckpt_dict|None, path|None)."""
    if not result_dir.exists():
        return None, None
    cands = sorted(result_dir.glob("ckpt_[0-9]*.pt"),
                   key=lambda p: int(p.stem.split("_")[1]), reverse=True)
    for p in cands:
        try:
            ck = torch.load(p, map_location="cpu", weights_only=False)
        except Exception:
            continue
        if ck.get("step", 0) >= max_steps:
            continue  # da xong roi, khong resume nua
        return ck, p
    return None, None


def _write_metrics(result_dir: Path, rec: dict):
    """Append 1 ban ghi vao metrics.json (giu lich su day du, khong ghi de)."""
    path = result_dir / "metrics.json"
    hist = []
    if path.exists():
        try:
            hist = json.loads(path.read_text())
        except Exception:
            hist = []
    hist.append(rec)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(hist, indent=2))
    tmp.replace(path)


def train(
    data_dir: str,
    result_dir: "str | Path",
    max_steps: int = 3000,
    factor: int = 1,
    eval_every: int = 500,
    save_ply: bool = True,
    white_background: bool = False,
    ckpt_every: int = 1000,
    resume: bool = True,
    keep_last_ckpts: int = 2,
):
    seed_all()
    device = torch.device("cuda")
    result_dir = Path(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)
    # Ghi log ra file de theo doi tien do that (subprocess capture_output buffer
    # hoan toan, khong thay gi cho den khi process ket thuc). Append + line-buffered
    # de doc duoc real-time tu volume khi job dang chay (TNG-003).
    log_path = result_dir / "train.log"
    _log = open(log_path, "a", buffering=1)

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

    # ---- resume (TNG-002) -------------------------------------------------
    # Modal preempt container bat cu luc nao va restart function voi cung input.
    # Khong resume thi moi lan preempt dot sach GPU-time da train.
    start_step = 0
    psnr_log = []
    if resume:
        ck, ck_path = _find_resume(result_dir, max_steps)
        if ck is not None:
            try:
                with torch.no_grad():
                    for k, v in ck["params"].items():
                        v_dev = v.to(device)
                        if k in params and params[k].shape == v_dev.shape:
                            params[k].copy_(v_dev)
                        else:
                            params[k] = torch.nn.Parameter(v_dev)
                            params[k].requires_grad_(True)
                # VOI DefaultStrategy: densify THAY THE params dict va optimizer.
                # Optimizer state cu khong match param moi -> KHONG load state_dict.
                # Tao optimizer moi tu params da load (giong init).
                for k, o in opts.items():
                    lr = o.param_groups[0]["lr"]
                    opts[k] = make_opt(params[k], lr)
                if isinstance(ck.get("strategy_state"), dict):
                    strategy_state = ck["strategy_state"]
                start_step = int(ck["step"])
                psnr_log = list(ck.get("psnr_log", []))
                log(f"RESUMED from {ck_path.name if ck_path else '?'} at step={start_step} "
                    f"n_gaussians={params['means'].shape[0]} (optimizer recreated)")
            except Exception as e:
                log(f"RESUME failed ({e}); bat dau lai tu step 0")
                start_step = 0
                psnr_log = []
        else:
            log("start from scratch")
    else:
        log("--resume off; start from scratch")
    # ----------------------------------------------------------------------

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
    step = start_step
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

        # ---- eval tren VAL set (TNG-003) ---------------------------------
        # Truoc day eval tren train_ds[0] -> lac quan va chi 1 anh. Val split
        # do Parser(test_every=8) tao san; eval trung binh toan bo val set.
        if step % eval_every == 0 or step == max_steps:
            with torch.no_grad():
                tot_mse, tot_ssim, n_val = 0.0, 0.0, 0
                for vi in range(len(val_ds)):
                    vr, va, vt, _ = render_one(val_ds[vi])
                    tot_mse += F.mse_loss(vr, vt).item()
                    tot_ssim += _ssim(vr, vt).mean().item()
                    n_val += 1
                mse = tot_mse / max(n_val, 1)
                psnr = -10 * math.log10(max(mse, 1e-10))
                ssim_val = tot_ssim / max(n_val, 1)
                psnr_log.append(psnr)
                n_g = int(params["means"].shape[0])
            log(f"step {step:5d}/{max_steps} loss={loss.item():.5f} "
                f"psnr_val={psnr:.2f} ssim_val={ssim_val:.4f} "
                f"n_gaussians={n_g} "
                f"opacity_mean={torch.sigmoid(params['opacities']).mean().item():.3f}")
            _write_metrics(result_dir, {
                "step": step, "psnr_val": round(psnr, 4),
                "ssim_val": round(ssim_val, 5), "n_gaussians": n_g,
                "n_val_images": n_val, "train_loss": round(loss.item(), 6),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            })
        # -------------------------------------------------------------------

        # ---- checkpoint dinh ky (TNG-002) --------------------------------
        if ckpt_every > 0 and step % ckpt_every == 0 and step < max_steps:
            _save_ckpt(_ckpt_payload(params, opts, strategy_state, step,
                                     psnr_log, parser, center),
                       result_dir, step, keep_last_ckpts, log)
        # ------------------------------------------------------------------

    train_time = time.time() - t_train
    log(f"TRAIN time: {train_time:.1f}s, steps={step}, "
        f"n_gaussians={params['means'].shape[0]}")

    # ckpt cuoi cung — luon giu de resume lan sau
    ckpt = _ckpt_payload(params, opts, strategy_state, step, psnr_log, parser, center)
    _save_ckpt(ckpt, result_dir, step, keep_last_ckpts + 1, log)

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
        "resumed_from": start_step,
        "n_gaussians": int(params["means"].shape[0]),
        "psnr_log": psnr_log,
        "psnr_val_final": psnr_log[-1] if psnr_log else None,
        "ply": str(ply_path) if ply_path else None,
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
    p.add_argument("--ckpt_every", type=int, default=1000,
                   help="luu checkpoint moi N steps (0 = tat)")
    p.add_argument("--keep_last_ckpts", type=int, default=2,
                   help="so ban checkpoint giu lai (cu nhat bi xoa)")
    p.add_argument("--no_resume", action="store_true",
                   help="tat resume, train lai tu dau")
    p.add_argument("--no_ply", action="store_true", help="khong xuat PLY")
    args = p.parse_args()
    train(args.data_dir, args.result_dir, args.max_steps, args.factor,
          args.eval_every, save_ply=not args.no_ply,
          ckpt_every=args.ckpt_every, resume=not args.no_resume,
          keep_last_ckpts=args.keep_last_ckpts)
