# TNG-005 — Công cụ đo điểm bão hoà PSNR + chia vùng GPS

Hai script, cả hai chạy được **offline, không cần GPU**:

- `psnr_sweep.py` — lập kế hoạch chi phí, chạy sweep, đọc bảng PSNR theo mốc
- `gps_regions.py` — chia ảnh drone thành vùng theo GPS EXIF

## psnr_sweep.py

Ba chế độ, dùng đúng thứ tự này:

```bash
# 1. Xem chi phí. KHÔNG gọi Modal, không tốn tiền.
python psnr_sweep.py plan --subset 40 --target-steps 50000

# 2. Chạy thật (tốn tiền). Không có --yes thì nó chỉ in chi phí rồi thoát.
python psnr_sweep.py run --subset 40 --target-steps 50000 --yes

# 3. Đọc metrics.json đã có, in bảng + kết luận điểm bão hoà.
python psnr_sweep.py collect --result-dir /vol/gsplat_s40_f1
```

Vì sao **một lượt dài** thay vì 3 lượt 15k/30k/50k: điểm bão hoà là câu hỏi
"PSNR còn tăng theo steps không", phải đọc trên cùng một quỹ đạo train. Ba lượt
riêng vừa tốn 3x GPU, vừa so sánh 3 quỹ đạo khác nhau. Một lượt 50k với
`eval_every=500` cho PSNR ở mọi mốc cần đo, và checkpoint mỗi 1000 steps
(TNG-002) nên preempt chỉ mất tối đa 1000 steps.

Ước tính chi phí nội suy từ 3 mốc đo thật trên bộ 40 ảnh
(1k=135s, 3k=380s, 15k=2126s), ngoại suy tuyến tính ngoài khoảng đó. Sai số ±30%.
Với bộ lớn hơn dùng `--per-step-scale 2..4` vì mỗi step đắt hơn (nhiều gaussian
hơn, ảnh phân giải cao hơn).

### Tham số mới trong train_gsplat.py

`--refine_stop`, `--grow_grad2d`, `--grow_scale3d` — trước đây hard-code. Cần
tham số hoá để đo điểm bão hoà ở nhiều cấu hình và chỉnh cho ảnh drone (độ phân
giải cao → gaussian nhỏ hơn → có thể cần `grow_grad2d` thấp hơn 0.0002).

`train_summary.json` giờ ghi thêm khối `config` để bảng PSNR có ngữ cảnh — cùng
PSNR nhưng `refine_stop` khác nhau là kết quả khác nhau.

`result_dir` trên volume có thêm tag cấu hình (`_rs20000`, `_gg0.0001`): hai cấu
hình densify khác nhau là hai scene khác nhau, không được resume chéo.

## gps_regions.py

```bash
# chỉ xem, không copy
python gps_regions.py --src /data/drone --report

# chia vùng và copy ảnh
python gps_regions.py --src /data/drone --out /data/regions --eps-km 0.8
```

Dùng single-link clustering (union-find) chứ không k-means: mục tiêu là "ảnh
liền kề về vị trí thuộc cùng scene", k-means sẽ cắt ngang dải bay và tách rời
ảnh kề nhau — đúng cái cần tránh.

Ảnh không có GPS được đưa vào `unassigned/`, **không** gán bừa vào vùng gần
nhất (ảnh thiếu GPS thường là ảnh scan phụ, gán sai sẽ làm bẩn model).

Cảnh báo tự động khi: >20% ảnh không GPS, có vùng <10 ảnh (COLMAP dễ fail),
hoặc số vùng >20 (eps quá nhỏ).

## Chạy test

```bash
cd spikes/3dgs-modal
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python numpy pillow pytest
.venv/bin/python -m pytest test_tng005.py -q     # 31 test
```

Test dùng ảnh JPEG tổng hợp có EXIF GPS thật (Pillow ghi được IFD GPSInfo), nên
kiểm được cả trường hợp toạ độ âm (Nam/Tây) và EXIF rác (0,0).

## Còn phải làm (cần dữ liệu thật)

- Chạy `psnr_sweep.py run` trên bộ ảnh để có bảng PSNR thật → AC thứ nhất
- Chạy `gps_regions.py` trên 2500 ảnh drone → kiểm chứng số vùng hợp lý
- Chạy COLMAP riêng từng vùng, xem có model rời rạc không
