# ADR 0001 — Trích xuất conversation từ legacy OpenClaw v3 session backups

- **Status**: Proposed (draft)
- **Ngày**: 2026-10-22
- **Bối cảnh**: `openclaw/scripts/group_conversations_assistant.py` (v10)

## Bối cảnh

Backup legacy của agent `assistant` (OpenClaw 2026.9.x, sessions dir
`agents/assistant/sessions`) chứa 3 thế hệ file cùng tồn tại:

- `<sid>.jsonl` — transcript gốc (có thể đã bị rotate).
- `<sid>.jsonl.reset.*` / `.deleted.*` / `.bak-*` — bản archive.
- `<sid>.checkpoint.<uuid>.jsonl` — snapshot đầy đủ tại thời điểm compaction.
- `<sid>.trajectory.jsonl` — event log (`prompt.submitted`, `model.completed`).

Script v10 chỉ đọc base + **một** checkpoint (chọn bằng `max(path)`, tức thứ tự
UUID), không đọc trajectory/archive, và lọc user noise **trước khi** bóc metadata
Telegram. Đo trên gold set (union của mọi nguồn, dedup theo text):

- 662/1.885 unique user text được giữ (35,1%).
- Chỉ 19/291 session có ít nhất một user message.
- 2.658 session chỉ tồn tại dưới dạng `.trajectory.jsonl` → mất hoàn toàn.

## Quyết định

1. **Union-of-sources**: đọc base + toàn bộ archive + checkpoint mới nhất theo
   **mtime** + trajectory. Dedup message theo `message.id` (envelope) và theo
   `model.completed.assistantTexts` của trajectory.
2. **Chỉ đọc checkpoint mới nhất**: checkpoint là snapshot cộng dồn. Đã kiểm
   chứng trên 3 session (62, 2 và 47 checkpoint): `latest ⊇ union`, không mất id
   nào. Base/archive/trajectory bù phần message phát sinh sau snapshot.
3. **Trajectory là nguồn turn chính thức** cho session trajectory-only, và là
   nguồn bổ sung cho session có envelope.
4. **Clean trước, filter sau**: bóc metadata (`Conversation info`, `Sender`,
   `Conversation context`), `System (untrusted): [ts]`, date prefix, media
   attachment boilerplate; sau đó mới drop noise (cron/heartbeat/bootstrap/
   pre-compaction).
5. **Dedup chéo nguồn** theo `(role, text)` trong cửa sổ 5 phút, ưu tiên
   envelope hơn trajectory.
6. **Output conversation-level**, tách khi gap ≥ 12h, timezone GMT+7, kèm
   `messages.jsonl` và `coverage_report.json` để kiểm toán.

## Hệ quả

- Tăng coverage lên 100% gold set (1.882/1.882 text, 291/291 session) trên backup
  assistant; chi phí đọc ~2,5 GB là ~25 giây.
- Dedup theo cửa sổ thời gian có thể gộp 2 tin nhắn giống hệt nhau nếu chúng cách
  nhau < 5 phút; chấp nhận được vì đây là trường hợp hiếm và không làm mất nội
  dung mới.
- Gold set được định nghĩa bằng chính cleaner/inventory của extractor, nên QA
  chứng minh **không mất dữ liệu so với union nguồn**, không chứng minh cleaner
  giữ 100% ngữ nghĩa. Các kiểm tra leakage (metadata, tool call, bootstrap) được
  chạy riêng.
- `coverage_report.json` phình theo số session (~4.000 entry) nhưng vẫn nhỏ.

## Phương án đã cân nhắc

- **Sửa trực tiếp v10**: rủi ro phá output cũ, khó so sánh; đã chọn script mới
  `extract_assistant_v11.py` và giữ v10 làm baseline.
- **Đọc tất cả checkpoint**: chậm hơn nhiều, không thêm dữ liệu (đã kiểm chứng).
- **Dùng `openclaw sessions export-trajectory`**: chỉ áp dụng cho session đang
  sống trong SQLite, không đọc được backup legacy hàng loạt.
