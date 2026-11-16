"""Chia ảnh drone thành vùng theo GPS để chạy COLMAP riêng từng vùng.

Vì sao cần: với ~2.500 ảnh phủ vùng rộng (>1-2 km), `sequential_matcher` +
`mapper` của COLMAP dễ tách thành nhiều model rời rạc — mỗi model chỉ phủ một
mảnh, phần còn lại không được reconstruct. Cách xử lý: cluster ảnh theo khoảng
cách địa lý, chạy COLMAP riêng từng vùng, mỗi vùng là một scene 3DGS độc lập
(hoặc merge sau bằng PLY).

Module này chỉ đọc EXIF và copy file — không cần GPU, không cần COLMAP.

Dùng:
    python gps_regions.py --src /data/drone --out /data/regions --eps-km 0.8
    python gps_regions.py --src /data/drone --report        # chỉ xem, không copy

Kết quả: <out>/region_00/, region_01/, ... + <out>/regions.json
Ảnh không có GPS được đưa vào region "unassigned" (KHÔNG tự gán bừa vào vùng
gần nhất: ảnh thiếu GPS thường là ảnh chụp trong nhà/scan phụ, gán sai sẽ làm
bẩn model).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".dng"}

# Earth radius (km) — dùng cho haversine
_R_EARTH = 6371.0088


@dataclass
class Photo:
    path: str
    lat: float
    lon: float


def _dms_to_deg(dms, ref) -> "float | None":
    """Đổi (deg, min, sec) + 'N'/'S'/'E'/'W' sang độ thập phân."""
    try:
        d, m, s = (float(x) for x in dms)
    except Exception:
        return None
    deg = d + m / 60.0 + s / 3600.0
    if isinstance(ref, bytes):
        ref = ref.decode("ascii", "ignore")
    if ref in ("S", "W"):
        deg = -deg
    return deg


def read_gps(path: "str | Path") -> "tuple[float, float] | None":
    """Đọc GPS từ EXIF. Trả (lat, lon) hoặc None nếu không có/không hợp lệ."""
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            if not exif:
                return None
            gps = exif.get_ifd(0x8825)  # GPSInfo IFD
    except Exception:
        return None
    if not gps:
        return None
    lat = _dms_to_deg(gps.get(2), gps.get(1))
    lon = _dms_to_deg(gps.get(4), gps.get(3))
    if lat is None or lon is None:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if abs(lat) < 1e-9 and abs(lon) < 1e-9:
        return None  # 0,0 = null island, chắc chắn là EXIF rác
    return lat, lon


def haversine_km(lat1, lon1, lat2, lon2):
    """Khoảng cách km giữa các mảng toạ độ (broadcast được)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * _R_EARTH * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def cluster_by_distance(pts: np.ndarray, eps_km: float) -> "list[list[int]]":
    """Single-link clustering theo ngưỡng khoảng cách (union-find).

    Dùng single-link vì mục tiêu là "ảnh liên tiếp nhau về vị trí thuộc cùng
    scene"; centroid-link (k-means) sẽ cắt ngang dải bay và tách rời ảnh kề nhau
    — đúng cái ta muốn tránh.

    O(n^2) bộ nhớ-thời gian với n=2500 là ~6M cặp, chấp nhận được. Không dùng
    sklearn để script chạy được cả ở venv tối giản.
    """
    n = len(pts)
    if n == 0:
        return []
    if n == 1:
        return [[0]]

    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    lat, lon = pts[:, 0], pts[:, 1]
    # Chia block để tránh ma trận n x n đầy đủ khi n lớn (2500 -> 6.25M float64
    # = 50MB, vẫn ổn, nhưng block giữ đỉnh bộ nhớ thấp và cho phép n ~ 20k).
    block = 512
    for i0 in range(0, n, block):
        i1 = min(i0 + block, n)
        d = haversine_km(lat[i0:i1, None], lon[i0:i1, None], lat[None, :], lon[None, :])
        ii, jj = np.nonzero(d <= eps_km)
        for a, b in zip(ii.tolist(), jj.tolist()):
            union(i0 + a, b)

    groups: "dict[int, list[int]]" = {}
    for idx in range(n):
        groups.setdefault(find(idx), []).append(idx)
    # sắp xếp để kết quả deterministic: vùng lớn trước, rồi theo chỉ số ảnh đầu
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]))


def scan_folder(src: "str | Path") -> "tuple[list[Photo], list[str]]":
    """Quét ảnh trong thư mục (đệ quy). Trả (photos có GPS, paths thiếu GPS)."""
    src = Path(src)
    files = sorted(p for p in src.rglob("*") if p.suffix.lower() in IMAGE_EXTS)
    photos, no_gps = [], []
    for p in files:
        ll = read_gps(p)
        if ll is None:
            no_gps.append(str(p.relative_to(src)))
        else:
            photos.append(Photo(path=str(p.relative_to(src)), lat=ll[0], lon=ll[1]))
    return photos, no_gps


def build_regions(photos: "list[Photo]", eps_km: float) -> "list[dict]":
    """Gom ảnh thành các vùng, trả metadata từng vùng."""
    if not photos:
        return []
    pts = np.array([[p.lat, p.lon] for p in photos], dtype=np.float64)
    groups = cluster_by_distance(pts, eps_km)
    regions = []
    for gi, idxs in enumerate(groups):
        sub = pts[idxs]
        regions.append({
            "region": f"region_{gi:02d}",
            "n_images": len(idxs),
            "lat": float(sub[:, 0].mean()),
            "lon": float(sub[:, 1].mean()),
            "bbox": {
                "lat_min": float(sub[:, 0].min()), "lat_max": float(sub[:, 0].max()),
                "lon_min": float(sub[:, 1].min()), "lon_max": float(sub[:, 1].max()),
            },
            "radius_km": round(float(haversine_km(
                sub[:, 0].mean(), sub[:, 1].mean(),
                sub[:, 0], sub[:, 1]).max()), 4),
            "images": [photos[i].path for i in idxs],
        })
    return regions


def write_regions(src: Path, out: Path, regions: "list[dict]",
                  unassigned: "list[str]", copy: bool = True) -> Path:
    """Ghi regions.json và (tuỳ chọn) copy ảnh vào từng thư mục vùng."""
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "src": str(src),
        "eps_km": None,  # điền bởi caller nếu cần
        "n_total": sum(r["n_images"] for r in regions) + len(unassigned),
        "n_assigned": sum(r["n_images"] for r in regions),
        "n_unassigned": len(unassigned),
        "regions": regions,
        "unassigned": unassigned,
    }
    if copy:
        for r in regions:
            d = out / r["region"]
            d.mkdir(parents=True, exist_ok=True)
            for rel in r["images"]:
                target = d / Path(rel).name
                if not target.exists():
                    shutil.copy(src / rel, target)
        if unassigned:
            d = out / "unassigned"
            d.mkdir(parents=True, exist_ok=True)
            for rel in unassigned:
                target = d / Path(rel).name
                if not target.exists():
                    shutil.copy(src / rel, target)
    path = out / "regions.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return path


def summarize(regions: "list[dict]", unassigned: "list[str]") -> str:
    lines = [f"Tổng {sum(r['n_images'] for r in regions) + len(unassigned)} ảnh "
             f"-> {len(regions)} vùng"]
    for r in regions:
        lines.append(f"  {r['region']}: {r['n_images']:4d} ảnh, "
                     f"tâm=({r['lat']:.6f}, {r['lon']:.6f}), "
                     f"bán kính {r['radius_km']:.2f}km")
    if unassigned:
        lines.append(f"  unassigned: {len(unassigned)} ảnh không có GPS")
    return "\n".join(lines)


def warn_if_suspicious(regions: "list[dict]", unassigned: "list[str]",
                       total: int) -> "list[str]":
    """Cảnh báo các tình huống làm pipeline chạy sai mà không báo lỗi."""
    warns = []
    if total and len(unassigned) / total > 0.2:
        warns.append(f"{len(unassigned)}/{total} ảnh không có GPS — "
                     "kiểm tra lại nguồn ảnh hoặc dùng --eps-km lớn hơn")
    small = [r["region"] for r in regions if r["n_images"] < 10]
    if small:
        warns.append(f"vùng quá nhỏ (<10 ảnh), COLMAP dễ fail: {', '.join(small)}")
    if len(regions) > 20:
        warns.append(f"{len(regions)} vùng — có thể eps_km quá nhỏ, "
                     "mỗi vùng sẽ tốn một lượt COLMAP riêng")
    return warns


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="thư mục ảnh gốc")
    ap.add_argument("--out", help="thư mục xuất vùng (mặc định <src>/../regions)")
    ap.add_argument("--eps-km", type=float, default=0.8,
                    help="ngưỡng khoảng cách gom vùng (km), mặc định 0.8")
    ap.add_argument("--report", action="store_true",
                    help="chỉ in báo cáo, không copy ảnh")
    ap.add_argument("--no-copy", action="store_true", help="không copy ảnh")
    args = ap.parse_args(argv)

    src = Path(args.src).expanduser().resolve()
    if not src.is_dir():
        print(f"LỖI: không thấy thư mục {src}", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser().resolve() if args.out else src.parent / "regions"

    photos, no_gps = scan_folder(src)
    if not photos:
        print("LỖI: không đọc được GPS của ảnh nào", file=sys.stderr)
        return 1

    regions = build_regions(photos, args.eps_km)
    print(summarize(regions, no_gps))
    total = len(photos) + len(no_gps)
    for w in warn_if_suspicious(regions, no_gps, total):
        print("CẢNH BÁO: " + w)

    if args.report:
        print("\n(chế độ --report: không ghi file)")
        return 0

    path = write_regions(src, out, regions, no_gps,
                         copy=not args.no_copy)
    payload = json.loads(path.read_text())
    payload["eps_km"] = args.eps_km
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nĐã ghi {path}")
    if not args.no_copy:
        print(f"Ảnh đã copy vào {out}/region_*/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
