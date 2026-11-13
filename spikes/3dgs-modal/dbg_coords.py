"""Kiem tra he truc toa do: render anh tu gaussians khoi tao va so sanh voi anh goc.

Neu he truc dung, render dau tien (truoc train) phai kha giong anh goc (blur nhung
dung cau truc). Neu lat nguoc / sai ti le, render se la noise.
"""
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, "/root")
from colmap_loader import Dataset, Parser

import gsplat
from gsplat import rasterization

import imageio.v2 as imageio

data_dir = sys.argv[1]
parser = Parser(data_dir=data_dir, factor=1, normalize=True, test_every=8)
print(f"scene_scale={parser.scene_scale:.4f} center={parser.scene_center} n_points={parser.points.shape[0]}")

ds = Dataset(parser, split="train")
item = ds[0]
img = item["image"].numpy()
H, W = img.shape[:2]
print(f"image {W}x{H} mean={img.mean():.3f}")

# Kiem tra camera: trong he toa do goc, diem points3D chieu vao anh phai roi vao
# vung trong anh. Lay vai diem va chieu.
K = item["K"].numpy()
c2w = item["cam_from_world"].numpy()
w2c = np.linalg.inv(c2w)
pts = parser.points[:2000]
R = w2c[:3, :3]
t = w2c[:3, 3]
pc = pts @ R.T + t
depth = pc[:, 2]
valid = depth > 0.1
uv = pc[valid] @ K.T
uv = uv[:, :2] / uv[:, 2:3]
inside = (uv[:, 0] > 0) & (uv[:, 0] < W) & (uv[:, 1] > 0) & (uv[:, 1] < H)
print(f"projected: {len(pts)} pts, {valid.sum()} in front, {inside.sum()} inside image "
      f"({inside.sum()/max(len(pts),1)*100:.1f}%)")
print(f"depth range: {depth[valid].min():.2f}..{depth[valid].max():.2f}")

# Render tu gaussians khoi tao
device = "cuda"
means = torch.from_numpy(parser.points).to(device)
rgb = torch.from_numpy(parser.points_rgb / 255.0).to(device).clamp(1e-6, 1 - 1e-6)
from scipy.spatial import cKDTree
tree = cKDTree(parser.points)
d, _ = tree.query(parser.points, k=4)
nn = np.maximum(d[:, 1:].min(axis=1), 1e-6)
scales = torch.log(torch.from_numpy(nn).float().to(device))[:, None].repeat(1, 3)
print(f"NN scale: min={nn.min():.4f} median={np.median(nn):.4f} max={nn.max():.4f} "
      f"(scene_scale={parser.scene_scale:.2f})")
quats = torch.zeros((means.shape[0], 4), device=device)
quats[:, 0] = 1.0
opacities = torch.full((means.shape[0],), 0.5, device=device)
colors = rgb

viewmats = torch.from_numpy(w2c).float().to(device)[None]
Ks = torch.from_numpy(K).float().to(device)[None]

renders, alphas, info = rasterization(
    means=means, quats=quats, scales=scales, opacities=opacities,
    colors=colors, viewmats=viewmats, Ks=Ks, width=W, height=H,
    render_mode="RGB", sh_degree=None, backgrounds=torch.zeros(3, device=device),
    packed=True, near_plane=0.01 * parser.scene_scale,
)
render = renders[0, ..., :3].detach().cpu().numpy()
alpha = alphas[0, ..., 0].detach().cpu().numpy()
print(f"render: mean={render.mean():.3f} max={render.max():.3f} alpha_mean={alpha.mean():.3f} "
      f"alpha_max={alpha.max():.3f}")
mse = ((render - img) ** 2).mean()
print(f"MSE vs original: {mse:.4f} PSNR={-10*np.log10(max(mse,1e-10)):.2f}")

# Thử lật trục: gsplat dùng he toa do OpenGL (Y up, -Z forward) khi cam_from_gs=eye?
# Kiem tra may cach dat lai he truc.
for name, M in [
    ("identity", np.eye(4)),
    ("y_flip", np.diag([1, -1, 1, 1])),
    ("x_flip", np.diag([-1, 1, 1, 1])),
    ("z_flip", np.diag([1, 1, -1, 1])),
    ("opengl", np.array([[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]], dtype=np.float32)),
]:
    w2c2 = w2c @ M
    vm = torch.from_numpy(w2c2).float().to(device)[None]
    try:
        r2, a2, _ = rasterization(
            means=means, quats=quats, scales=scales, opacities=opacities,
            colors=colors, viewmats=vm, Ks=Ks, width=W, height=H,
            render_mode="RGB", sh_degree=None, backgrounds=torch.zeros(3, device=device),
            packed=True, near_plane=0.01 * parser.scene_scale,
        )
        rr = r2[0, ..., :3].detach().cpu().numpy()
        aa = a2[0, ..., 0].detach().cpu().numpy()
        m2 = ((rr - img) ** 2).mean()
        print(f"  {name:9s}: alpha_mean={aa.mean():.3f} PSNR={-10*np.log10(max(m2,1e-10)):.2f} "
              f"render_mean={rr.mean():.3f}")
    except Exception as e:
        print(f"  {name:9s}: FAIL {type(e).__name__} {e}")

imageio.imwrite("/tmp/render_raw.png", (np.clip(render, 0, 1) * 255).astype(np.uint8))
imageio.imwrite("/tmp/target.png", (np.clip(img, 0, 1) * 255).astype(np.uint8))
print("wrote /tmp/render_raw.png /tmp/target.png")
