# Pitfalls — OpenClaw session extraction

## 1. Filter trước khi clean

**Sai**: `if raw.lstrip().startswith(USER_SKIP_PREFIXES): continue` rồi mới
`clean_user()`.

Message Telegram thật thường bắt đầu bằng `Conversation info (untrusted
metadata):` + JSON, `System (untrusted): [ts]`, hoặc `[Fri 2026-...]`. Lọc trước
khi bóc các prefix này sẽ drop chính tin nhắn của user.

**Đúng**: bóc metadata/prefix trước, sau đó mới kiểm tra noise trên phần text
còn lại.

## 2. `max(path)` để chọn checkpoint

Tên file checkpoint chứa UUID, nên `max(glob(...))` chọn theo thứ tự **chữ cái**,
không phải thời gian. Trên `3b1780b2-...`, cách này chọn snapshot `ff86105c`
(46 user message) thay vì `4ed0c90f` (216 user message).

**Đúng**: `max(checkpoints, key=os.path.getmtime)`.

## 3. Bỏ qua `.trajectory.jsonl` và archive

v10 chỉ đọc `<sid>.jsonl` + checkpoint. Trong backup assistant có:

- 2.658 session **chỉ** có `.trajectory.jsonl` (không có base/checkpoint).
- 248 unique user text chỉ nằm trong `.reset.*` / `.deleted.*` / `.bak-*`.
- 508 unique user text chỉ nằm trong `prompt.submitted`.

**Đúng**: union mọi nguồn, dedup theo `message.id` (envelope) và theo
`(role, text, timestamp)` cho trajectory.

## 4. Tin vào số raw message

Một user turn có thể xuất hiện 2 lần trong envelope: bản có metadata Telegram và
bản text sạch, với `id` khác nhau. Raw count vì thế **cao hơn** số turn thật
(ví dụ `5d3539a4`: 186 raw → 91 unique text; `3b1780b2`: 216 raw → 81 unique).

**Đúng**: đo coverage bằng `set(text)` theo session, không bằng raw count.

## 5. Dedup chéo nguồn quá tay

Cùng một text có thể là 2 lượt thật nếu user gửi lại sau vài phút ("Ok", "Em làm
nhé"). Chỉ dedup khi cùng `(role, text)` và lệch timestamp ≤ 5 phút; ưu tiên giữ
bản envelope (timestamp chính xác hơn).

## 6. Quên strip `<final>` và tool-call giả dạng text

Assistant text trong bản legacy có thể là:

- `<final>...</final>` — cần bỏ tag, giữ nội dung.
- `read(path="...")`, `read = {"function_name": ...}`,
  `{"type": "function", "name": "read", ...}` — đây là tool call bị lưu thành
  text, phải drop.
- `NO_REPLY` / `HEARTBEAT_OK` / cron narration — drop.
- `Read HEARTBEAT.md if it exists ...` — heartbeat prompt, không phải user text;
  drop (prompt này xuất hiện hàng trăm lần trong session heartbeat-only).
- `[Queued user message ...]` / `[Retry after ...]` — wrapper, bóc **lặp lại**
  (có thể lồng 2 lớp) rồi giữ phần text thật phía sau.

Không xử lý các dạng này sẽ làm bẩn transcript và tăng sai số khi đếm message.
