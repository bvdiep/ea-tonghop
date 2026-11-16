"""Đo điểm bão hoà PSNR theo steps + ước tính chi phí TRƯỚC khi tiêu tiền.

Nguyên tắc: điểm bão hoà là câu hỏi "PSNR còn tăng theo steps nữa không", nên
phải đọc trên CÙNG MỘT quỹ đạo train. Vì vậy chạy MỘT lượt dài (mặc định 50k)
với `eval_every` đủ dày, rồi cắt ra các mốc 3k/15k/30k/50k — rẻ hơn nhiều so với
3 lượt chạy riêng (3 lượt = 3x GPU-time, mà 2 lượt đầu lặp lại đúng việc đã làm).

Có checkpoint/resume (TNG-002) nên một lượt dài bị preempt vẫn không mất tiến độ:
gọi lại lệnh là nó chạy tiếp từ ckpt gần nhất.

Ba chế độ, theo đúng thứ tự nên dùng:

  1. plan    — in cấu hình + ước tính GPU-giờ và tiền. KHÔNG gọi Modal.
  2. run     — chạy thật trên Modal (tốn tiền). In lệnh tương đương để kiểm tra.
  3. collect — đọc metrics.json/train_summary.json đã có, in bảng PSNR theo mốc
               và kết luận điểm bão hoà. KHÔNG gọi Modal.

Ví dụ:
    # xem kế hoạch và chi phí, chưa tốn đồng nào
    python psnr_sweep.py plan --subset 40 --target-steps 50000

    # chạy thật (chỉ khi đã đồng ý ngân sách)
    python psnr_sweep.py run --subset 40 --target-steps 50000 --yes

    # đọc kết quả đã có trên volume (sau khi tải về hoặc mount)
    python psnr_sweep.py collect --result-dir /vol/gsplat_s40_f1
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

MILESTONES = (3_000, 15_000, 30_000, 50_000)

# Giá GPU Modal (USD/giờ, tham khảo; đổi bằng --usd-per-hour nếu giá thay đổi).
GPU_PRICE_USD_PER_HOUR = {"T4": 0.59, "L4": 0.80, "A10": 1.10, "A100": 2.50}

# Thời gian train đo được thật trên bộ 40 ảnh (South-Building), DefaultStrategy:
# 1000 steps = 135s, 3000 steps = 380s, 15000 steps = 2126s.
# Từ các mốc này, chi phí mỗi 1000 steps tăng dần (gaussian nhiều lên) — mô hình
# dưới đây dùng nội suy tuyến tính theo đoạn, KHÔNG phải công thức lý thuyết.
_MEASURED = [(1_000, 135.0), (3_000, 380.0), (15_000, 2_126.0)]


def estimate_train_seconds(steps: int) -> float:
    """Ước tính thời gian train (giây) bằng nội suy từ số đo thật.

    Ngoài khoảng đo được thì ngoại suy theo tốc độ của đoạn cuối (đoạn 3k->15k,
    ~145.5s/1000 steps). Đây là ước tính, sai số thực tế ±30% tuỳ dữ liệu.
    """
    pts = _MEASURED
    if steps <= pts[0][0]:
        return pts[0][1] * steps / pts[0][0]
    for (s0, t0), (s1, t1) in zip(pts, pts[1:]):
        if steps <= s1:
            return t0 + (t1 - t0) * (steps - s0) / (s1 - s0)
    s0, t0 = pts[-2]
    s1, t1 = pts[-1]
    rate = (t1 - t0) / (s1 - s0)
    return t1 + rate * (steps - s1)


def estimate_run(steps: int, gpu: str, usd_per_hour: "float | None" = None,
                 colmap_cached: bool = True, colmap_images: int = 40,
                 per_step_scale: float = 1.0) -> dict:
    """Ước tính GPU-giờ và tiền cho một lượt chạy.

    `colmap_cached=True`: giả định COLMAP đã có trong cache volume (đúng khi
    chạy lại cùng subset). Nếu không, cộng thêm thời gian COLMAP mapper.

    `per_step_scale`: số đo gốc là bộ 40 ảnh (South-Building, 128 ảnh gốc). Với
    bộ lớn hơn (2500 ảnh drone, ảnh phân giải cao hơn, nhiều gaussian hơn), chi
    phí mỗi step tăng — ước tính 2-4x cho 2500 ảnh. Dùng cờ --per-step-scale để
    không phải nhân nhẩm, và nhớ đây vẫn là ước tính.
    """
    price = usd_per_hour if usd_per_hour is not None else GPU_PRICE_USD_PER_HOUR.get(gpu, 0.80)
    train_s = estimate_train_seconds(steps) * per_step_scale
    # COLMAP: 40 ảnh đo được mapper ~37-41s + extract/match ~40s => ~90s tổng.
    # Với n ảnh, mapper scale siêu tuyến — dùng ~2.2s/ảnh ở quy mô nhỏ, chặn dưới.
    colmap_s = 0.0 if colmap_cached else max(90.0, 2.2 * colmap_images)
    overhead_s = 120.0  # container start + import gsplat + volume commit
    total_s = train_s + colmap_s + overhead_s
    hours = total_s / 3600.0
    return {
        "gpu": gpu,
        "usd_per_hour": price,
        "train_s": round(train_s, 1),
        "colmap_s": round(colmap_s, 1),
        "overhead_s": overhead_s,
        "total_s": round(total_s, 1),
        "gpu_hours": round(hours, 2),
        "cost_usd": round(hours * price, 2),
        "colmap_cached": colmap_cached,
        "per_step_scale": per_step_scale,
    }


def milestones_from_metrics(metrics: "list[dict]") -> "list[dict]":
    """Chọn bản ghi metrics gần nhất tại/trước từng mốc steps."""
    if not metrics:
        return []
    recs = sorted(metrics, key=lambda r: r.get("step", 0))
    out = []
    for m in MILESTONES:
        cand = [r for r in recs if r.get("step", 0) <= m]
        if not cand:
            continue
        # lấy bản ghi sát mốc nhất (không lấy bản ghi sát cuối nếu vượt mốc)
        best = max(cand, key=lambda r: r.get("step", 0))
        out.append({
            "milestone": m,
            "step": best.get("step"),
            "psnr_val": best.get("psnr_val"),
            "ssim_val": best.get("ssim_val"),
            "n_gaussians": best.get("n_gaussians"),
        })
    return out


def saturation_verdict(rows: "list[dict]", min_gain_db: float = 0.3) -> dict:
    """Kết luận điểm bão hoà: mốc đầu tiên mà gain so với mốc trước < min_gain_db."""
    valid = [r for r in rows if isinstance(r.get("psnr_val"), (int, float))]
    if len(valid) < 2:
        return {"verdict": "insufficient_data", "detail": "cần ít nhất 2 mốc PSNR"}
    plateau_at = None
    for prev, cur in zip(valid, valid[1:]):
        gain = cur["psnr_val"] - prev["psnr_val"]
        cur["gain_db"] = round(gain, 3)
        if plateau_at is None and gain < min_gain_db:
            plateau_at = cur["step"]
    return {
        "verdict": "plateau" if plateau_at is not None else "still_improving",
        "plateau_step": plateau_at,
        "min_gain_db": min_gain_db,
        "note": ("PSNR tăng < %.1f dB giữa hai mốc liên tiếp => coi là bão hoà"
                 % min_gain_db),
    }


def render_table(rows: "list[dict]", config: "dict | None" = None) -> str:
    if not rows:
        return "(không có dữ liệu metrics)"
    head = "| steps | PSNR val | SSIM val | n_gaussians | gain dB |\n|---|---|---|---|---|"
    lines = [head]
    for r in rows:
        gain = r.get("gain_db")
        lines.append(
            f"| {r.get('step')} | {r.get('psnr_val')} | {r.get('ssim_val')} "
            f"| {r.get('n_gaussians')} | {'—' if gain is None else f'{gain:+.3f}'} |"
        )
    if config:
        lines.append("")
        lines.append("Cấu hình: " + json.dumps(config, ensure_ascii=False))
    return "\n".join(lines)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def cmd_plan(args) -> int:
    prof_gpu = "L4" if args.subset > 100 else "T4"
    gpu = args.gpu or prof_gpu
    est = estimate_run(args.target_steps, gpu, args.usd_per_hour,
                       colmap_cached=args.colmap_cached,
                       colmap_images=args.subset,
                       per_step_scale=args.per_step_scale)
    print("=== KẾ HOẠCH (chưa gọi Modal, chưa tốn tiền) ===")
    print(f"subset={args.subset} target_steps={args.target_steps} "
          f"eval_every={args.eval_every} data_factor={args.data_factor}")
    print(f"refine_stop={args.refine_stop or 'auto (min(max_steps*0.5,15000))'} "
          f"grow_grad2d={args.grow_grad2d} grow_scale3d={args.grow_scale3d}")
    if args.per_step_scale != 1.0:
        print(f"per_step_scale={args.per_step_scale} (bộ lớn hơn bộ đo gốc 40 ảnh)")
    print()
    print("--- Ước tính thời gian/chi phí ---")
    print(f"train      : {est['train_s']:.0f}s ({est['train_s']/3600:.2f}h)")
    print(f"colmap     : {est['colmap_s']:.0f}s"
          f"{' (cache hit)' if est['colmap_cached'] else ' (chạy lại từ đầu)'}")
    print(f"overhead   : {est['overhead_s']}s")
    print(f"TỔNG       : {est['total_s']:.0f}s = {est['gpu_hours']} GPU-giờ "
          f"trên {est['gpu']}")
    print(f"CHI PHÍ    : ~${est['cost_usd']} (${est['usd_per_hour']}/h)")
    print()
    print("Lưu ý: đây là một lượt chạy duy nhất, không phải 3 lượt 15k/30k/50k.")
    print("Checkpoint mỗi 1000 steps nên preempt chỉ mất tối đa 1000 steps.")
    print("Sai số ước tính ±30% (nội suy từ 3 mốc đo thật trên bộ 40 ảnh).")
    print()
    print("Lệnh chạy thật tương đương:")
    fn = "run_pipeline_scaled" if args.subset > 100 else "run_pipeline"
    extra = ""
    if args.refine_stop:
        extra += f" --refine_stop {args.refine_stop}"
    print(f"  modal run gsplat_app.py::main --subset {args.subset} "
          f"--max_steps {args.target_steps} --data_factor {args.data_factor}{extra}")
    print(f"  (function: {fn})")
    return 0


def cmd_run(args) -> int:
    if not args.yes:
        est = estimate_run(args.target_steps, args.gpu or "T4", args.usd_per_hour,
                           colmap_cached=args.colmap_cached,
                           colmap_images=args.subset,
                           per_step_scale=args.per_step_scale)
        print(f"Sẽ tốn khoảng ${est['cost_usd']} ({est['gpu_hours']} GPU-giờ).")
        print("Thêm --yes để thực sự chạy, hoặc dùng `plan` để xem chi tiết.")
        return 1
    try:
        import modal
    except ImportError:
        print("LỖI: chưa cài modal (pip install modal)", file=sys.stderr)
        return 2
    fn_name = "run_pipeline_scaled" if args.subset > 100 else "run_pipeline"
    print(f"Gọi Modal: app=s3dgs-gsplat fn={fn_name} subset={args.subset} "
          f"max_steps={args.target_steps}")
    fn = modal.Function.from_name("s3dgs-gsplat", fn_name)
    result = fn.remote(args.subset, args.target_steps, True,
                       args.ckpt_every, args.data_factor,
                       args.refine_stop, args.grow_grad2d, args.grow_scale3d)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    rows = milestones_from_metrics(result.get("metrics") or [])
    verdict = saturation_verdict(rows)
    print()
    print(render_table(rows, (result.get("train_summary") or {}).get("config")))
    print()
    print("Kết luận: " + json.dumps(verdict, ensure_ascii=False))
    return 0


def cmd_collect(args) -> int:
    d = Path(args.result_dir).expanduser()
    metrics = _load_json(d / "metrics.json") or []
    summary = _load_json(d / "train_summary.json") or {}
    if not metrics:
        print(f"LỖI: không đọc được {d/'metrics.json'}", file=sys.stderr)
        return 2
    rows = milestones_from_metrics(metrics)
    verdict = saturation_verdict(rows)
    print(render_table(rows, summary.get("config")))
    print()
    print("Kết luận: " + json.dumps(verdict, ensure_ascii=False))
    if summary:
        print(f"\nTổng: {len(metrics)} bản ghi metrics, "
              f"final step {summary.get('steps')}, "
              f"PSNR cuối {summary.get('psnr_val_final')}, "
              f"n_gaussians {summary.get('n_gaussians')}, "
              f"train {summary.get('train_time_s')}s")
    return 0


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--subset", type=int, default=40, help="số ảnh dùng")
        p.add_argument("--target-steps", type=int, default=50_000)
        p.add_argument("--eval-every", type=int, default=500)
        p.add_argument("--data-factor", type=int, default=1)
        p.add_argument("--ckpt-every", type=int, default=1000)
        p.add_argument("--refine-stop", type=int, default=None,
                       help="pin refine_stop cho mọi lượt (nên 20000-25000 với drone)")
        p.add_argument("--grow-grad2d", type=float, default=0.0002)
        p.add_argument("--grow-scale3d", type=float, default=0.01)
        p.add_argument("--gpu", default=None, help="T4/L4/A10 (mặc định theo subset)")
        p.add_argument("--usd-per-hour", type=float, default=None)
        p.add_argument("--colmap-cached", action="store_true", default=True)
        p.add_argument("--no-colmap-cached", dest="colmap_cached", action="store_false")
        p.add_argument("--per-step-scale", type=float, default=1.0,
                       help="hệ số chi phí mỗi step so với bộ đo gốc 40 ảnh "
                            "(2500 ảnh drone: dùng 2-4)")

    p_plan = sub.add_parser("plan", help="in kế hoạch + chi phí, không gọi Modal")
    add_common(p_plan)
    p_plan.set_defaults(func=cmd_plan)

    p_run = sub.add_parser("run", help="chạy thật trên Modal")
    add_common(p_run)
    p_run.add_argument("--yes", action="store_true", help="xác nhận chi phí")
    p_run.set_defaults(func=cmd_run)

    p_col = sub.add_parser("collect", help="đọc metrics.json đã có, in bảng PSNR")
    p_col.add_argument("--result-dir", required=True)
    p_col.set_defaults(func=cmd_collect)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
