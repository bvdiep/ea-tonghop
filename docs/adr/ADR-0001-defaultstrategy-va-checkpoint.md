# ADR-0001: Dùng DefaultStrategy thay MCMCStrategy cho densify, và checkpoint bắt buộc trên Modal

Trạng thái: Proposed (draft)
Ngày: 2026-11-13

## Bối cảnh

Pipeline 3DGS trên Modal Labs (`spike-3dgs-modal/`) đã chạy được trọn vẹn COLMAP + gsplat
trên subset COLMAP South-Building. Nhưng chất lượng dừng ở PSNR 16.32 với 3.000 steps và
**không tăng** khi chạy 30.000 steps — số gaussian giữ nguyên 21.162 suốt quá trình.

Đồng thời, khi chạy job dài (15.000 steps), Modal preempt container 2 lần. Mỗi lần function
bị restart với cùng input, nên `run_pipeline()` chạy lại COLMAP từ đầu và mất toàn bộ tiến
độ train. Chi phí GPU thực tế 76 phút trong khi chỉ 37 phút sinh ra kết quả.

## Quyết định

### 1. Dùng `DefaultStrategy` (split/duplicate theo gradient), không dùng `MCMCStrategy`

`MCMCStrategy` chỉ relocate gaussian có opacity thấp (teleport sang vị trí gaussian còn
sống), không tạo thêm gaussian ở vùng gradient cao. Vì vậy số lượng gaussian bị chốt ở số
khởi tạo ban đầu và chất lượng bão hoà sớm.

`DefaultStrategy` là cơ chế densify của 3DGS gốc: duplicate gaussian nhỏ ở vùng gradient
 lớn, split gaussian lớn, prune gaussian trong suốt. Đo được: cùng 3.000 steps, PSNR
16.32 → 21.03, gaussian 21.162 → 50.824.

### 2. `params` dict là nguồn sự thật duy nhất, không dùng biến local

`DefaultStrategy.step_post_backward()` **thay thế** `nn.Parameter` trong dict khi densify.
Biến local trỏ tới tensor cũ sẽ stale ngay sau lần grow đầu tiên. Mọi render, eval, và ghi
PLY phải đọc qua `params["means"]`, `params["scales"]`, v.v.

Kèm theo: optimizer phải tách riêng từng tensor (mỗi optimizer đúng 1 param_group) vì
`Strategy.check_sanity()` yêu cầu vậy.

### 3. Checkpoint là bắt buộc, không phải tối ưu hoá

Modal preemption là hành vi hạ tầng bình thường, không phải lỗi. Với job 8–20h, preempt
gần như chắc chắn xảy ra. Không có checkpoint nghĩa là mỗi lần preempt mất toàn bộ GPU-time
đã tiêu cho train.

Do đó: `train_gsplat.py` phải lưu `ckpt_{step}.pt` (params + optimizer state +
strategy_state + step) định kỳ vào volume, và resume được khi restart. `run_pipeline`
không được là hàm nguyên khối COLMAP+train mà phải kiểm tra cache/checkpoint ở mỗi stage.

### 4. Báo cáo chi phí phải tách wall-clock nội bộ và GPU-time thực

`wall_clock_s` đo bên trong function bỏ qua preemption, queue, và restart. Mọi báo cáo chi
phí cho user/khách phải dùng timestamp thật từ `modal app logs` (dòng `I20261113 hh:mm:ss`)
để tính tổng khoảng thời gian GPU bị tính tiền.

## Hệ quả

### Tích cực
- Chất lượng tăng đáng kể (+29% PSNR ở cùng số steps), còn dư địa tăng tiếp
- Preemption chỉ mất tối đa `ckpt_every` steps thay vì toàn bộ
- Số liệu chi phí trung thực, lập kế hoạch được cho bộ 20GB

### Tiêu cực / đánh đổi
- Code phức tạp hơn: phải quản lý params dict, optimizer state, strategy_state khi resume
- Checkpoint 200k+ gaussians với SH degree 3 tốn ~130MB mỗi file; cần giới hạn số bản giữ
  lại (ví dụ giữ `ckpt_latest.pt` + mỗi 5.000 steps một bản)
- `DefaultStrategy` cần `step_pre_backward()` và `info` đầy đủ, trong khi MCMC chỉ cần
  `step_post_backward()` — bề mặt tích hợp rộng hơn

### Không thay đổi
- Tổ hợp phiên bản (Python 3.10 + torch 2.4.1+cu121 + gsplat 1.5.3+pt24cu121) giữ nguyên;
  lý do đã ghi trong skill `modal-serverless-jobs`
- Không quay lại LichtFeld Studio (thiếu Vulkan presentation trên driver datacenter)
- Không dùng `simple_trainer.py` của gsplat (phụ thuộc SceneManager/fused_ssim/lib_bilagrid)

## Tham chiếu

- `docs/ke-hoach-3dgs-production.md` — kế hoạch triển khai đầy đủ
- `spike-3dgs-modal/train_gsplat.py` — trainer tự viết
- `spike-3dgs-modal/gsplat_app.py:171` — `run_pipeline` cần tách stage
- Log bằng chứng preemption: `modal app logs ap-8ttrL2LOLIAaL9q4rlAClB`
