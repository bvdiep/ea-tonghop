# Kế hoạch: Pipeline 3DGS production-ready trên Modal Labs

Trạng thái: draft
Ngày: 2026-11-13
Phạm vi: `spike-3dgs-modal/` (đã có code chạy được), hướng tới bộ dữ liệu thật ~20GB

## 1. Hiện trạng đã đo được (baseline thật, không ước lượng)

### 1.1 Chất lượng

| strategy | steps | n_gaussians | PSNR cuối | train time (trong container) |
|---|---|---|---|---|
| MCMCStrategy | 3.000 | 21.162 | 16.32 | 405s |
| MCMCStrategy | 30.000 | 21.177 | không đọc được | 4.195s |
| DefaultStrategy | 1.000 | 21.164 | 18.35 | 135s |
| DefaultStrategy | 3.000 | 50.824 | 21.03 | 380s |
| DefaultStrategy | 15.000 | 218.707 | không đọc được | 2.126s |

Kết luận: chuyển MCMC → DefaultStrategy là thay đổi quyết định (+29% PSNR ở cùng 3.000 steps,
số gaussian tăng 4x). MCMC chỉ teleport gaussian chết, không split/duplicate theo gradient
nên số lượng đứng yên vĩnh viễn ở ~21k.

### 1.2 Chi phí GPU thực tế bị đốt

Lượt 15.000 steps: `wall_clock_s` trong JSON là 2.204s (37 phút) nhưng **GPU thực tế bị
tính ~76 phút**. Nguyên nhân: container bị **preemption 2 lần**, mỗi lần Modal restart
function với cùng input → chạy lại COLMAP từ đầu.

Bằng chứng từ `modal app logs ap-8ttrL2LOLIAaL9q4rlAClB`:

```
08:57 UTC  lần 1: download 3.7s → mapper 37.0s → gsplat import → PREEMPTED
09:25 UTC  lần 2: download 2.7s → mapper 32.7s → gsplat import → PREEMPTED
09:36 UTC  lần 3: download 12.1s → mapper 41.3s → train 2126.4s → OK
```

Log ghi rõ:
```
Container terminated due to preemption. Your Function will be restarted with the same input.
```

Đây là preemption của Modal (hạ tầng), không phải bug code và không phải OOM.

### 1.3 Hệ quả cho bộ 20GB (~2.000–3.000 ảnh)

Ước tính cũ (8–20h) chỉ cộng phần compute, bỏ qua:
- preemption: với job 8–20h, xác suất bị preempt gần như chắc chắn, và mỗi lần mất trắng
  toàn bộ tiến độ train
- queue chờ GPU (L4 đã từng chờ 35–60+ phút)
- COLMAP mapper với 2.500 ảnh có thể cần 16–32GB RAM (cấu hình hiện tại chỉ 8GB)

Không có checkpoint thì một lần preempt ở giờ thứ 10 = mất 10 giờ GPU.

## 2. Nguyên nhân gốc của các vấn đề còn lại

### 2.1 Không có checkpoint/resume (P0)

`gsplat_app.py:171` `run_pipeline()` là một hàm nguyên khối: COLMAP → train → ghi PLY.
Modal preemption restart từ đầu hàm. Không có:
- lưu trạng thái COLMAP (`database.db`, `sparse/`) để bỏ qua stage 1
- lưu `params` dict + step counter trong train để resume giữa chừng

`train_gsplat.py` có `torch.save(ckpt, ...)` ở cuối (dòng ~292) nhưng chỉ lưu **một lần khi
train xong** — vô dụng khi bị preempt.

### 2.2 Không đọc được PSNR khi chạy dài (P1)

`train_gsplat.py` in PSNR ra stdout, nhưng `run_pipeline` gọi qua `sh()` (subprocess) nên
stdout bị buffer, chỉ trả về khi process kết thúc. `modal app logs` cũng không thấy vì log
nằm trong subprocess. Hệ quả: với job dài không biết được chất lượng cho đến khi xong,
không phát hiện sớm được phân kỳ.

### 2.3 Cấu hình tài nguyên chưa đủ cho dữ liệu thật (P0)

`gsplat_app.py:169` hard-code `cpu=2, memory=8192, gpu="T4"` cho mọi lượt. Với 2.500 ảnh:
- COLMAP mapper có thể OOM ở 8GB
- T4 (16GB VRAM) không đủ cho 200k+ gaussians ở resolution gốc 3072x2304
- L4/A10 cần thiết cho train, nhưng queue lâu

### 2.4 Chưa có eval/val split và metric chuẩn (P1)

PSNR hiện tính trên `train_ds[0]` (một ảnh train) — không phải val, và chỉ 1 ảnh nên
nhiễu. Không có khả năng so sánh khách quan giữa các cấu hình.

## 3. Kế hoạch triển khai

### P0 — Bắt buộc trước khi chạy dữ liệu thật

#### 3.1 Checkpoint COLMAP vào volume

Sau khi COLMAP xong, copy `database.db` + `sparse/0/` + `images/` vào `/vol/colmap_cache_s{subset}/`.
Đầu `run_pipeline`, kiểm tra cache: nếu có và số ảnh khớp thì bỏ qua stage 1.
Tiết kiệm ~50s mỗi lần restart — nhỏ, nhưng là tiền đề cho 3.2.

#### 3.2 Checkpoint train + resume

- `train_gsplat.py` nhận thêm `--resume` và `--ckpt_every N` (mặc định 1.000)
- Mỗi N steps: `torch.save({params, optimizers state, strategy_state, step, psnr_log})` vào
  `result_dir/ckpt_{step}.pt`
- Khi khởi động: nếu có `ckpt_latest.pt` thì load và tiếp tục từ step đó
- `run_pipeline` truyền `result_dir` trỏ thẳng vào `/vol/` để checkpoint sống sót qua restart
- Ghi `train.log` (không phải stdout) vào `/vol/` để theo dõi tiến độ real-time

Đây là hạng mục quan trọng nhất: nó biến preemption từ "mất trắng" thành "mất tối đa N steps".

#### 3.3 Tách function theo stage, mỗi stage ngắn

Thay vì một `run_pipeline` khối lớn, tách:
- `stage_colmap(subset)` → ghi cache, trả path
- `stage_train(subset, max_steps, resume=True)` → có checkpoint, chạy tối đa ~3.000 steps
  mỗi lần gọi
- `stage_export(subset, steps)` → PLY

Orchestrator (local entrypoint hoặc một function điều phối) gọi tuần tự, mỗi lần kiểm tra
volume. Preempt chỉ mất một đoạn ngắn, lần sau tiếp tục.

#### 3.4 Cấu hình tài nguyên theo quy mô

Tham số hoá thay vì hard-code:
- ≤100 ảnh: T4, cpu=2, memory=8192
- 100–1.000 ảnh: L4, cpu=8, memory=32768
- >1.000 ảnh: A10/L4, cpu=16, memory=65536, và bắt buộc chia vùng theo GPS

#### 3.5 Val split + eval chuẩn

- Tách 10% ảnh làm val ngay sau COLMAP (deterministic theo seed)
- Tính PSNR/SSIM/LPIPS trên toàn val set, log mỗi `eval_every`
- Ghi vào `metrics.json` trong volume sau mỗi lần eval để theo dõi được từ ngoài

### P1 — Cải thiện chất lượng và vận hành

#### 3.6 Tăng steps và densify budget

- `refine_stop_iter` hiện là `min(max_steps*0.5, 15000)`. Với dữ liệu thật nên cho
  refine đến 20.000–25.000 steps.
- Đo PSNR ở 15k/30k/50k để tìm điểm bão hoà thay vì đoán.

#### 3.7 data_factor cho ảnh drone độ phân giải cao

Ảnh 3072x2304 với 200k gaussians sẽ OOM trên T4. Thêm `--data_factor 2` (hoặc 4) để
giảm resolution khi train, giữ nguyên khi render cuối nếu cần.

#### 3.8 Chia vùng theo GPS cho dữ liệu drone

Với ~2.500 ảnh drone phủ vùng rộng, `spatial_matcher` + mapper có thể tách thành nhiều
model rời rạc. Cần: đọc GPS từ EXIF, cluster theo khoảng cách, chạy COLMAP riêng từng
vùng, và merge hoặc export nhiều PLY.

#### 3.9 Giới hạn thời gian mỗi function để giảm preempt

`@app.function(timeout=...)` nên đặt ngắn hơn (ví dụ 2h) và để orchestrator gọi lại nhiều
lần. Function càng dài, xác suất bị preempt giữa chừng càng cao.

## 4. Thứ tự thực thi đề xuất

1. 3.2 (checkpoint train + resume) — giá trị cao nhất
2. 3.1 (cache COLMAP) — rẻ, hỗ trợ 3.2
3. 3.5 (val split + metrics) — cần để đo được mọi cải tiến sau
4. 3.4 (tài nguyên theo quy mô) — cần trước khi thử dữ liệu thật
5. 3.6 + 3.7 (steps, data_factor) — tối ưu chất lượng
6. 3.3 (tách stage) — làm cùng 3.2
7. 3.8 (chia vùng GPS) — chỉ khi thử dữ liệu thật và thấy mapper tách model

## 5. Ngoài phạm vi

- Viewer/web hiển thị splat: chưa bàn, chỉ xuất PLY
- Huấn luyện phân tán nhiều GPU: chưa cần ở quy mô này
- Thay gsplat bằng renderer khác (LichtFeld, nerfstudio): đã loại vì lý do kỹ thuật

## 6. Rủi ro

| rủi ro | mức | giảm thiểu |
|---|---|---|
| Preemption giữa train mất tiến độ | cao | checkpoint 3.2 |
| COLMAP mapper OOM với 2.500 ảnh | cao | tăng RAM 3.4, chia vùng 3.8 |
| T4 hết VRAM với ảnh gốc | cao | data_factor 3.7 |
| Queue L4 chờ lâu | trung bình | dùng T4 cho thử nghiệm, L4 cho chạy cuối |
| Không biết chất lượng khi đang chạy | trung bình | metrics.json 3.5 + train.log 3.2 |

## 7. Tiêu chí nghiệm thu

- Job 15.000 steps chạy qua ít nhất một lần preemption mà không mất tiến độ train
- `metrics.json` có PSNR val sau mỗi `eval_every`, đọc được từ ngoài khi job đang chạy
- Chạy được bộ 2.500 ảnh không OOM ở stage COLMAP
- Tổng GPU-time cho một lượt chạy báo cáo được chính xác (không phải chỉ wall_clock)
