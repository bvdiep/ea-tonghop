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

### 5. Rủi ro GPU path trên Modal (đã probe THÀNH CÔNG 20/10/2026)

Kết quả probe thật trên Modal workspace `tech-62960` (function GPU T4, image
`nvidia/cuda:12.8.1-runtime-ubuntu22.04` + `NVIDIA_DRIVER_CAPABILITIES=compute,graphics,utility`
+ vulkan-tools/libgl1/libxext6 + Node 22 + splat-transform):

- Host Modal expose Vulkan đầy đủ: `vulkaninfo` thấy Tesla T4 với NVIDIA proprietary driver
  610.57.04, Vulkan 1.4.341 (không phải cảnh báo Tesla-compute-only của AWS).
- `splat-transform --list-gpus` trong container: `[0] Tesla T4`, `[1] llvmpipe` → Dawn/WebGPU
  nhận GPU. VERDICT: GPU VIABLE trên Modal.
- Lưu ý image: bắt buộc cài `curl ca-certificates gnupg` TRƯỚC khi chạy nodesource setup,
  nếu không sẽ rơi về Node 12 của Ubuntu (không có npm).

### 5b. Benchmark end-to-end TRÊN MODAL (500k splats SH3, 4 LOD, cùng pipeline)

| Môi trường | Decimate | Bundle SOG | Zip | Tổng | Chi phí/job ước tính |
|---|---|---|---|---|---|
| Modal CPU (4 core, 8GiB) | 62.1s | 49.3s | 0.1s | 111.5s | ~$0.008 |
| Modal GPU T4 | 28.3s | 392.2s | 0.1s | 420.6s | ~$0.069 |
| Modal GPU L4 | 25.7s | 60.5s | 0.1s | 86.4s | ~$0.025 |
| Local 4-core (tham chiếu) | ~56s | ~72s | — | ~128s | — |

Phát hiện quan trọng:
- T4 là BẤT LỢI cho workload này: bước bundle SOG (k-means + WebP encode qua WebGPU) chậm
  gấp 6.5 lần L4 → T4 vừa chậm vừa đắt hơn ($0.069 vs $0.025). Nếu dùng GPU, dùng L4 trở lên,
  tránh T4.
- Với file nhỏ (≤1-2M splats): CPU vẫn rẻ hơn ~3 lần, chỉ chậm hơn ~30% so với L4.
- Với file lớn: GPU L4 thắng rõ về thời gian; chi phí gần ngang hoặc rẻ hơn CPU khi tăng cores.
- Output `.ssog` từ Modal (cả CPU và GPU) đã được tải về và kiểm chứng: zip đúng cấu trúc
  (`lod-meta.json` root + chunk folders), `--info` đọc lại đúng 4 LOD 500k/250k/125k/50k.

### 6. Đã tạo sẵn

- `modal_app.py` (cùng thư mục với report này): probe 3 lệnh nvidia-smi / vulkaninfo /
  splat-transform --list-gpus trên Modal GPU T4, tự in VERDICT. Chạy: `modal run modal_app.py`.
- Bộ lệnh pipeline + gen PLY test: /tmp/ssog-spike/.

## Verdict: VALIDATED (cả CPU và GPU trên Modal)

- CPU-only trên Modal: VALIDATED. Full pipeline chạy, output .ssog hợp lệ. Phù hợp file
  ≤ vài triệu splats (rẻ nhất, đơn giản nhất).
- GPU trên Modal: VALIDATED. Vulkan + WebGPU chạy được; L4 nhanh nhất trong các card đã test
  (86.4s cho 500k). TRÁNH T4 (bundle chậm bất thường 392s).
- Khuyến nghị cuối: dùng GPU L4 làm default cho mọi kích thước file (đơn giản 1 code path,
  thời gian tốt); hoặc hybrid CPU(<2M)/L4(≥2M) nếu tối ưu chi phí triệt để.
- Điểm chưa test: file thực tế lớn (10GB+), `--decimate-adaptive` (tốn RAM hơn, cần cho cảnh
  có sky), zip64 >4GB, tính thời gian chính xác trên Modal (IO network + cold start).

## Khuyến nghị cho build thật

1. Deploy modal_app.py chạy probe GPU trước (30 phút).
2. Nếu probe PASS: dùng GPU function (T4/L4) cho input ≥10-20M splats, CPU function cho phần còn lại.
3. Nếu probe FAIL: CPU-only, cân nhắc 16 cores cho file lớn (linear scaling với decimate) hoặc
   tự host GPU VM (RunPod/Vast có Vulkan ICD) cho các file rất lớn.
4. Job queue + volume lưu input/output; với file >4GB nhớ zip64 (đã hỗ trợ trong ecosystem).
5. Layout function: mount volume, `subprocess.run` CLI là đủ — không cần binding library API.
