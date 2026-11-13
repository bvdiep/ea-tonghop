# Đánh giá trace LiteLLM — `ses_ea04a7a98ffexGIDVO9Fvmzr82`

- **Ngày phân tích**: 2026-10-22
- **Nguồn**: `https://litellm.ccc.io.vn/ui/logs/?session_id=ses_ea04a7a98ffexGIDVO9Fvmzr82&log_id=chatcmpl-506fb446-ae9e-40d0-bf16-fb97052437cd`
- **Host**: thinkcentre — LiteLLM proxy tại `~/docker/litellm` (cổng 4000), DB Postgres `litellm-db-1`
- **Cách thu thập**: truy vấn trực tiếp bảng `LiteLLM_SpendLogs` (URL UI bị chặn vì là địa chỉ private)
- **Log ID được hỏi**: `chatcmpl-506fb446-ae9e-40d0-bf16-fb97052437cd` (1 trong 178 call của session)

## 1. Số liệu tổng quan

| Chỉ số | Giá trị |
|---|---|
| Tổng số call | 178 |
| Khoảng thời gian | 05:16:28 → 05:51:53 (~35 phút) |
| Tổng token | 21,385,538 (21.3M prompt / 70.5K completion) |
| Model group | `model-coding-free` (100%) |
| Số model thực thi | 10 |
| Lần đổi model (model switch) | 48 (mỗi ~3.7 call) |
| Tỉ lệ prompt cache hit | 88.2% (18,805,920 / 21,315,000 token) |
| Latency TB | 5,950 ms (max 102,834 ms) |
| Failures | 0 (`status='success'` toàn bộ) |
| `attempted_retries` / `attempted_fallbacks` | 0 / 0 (mọi call) |
| Spend | $0.00 (toàn bộ model là bản `:free`) |
| User-Agent | `opencode/latest/2.0.32/cli` |
| API key alias | `Thinkcentre_Opencode` |

## 2. Phân bố theo model

| model | calls | prompt tok | cached | wasted | %waste |
|---|---|---|---|---|---|
| `openai/reflection/beam-1.0-501b-a23b:free` (Nous) | 74 | 8,899,448 | 8,611,520 | 287,928 | 3.2% |
| `openai/nvidia/nemotron-3-ultra-550b-a55b` (NVIDIA) | 63 | 7,532,200 | 6,821,280 | 710,920 | 9.4% |
| `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | 19 | 2,244,687 | 1,827,360 | 417,327 | 18.6% |
| `openai/nvidia/nemotron-3-ultra-550b-a55b:free` (kilo.ai) | 13 | 1,470,459 | 1,321,920 | 148,539 | 10.1% |
| `litellm_proxy/kilo-nemotron-3-ultra-free` (bsmlabs) | 2 | 239,696 | 220,320 | 19,376 | 8.1% |
| `openai/deepseek-ai/deepseek-v4.1-flash` | 2 | 258,975 | 640 | 258,335 | 99.8% |
| `openai/stepfun-ai/step-5-preview` | 2 | 252,147 | 192 | 251,955 | 99.9% |
| `openai/z-ai/glm-5.3` | 1 | 136,768 | 1,408 | 135,360 | 99.0% |
| `openai/z-ai/glm-5.3-flash` | 1 | 135,858 | 1,280 | 134,578 | 99.1% |
| `openai/minimax/minimax-m3.1-flash:free` | 1 | 144,762 | 0 | 144,762 | 100.0% |

`wasted` = `prompt_tokens - cached_tokens`, tức phần context phải xử lý lại từ đầu.

## 3. Tại sao trace dài bất thường

Không phải lỗi hệ thống — đây là hành vi agent bình thường với **context cực lớn**:

- Prompt khởi đầu ~97K token và **tăng đơn điệu** suốt phiên (tới 180,777 token ở 05:45:28).
- Mỗi call là một bước trong agent/tool-call loop của opencode; toàn bộ lịch sử được gửi lại mỗi lần.
- 21.3M token = `178 call × ~120K token/call trung bình`.
- 35 phút / 178 call ≈ 1 call / 12 giây — nhịp agent loop bình thường, **không phải retry loop**.
- Dấu hiệu compaction: 05:46:12 prompt giảm từ 180,777 → 116,484, rồi 05:46:16 → 68,646. opencode **compact quá muộn** — sau 30 phút và 150+ call với context 180K.

## 4. Tại sao gom rất nhiều model

Đây là **tính năng của router**, không phải bug.

`model-coding-free` là một `routing_group` trong `litellm-config.yaml` với `routing_strategy: latency-based-routing`:

```yaml
- group_name: model-coding-free
  models:
    - nvidia-step-5-preview
    - nvidia-deepseek-v4.1-flash
    - nvidia-glm-5.3-flash
    - nvidia-glm-5.3
    - kilo-minimax-m3.1-flash-free
    - kilo-nemotron-3-ultra-free
    - nvidia-nemotron-3-ultra-550b
    - openrouter-nemotron-3-ultra-free
    - nous-beam-1.0
  routing_strategy: latency-based-routing
  routing_strategy_args:
    lowest_latency_buffer: 0.5
    ttl: 3600
```

Router chọn model theo **latency thấp nhất** (TTL 1h, buffer 0.5). Vì agent loop gửi lại cùng một context khổng lồ, mỗi request đều ở rìa context window → model nào đáp nhanh nhất ở thời điểm đó thắng. Hệ quả:

- `nemotron-3-ultra-550b` (NVIDIA) chiếm 63/178 call (35%) — nhanh nhất, cache hit tốt.
- `beam-1.0` (Nous) chiếm 74/178 (42%) — nhanh nhất ở các đoạn 05:43–05:51.
- Các model còn lại (step-5, deepseek-v4.1, glm-5.3, minimax) chỉ xuất hiện 1–2 lần: kiểu **probe ban đầu + khi context phình to và model chính bị trần context**.

48 lần đổi model / 178 call là hệ quả của latency-based routing, **không phải fallback** (fallback chỉ kích hoạt khi có lỗi; trace này lỗi = 0, `attempted_fallbacks=0`).

## 5. Chi phí thật sự: đổi model phá cache

| model | calls | wasted prompt tok | %waste |
|---|---|---|---|
| `openai/stepfun-ai/step-5-preview` | 2 | 251,955 | 99.9% |
| `openai/deepseek-ai/deepseek-v4.1-flash` | 2 | 258,335 | 99.8% |
| `openai/minimax/minimax-m3.1-flash:free` | 1 | 144,762 | 100.0% |
| `openai/z-ai/glm-5.3` | 1 | 135,360 | 99.0% |
| `openai/z-ai/glm-5.3-flash` | 1 | 134,578 | 99.1% |
| `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | 19 | 417,327 | 18.6% |

Các model "lạ" xuất hiện 1–2 lần thì **cache hit gần như 0** → phải xử lý lại toàn bộ 130–150K token từ đầu. 6 call đó đã tạo ~1.2M token không cache được. Tổng session: **2.5M / 21.3M token bị lãng phí do mất cache**.

Ngoài ra `litellm_proxy/kilo-nemotron-3-ultra-free` là entry trỏ qua proxy `aigateway.bsmlabs.io` → request đi **hai tầng proxy** (LiteLLM → bsmlabs → kilo.ai), tạo thêm độ trễ.

## 6. Nguyên nhân gốc

Context tăng đơn điệu không dừng, và router latency-based trên 9 model không có tín hiệu về context window.

## 7. Khuyến nghị (theo thứ tự hiệu quả)

1. **Bật compaction sớm hơn trong opencode** — hiện context đã 180K mới compact; nên compact ở ~100–120K. ROI cao nhất, giảm phần lớn 21.3M token.
2. **Giảm `model-coding-free` xuống 2–3 model** thay vì 9. Với context 100K+, latency-based routing trên 9 model chỉ tạo model-hop vô nghĩa + phá cache. Hoặc đặt `routing_strategy` cố định cho group.
3. **Bỏ `litellm_proxy/kilo-nemotron-3-ultra-free`** khỏi group nếu không cần — entry thừa (duplicate với `openai/nvidia/nemotron-3-ultra-550b-a55b:free` qua kilo.ai), đi qua 2 tầng proxy.
4. **Thêm `context_window_fallbacks`** — LiteLLM hỗ trợ fallback riêng khi vượt context window; hiện config chỉ có `fallbacks` (chỉ kích hoạt khi lỗi), không có `context_window_fallbacks`. Với trace này (0 lỗi nhưng 48 lần đổi model), `context_window_fallbacks` chính xác hơn nhiều: model chính dùng đến khi chạm trần context rồi mới chuyển.

## 8. Ghi chú

- Session này là session `model-coding-free` duy nhất hôm nay (183 call total, 2 session).
- Spend = $0 vì toàn bộ model là bản `:free`. Vấn đề ở đây là **chất lượng context + chi phí token vô hình**, không phải tiền.
- Dữ liệu thô theo từng call: xem `docs/litellm-trace-ses_ea04a7a98ffexGIDVO9Fvmzr82-timeline.csv`.

## 9. Câu lệnh tái lập

```bash
docker exec litellm-db-1 psql -U llmadmin -d litellm -A -F'|' -c "
SELECT to_char(\"startTime\",'HH24:MI:SS') t, model, prompt_tokens, completion_tokens,
       total_tokens, request_duration_ms,
       (metadata->'usage_object'->'prompt_tokens_details'->>'cached_tokens') cached
FROM \"LiteLLM_SpendLogs\"
WHERE session_id='ses_ea04a7a98ffexGIDVO9Fvmzr82'
ORDER BY \"startTime\";"
```
