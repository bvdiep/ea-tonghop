# Spike: Chuyển đổi .sog/.ply → Streamed SOG (.ssog) serverless trên Modal Labs

Ngày: 20/10/2026. Loại: khảo sát khả thi (spike), chưa có code production.

## Câu hỏi nghiên cứu

1. Tool nào convert được PLY/SOG → Streamed SOG (SSOG) headless trên server?
2. Serverless Modal Labs có khả thi không — CPU và GPU?

## Kết quả chính

### 1. SSOG thực chất là gì (đã xác minh bằng source + tool thực tế)

- Streamed SOG bundle = `lod-meta.json` (index cây không gian + per-LOD counts) + các thư mục chunk
  dạng `0_0/`, `1_0/`... (mỗi chunk là 1 SOG: `meta.json` + textures `.webp`).
- `.ssog` / `-SSOG.zip` = file ZIP của bundle trên (có thể kèm `env/` cho backdrop). SuperSplat
  upload chấp nhận `.zip` chứa `lod-meta.json` + chunk folders; API SuperSplat gọi sourceFormat `ssog`.
- Không cần tool riêng: chỉ cần `zip` sau khi splat-transform xuất bundle ra thư mục.

### 2. splat-transform CLI chạy headless CPU — ĐÃ CHỨNG MINH end-to-end

Lệnh (v3.10.1, Node ≥22, `npm i @playcanvas/splat-transform`):

```bash
# Bước 1: decimate các LOD (bắt buộc output .ply, decimate phải là action cuối)
splat-transform -g cpu input.ply -d 50% lod1.ply
splat-transform -g cpu input.ply -d 25% lod2.ply
splat-transform -g cpu input.ply -d 10% lod3.ply

# Bước 2: bundle thành Streamed SOG (output filename BẮT BUỘC là lod-meta.json)
splat-transform -g cpu input.ply -l 0 lod1.ply -l 1 lod2.ply -l 2 lod3.ply -l 3 out/lod-meta.json --filter-nan

# Bước 3: đóng gói .ssog
cd out && zip -qr ../output.ssog .
```

- Input `.sog` (bundled) KHÔNG dùng trực tiếp được cho `lod-meta.json` output → cần bước trung gian
  `.sog` → `.ply` rồi mới decimate (đã test, chạy tốt, ~1s cho 500k).
- Decimation memory-bounded + streaming, hỗ trợ scene 100M+ gaussians; scene lớn sâu cần `--scratch-dir`.

Số đo thực tế (máy 4 core, 15GB RAM, KHÔNG GPU NVIDIA — Intel HD 630):

| Công đoạn (500k splats, SH 3 bands) | Thời gian | Peak RAM |
|---|---|---|
| .sog → .ply | 1.0s | 334MB |
| decimate 25% | 18.3s | 940MB |
| bundle 2 LOD → lod-meta.json | 49.8s | 934MB |
| decimate 50%+25%+10% + bundle 4 LOD | ~128s | ~1GB |

### 3. Chạy trong container CPU thuần — ĐÃ CHỨNG MINH

Docker `node:22-slim` (không mesa, không vulkan, không driver):

- `npm install @playcanvas/splat-transform` hoạt động, kể cả `--ignore-scripts`
  (package `webgpu` 0.6.2 đã bundle sẵn binary Dawn native cho linux-x64 trong package, 132MB).
- `-g cpu` → CLI bỏ qua hoàn toàn việc tạo WebGPU device (đọc source: `deviceIdx === -2` →
  `createDevice: undefined`) → không cần Vulkan/Mesa trên hệ thống.
- Full pipeline decimate + bundle chạy thành công trong container.

### 4. Đánh giá Modal Labs

Giá (Starter, $30 credit/tháng): CPU $0.0000131/core/s (~$0.047/core-h), RAM $0.00000222/GiB/s,
T4 $0.000164/s, L4 $0.000222/s. Timeout function tối đa 24h. `cpu=(request, limit)` và
`memory=(request, limit)` để kiểm soát OOM. Disk quota mặc định vài trăm GB, có `ephemeral_disk`.

Chi phí ước tính mỗi job:

| Quy mô | CPU-only | GPU (T4) | Ghi chú |
|---|---|---|---|
| 500k splats | ~$0.007 | ~$0.02 | CPU rẻ hơn, đơn giản hơn |
| 2M splats | ~$0.03 | ~$0.03 | ngang nhau |
| 50M splats | ~$2.0 (16c, ~2.5h) | ~$0.30-0.37 (~20-25ph) | GPU rẻ hơn ~5-6x và nhanh gấp nhiều lần |

Kết luận kiến trúc đề xuất: hybrid — CPU path cho file nhỏ/vừa (đã chắc chắn chạy), GPU path
cho file lớn NẾU probe Vulkan trên Modal thành công (mục dưới).

### 5. Rủi ro GPU path trên Modal (chưa giải quyết — cần probe)

GPU của splat-transform đi qua WebGPU → Vulkan, KHÔNG phải CUDA. Để chạy trên container GPU:

- Host của Modal phải có NVIDIA driver expose Vulkan ICD. Cảnh báo từ docs PlayCanvas: trên AWS
  GPU instances driver mặc định là Tesla compute-only (không có Vulkan), cần GRID driver ≥19.2.
  Modal không công bố cấu hình driver host → đây là ẩn số lớn nhất, không kiểm soát được từ image.
- Image cần: CUDA base + `NVIDIA_DRIVER_CAPABILITIES=compute,graphics,utility` (chữ `graphics`
  bắt buộc để toolkit mount ICD) + `vulkan-tools libgl1 libglvnd0 libglx0 libegl1 libxext6`.
- Kiểm chứng nhanh: `splat-transform --list-gpus` trong container phải thấy adapter NVIDIA;
  `vulkaninfo --summary` phải thấy GPU0 NVIDIA. RunPod đã có người chạy được WebGPU headless
  (cần libnvidia-gl đúng version driver + Vulkan loader 1.4+); Modal chưa thấy ai công bố.

### 6. Đã tạo sẵn

- `modal_app.py` (cùng thư mục với report này): probe 3 lệnh nvidia-smi / vulkaninfo /
  splat-transform --list-gpus trên Modal GPU T4, tự in VERDICT. Chạy: `modal run modal_app.py`.
- Bộ lệnh pipeline + gen PLY test: /tmp/ssog-spike/.

## Verdict: PARTIAL → VALIDATED (CPU), PARTIAL (GPU)

- CPU-only trên Modal: khả thi cao, đã chứng minh toàn pipeline chạy trong container CPU thuần.
  Phù hợp file ≤ vài triệu splats; chi phí thấp, không rủi ro driver.
- GPU trên Modal: tiềm năng cho file lớn (rẻ + nhanh hơn nhiều) nhưng phụ thuộc host driver
  Vulkan của Modal — phải chạy probe thật trước khi cam kết.
- Điểm chưa test: file thực tế lớn (10GB+), `--decimate-adaptive` (tốn RAM hơn, cần cho cảnh
  có sky), zip64 >4GB, tính thời gian chính xác trên Modal (IO network + cold start).

## Khuyến nghị cho build thật

1. Deploy modal_app.py chạy probe GPU trước (30 phút).
2. Nếu probe PASS: dùng GPU function (T4/L4) cho input ≥10-20M splats, CPU function cho phần còn lại.
3. Nếu probe FAIL: CPU-only, cân nhắc 16 cores cho file lớn (linear scaling với decimate) hoặc
   tự host GPU VM (RunPod/Vast có Vulkan ICD) cho các file rất lớn.
4. Job queue + volume lưu input/output; với file >4GB nhớ zip64 (đã hỗ trợ trong ecosystem).
5. Layout function: mount volume, `subprocess.run` CLI là đủ — không cần binding library API.
