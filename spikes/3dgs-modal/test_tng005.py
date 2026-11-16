"""Test gps_regions.py + psnr_sweep.py — không cần GPU, không cần COLMAP.

Chạy: .venv/bin/python -m pytest test_tng005.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import gps_regions as gr  # noqa: E402
import psnr_sweep as ps  # noqa: E402


def _make_jpeg(path: Path, lat=None, lon=None):
    """Tạo JPEG 8x8, gắn GPS EXIF nếu có lat/lon."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (8, 8), (120, 130, 140))
    exif = Image.Exif()
    if lat is not None and lon is not None:
        def dms(v):
            v = abs(v)
            d = int(v)
            m = int((v - d) * 60)
            s = round(((v - d) * 60 - m) * 60, 4)
            return (float(d), float(m), float(s))
        exif[0x8825] = {
            1: "N" if lat >= 0 else "S",
            2: dms(lat),
            3: "E" if lon >= 0 else "W",
            4: dms(lon),
        }
    img.save(path, "JPEG", exif=exif)


# ---------- GPS reading ----------

def test_read_gps_roundtrip(tmp_path):
    p = tmp_path / "a.jpg"
    _make_jpeg(p, 21.027764, 105.834160)  # Hà Nội
    ll = gr.read_gps(p)
    assert ll is not None
    lat, lon = ll
    assert abs(lat - 21.027764) < 1e-4
    assert abs(lon - 105.834160) < 1e-4


def test_read_gps_south_west_negated(tmp_path):
    p = tmp_path / "b.jpg"
    # Buenos Aires: lat âm, lon âm
    _make_jpeg(p, -34.603684, -58.381559)
    lat, lon = gr.read_gps(p)
    assert lat < 0 and lon < 0
    assert abs(lat + 34.603684) < 1e-4
    assert abs(lon + 58.381559) < 1e-4


def test_read_gps_missing_returns_none(tmp_path):
    p = tmp_path / "c.jpg"
    _make_jpeg(p)
    assert gr.read_gps(p) is None


def test_read_gps_null_island_rejected(tmp_path):
    p = tmp_path / "d.jpg"
    _make_jpeg(p, 0.0, 0.0)
    assert gr.read_gps(p) is None


def test_read_gps_non_image_returns_none(tmp_path):
    p = tmp_path / "e.jpg"
    p.write_bytes(b"not an image")
    assert gr.read_gps(p) is None


# ---------- clustering ----------

def test_haversine_known_distance():
    # Hà Nội -> TP.HCM ~ 1140 km (đường chim bay ~1137)
    d = gr.haversine_km(21.0278, 105.8342, 10.8231, 106.6297)
    assert 1120 < float(d) < 1160


def test_cluster_separates_two_areas():
    pts = np.array([
        [21.0277, 105.8341], [21.0280, 105.8345], [21.0279, 105.8343],
        [10.8231, 106.6297], [10.8235, 106.6300],
    ])
    groups = gr.cluster_by_distance(pts, eps_km=0.8)
    assert len(groups) == 2
    assert sorted(len(g) for g in groups) == [2, 3]


def test_cluster_single_link_chains_sequential_flight():
    """Ảnh bay theo dải: mỗi ảnh cách nhau 0.3km, cả dải 3km.
    Với eps=0.5km thì single-link gom hết thành 1 vùng (đúng: chúng liền nhau),
    centroid-link sẽ cắt thành nhiều mảnh — đó là cái ta muốn tránh.
    """
    lats = [21.0 + i * 0.0027 for i in range(11)]  # ~0.3km mỗi bước
    pts = np.array([[la, 105.83] for la in lats])
    groups = gr.cluster_by_distance(pts, eps_km=0.5)
    assert len(groups) == 1
    assert len(groups[0]) == 11


def test_cluster_eps_too_small_splits(tmp_path):
    lats = [21.0 + i * 0.0027 for i in range(11)]
    pts = np.array([[la, 105.83] for la in lats])
    # eps nhỏ hơn khoảng cách giữa 2 ảnh liên tiếp -> mỗi ảnh một vùng
    groups = gr.cluster_by_distance(pts, eps_km=0.1)
    assert len(groups) == 11


def test_cluster_empty_and_single():
    assert gr.cluster_by_distance(np.zeros((0, 2)), 1.0) == []
    assert gr.cluster_by_distance(np.array([[21.0, 105.0]]), 1.0) == [[0]]


def test_cluster_deterministic_ordering():
    pts = np.array([[21.0, 105.0], [10.0, 106.0], [10.001, 106.001]])
    a = gr.cluster_by_distance(pts, 0.8)
    b = gr.cluster_by_distance(pts, 0.8)
    assert a == b
    assert len(a[0]) == 2  # vùng lớn đứng trước


# ---------- end to end: scan + build + write ----------

def test_end_to_end_two_regions(tmp_path):
    src = tmp_path / "src"
    _make_jpeg(src / "sub" / "h1.jpg", 21.0277, 105.8341)
    _make_jpeg(src / "sub" / "h2.jpg", 21.0279, 105.8344)
    _make_jpeg(src / "s1.jpg", 10.8231, 106.6297)
    _make_jpeg(src / "s2.jpg", 10.8234, 106.6301)
    _make_jpeg(src / "nogps.jpg")

    photos, no_gps = gr.scan_folder(src)
    assert len(photos) == 4
    assert no_gps == ["nogps.jpg"]

    regions = gr.build_regions(photos, eps_km=0.8)
    assert len(regions) == 2
    assert sum(r["n_images"] for r in regions) == 4
    for r in regions:
        assert r["bbox"]["lat_min"] <= r["bbox"]["lat_max"]
        assert r["radius_km"] >= 0

    out = tmp_path / "out"
    path = gr.write_regions(src, out, regions, no_gps, copy=True)
    data = json.loads(path.read_text())
    assert data["n_assigned"] == 4
    assert data["n_unassigned"] == 1
    assert (out / "region_00").is_dir()
    assert (out / "region_01").is_dir()
    assert (out / "unassigned" / "nogps.jpg").is_file()
    # ảnh trong sub/ được flatten về tên file (COLMAP cần 1 thư mục phẳng)
    assert len(list((out / "region_00").glob("*.jpg"))) == 2


def test_write_regions_no_copy(tmp_path):
    src = tmp_path / "src"
    _make_jpeg(src / "a.jpg", 21.0, 105.0)
    photos, no_gps = gr.scan_folder(src)
    regions = gr.build_regions(photos, 0.8)
    out = tmp_path / "out"
    gr.write_regions(src, out, regions, no_gps, copy=False)
    assert not (out / "region_00").exists()
    assert (out / "regions.json").is_file()


def test_cli_report_mode(tmp_path, capsys):
    src = tmp_path / "src"
    _make_jpeg(src / "a.jpg", 21.0, 105.0)
    _make_jpeg(src / "b.jpg", 21.0005, 105.0005)
    rc = gr.main(["--src", str(src), "--report"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "1 vùng" in out


def test_cli_no_gps_fails(tmp_path):
    src = tmp_path / "src"
    _make_jpeg(src / "a.jpg")
    assert gr.main(["--src", str(src), "--report"]) == 1


def test_warn_suspicious_many_unassigned():
    regions = [{"region": "region_00", "n_images": 100}]
    warns = gr.warn_if_suspicious(regions, ["x"] * 50, 150)
    assert any("không có GPS" in w for w in warns)


def test_warn_suspicious_small_region():
    regions = [{"region": "region_00", "n_images": 3}]
    warns = gr.warn_if_suspicious(regions, [], 3)
    assert any("quá nhỏ" in w for w in warns)


# ---------- psnr_sweep ----------

def test_estimate_train_seconds_matches_measurements():
    for steps, expect in ps._MEASURED:
        got = ps.estimate_train_seconds(steps)
        assert abs(got - expect) < 1e-6, (steps, got, expect)


def test_estimate_train_seconds_monotonic():
    vals = [ps.estimate_train_seconds(s) for s in (500, 1000, 3000, 15000, 30000, 50000)]
    assert vals == sorted(vals)
    assert all(b > a for a, b in zip(vals, vals[1:]))


def test_estimate_run_cost_positive():
    est = ps.estimate_run(50_000, "T4")
    assert est["gpu_hours"] > 0
    assert est["cost_usd"] > 0
    assert est["total_s"] == pytest.approx(
        est["train_s"] + est["colmap_s"] + est["overhead_s"], rel=1e-6)


def test_estimate_run_colmap_cache_saves_time():
    a = ps.estimate_run(50_000, "T4", colmap_cached=True, colmap_images=2500)
    b = ps.estimate_run(50_000, "T4", colmap_cached=False, colmap_images=2500)
    assert a["total_s"] < b["total_s"]
    assert a["colmap_s"] == 0.0


def test_milestones_from_metrics():
    metrics = [
        {"step": 500, "psnr_val": 16.1, "ssim_val": 0.5, "n_gaussians": 21000},
        {"step": 3000, "psnr_val": 21.0, "ssim_val": 0.7, "n_gaussians": 50000},
        {"step": 15000, "psnr_val": 26.4, "ssim_val": 0.85, "n_gaussians": 218000},
        {"step": 30000, "psnr_val": 27.0, "ssim_val": 0.87, "n_gaussians": 300000},
        {"step": 50000, "psnr_val": 27.1, "ssim_val": 0.875, "n_gaussians": 320000},
    ]
    rows = ps.milestones_from_metrics(metrics)
    assert [r["step"] for r in rows] == [3000, 15000, 30000, 50000]


def test_milestones_uses_closest_not_overshoot():
    """Mốc 3000 phải lấy bản ghi step<=3000 gần nhất, không lấy step 3500."""
    metrics = [{"step": 2800, "psnr_val": 20.0}, {"step": 3500, "psnr_val": 22.0}]
    rows = ps.milestones_from_metrics(metrics)
    assert rows[0]["step"] == 2800


def test_saturation_detects_plateau():
    rows = [
        {"step": 3000, "psnr_val": 21.0},
        {"step": 15000, "psnr_val": 26.4},
        {"step": 30000, "psnr_val": 27.0},
        {"step": 50000, "psnr_val": 27.1},  # chỉ +0.1 dB
    ]
    v = ps.saturation_verdict(rows, min_gain_db=0.3)
    assert v["verdict"] == "plateau"
    assert v["plateau_step"] == 50000


def test_saturation_still_improving():
    rows = [
        {"step": 3000, "psnr_val": 21.0},
        {"step": 15000, "psnr_val": 26.4},
        {"step": 30000, "psnr_val": 28.5},
    ]
    v = ps.saturation_verdict(rows, min_gain_db=0.3)
    assert v["verdict"] == "still_improving"
    assert v["plateau_step"] is None


def test_saturation_insufficient_data():
    assert ps.saturation_verdict([])["verdict"] == "insufficient_data"
    assert ps.saturation_verdict([{"step": 1, "psnr_val": 1.0}])["verdict"] == "insufficient_data"


def test_render_table_has_all_rows():
    rows = [{"step": 3000, "psnr_val": 21.0, "ssim_val": 0.7,
             "n_gaussians": 50000, "gain_db": None}]
    t = ps.render_table(rows)
    assert "| 3000 | 21.0 |" in t


def test_collect_reads_real_files(tmp_path):
    (tmp_path / "metrics.json").write_text(json.dumps([
        {"step": 3000, "psnr_val": 21.0, "ssim_val": 0.7, "n_gaussians": 50000},
        {"step": 15000, "psnr_val": 26.4, "ssim_val": 0.85, "n_gaussians": 218000},
    ]))
    (tmp_path / "train_summary.json").write_text(json.dumps({
        "steps": 15000, "psnr_val_final": 26.4, "n_gaussians": 218000,
        "train_time_s": 2126.0, "config": {"refine_stop": 15000},
    }))
    assert ps.main(["collect", "--result-dir", str(tmp_path)]) == 0


def test_collect_missing_metrics_returns_error(tmp_path, capsys):
    assert ps.main(["collect", "--result-dir", str(tmp_path)]) == 2


def test_plan_mode_does_not_touch_modal(capsys):
    """plan phải chạy được khi KHÔNG cài modal — chứng minh không gọi Modal."""
    assert ps.main(["plan", "--subset", "40", "--target-steps", "50000"]) == 0
    out = capsys.readouterr().out
    assert "CHI PHÍ" in out
    assert "modal run" in out


def test_run_refuses_without_yes(capsys):
    assert ps.main(["run", "--subset", "40", "--target-steps", "1000"]) == 1
    out = capsys.readouterr().out
    assert "--yes" in out
