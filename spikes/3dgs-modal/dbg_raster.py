"""Debug shapes dau vao rasterization — chay tren Modal de xem wheel that."""
import torch
import gsplat
from gsplat import rasterization

print("gsplat", gsplat.__version__)
print("torch", torch.__version__)

N = 100
means = torch.randn(N, 3, device="cuda")
quats = torch.zeros(N, 4, device="cuda")
quats[:, 0] = 1.0
scales = torch.rand(N, 3, device="cuda") * 0.1
opacities = torch.rand(N, device="cuda") * 0.5
colors = torch.rand(N, 3, device="cuda")
viewmats = torch.eye(4, device="cuda")[None]
Ks = torch.tensor([[[300.0, 0, 150], [0, 300.0, 100], [0, 0, 1.0]]], device="cuda")

print("shapes:", means.shape, quats.shape, scales.shape, opacities.shape, colors.shape)

# Test 1: packed=False
try:
    r, a, m = rasterization(
        means=means, quats=quats, scales=scales, opacities=opacities,
        colors=colors, viewmats=viewmats, Ks=Ks, width=300, height=200,
        render_mode="RGB", sh_degree=None, packed=False,
    )
    print("packed=False OK ->", r.shape, a.shape)
except Exception as e:
    print("packed=False FAIL:", type(e).__name__, e)

# Test 2: packed=True
try:
    r, a, m = rasterization(
        means=means, quats=quats, scales=scales, opacities=opacities,
        colors=colors, viewmats=viewmats, Ks=Ks, width=300, height=200,
        render_mode="RGB", sh_degree=None, packed=True,
    )
    print("packed=True OK ->", r.shape, a.shape)
except Exception as e:
    print("packed=True FAIL:", type(e).__name__, e)
