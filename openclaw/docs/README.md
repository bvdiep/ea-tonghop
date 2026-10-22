# OpenClaw Session Extraction Pipeline

Trích xuất nhật ký sạch từ raw OpenClaw session JSONL files.

## Tổng quan

Pipeline 2 bước:
1. **Extract**: Đọc JSONL files → lọc theo 9 rules → output Markdown files (mỗi ngày một file)
2. **Convert**: Markdown files → HTML dark-theme chat-bubble format

## Cấu trúc thư mục

```
openclaw/
├── docs/
│   └── README.md          # Tài liệu này
└── scripts/
    ├── extract_openclaw_sessions.py
    └── convert_to_html.py
```

## Sử dụng

### Bước 1: Extract

```bash
python openclaw/scripts/extract_openclaw_sessions.py [sessions_dir] [output_dir]

# Ví dụ
python openclaw/scripts/extract_openclaw_sessions.py \
  ~/.openclaw/agents/assistant/sessions \
  openclaw/output/test_logs
```

Options:
- `sessions_dir`: Đường dẫn đến sessions directory (mặc định: `~/.openclaw/agents/assistant/sessions`)
- `output_dir`: Đường dẫn output markdown (mặc định: `./test_logs`)
- `--timezone`: Timezone offset (mặc định: 7 cho GMT+7)

### Bước 2: Convert to HTML

```bash
python openclaw/scripts/convert_to_html.py [md_dir] [html_dir]

# Ví dụ
python openclaw/scripts/convert_to_html.py \
  openclaw/output/test_logs \
  openclaw/output/test_logs_html
```

## Filtering Rules

### Session-level (loại bỏ toàn bộ session)

| Rule | Điều kiện | Lý do |
|------|-----------|-------|
| Cron-only | `[cron:` + ≤1 user msg | Cron job session |
| Heartbeat-only | `[OpenClaw heartbeat poll]` + ≤2 user msg | Background heartbeat |
| Subagent-only | `[Subagent Context]` hoặc `[Subagent Task]` | Subagent execution |

### Message-level (loại bỏ từng message)

| # | Rule | Cấu trúc/Pattern | Loại |
|---|------|-----------------|------|
| 1 | toolCall narration | `content` có `type: "toolCall"` | Assistant |
| 2 | Artifact | `stopReason: "toolUse"` + không toolCall | Assistant |
| 3 | Status report | `stopReason: "stop"` + `HEARTBEAT_OK`/`NO_REPLY` | Assistant |
| 4 | Thinking tag | text chứa ``/`` | Assistant |
| 5 | Prompt leak | ≥2 system prompt markers | Assistant |
| 6 | Cron/heartbeat | `[cron:` / `NO_REPLY`/``/heartbeat | All |
| 7 | Thinking leak | text bắt đầu `Thinking Process:` | Assistant |
| 8 | Internal context | `provenance` field | All |
| 9 | Inter-session | `[Inter-session message]`/`<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>` | All |

## Output format

### Markdown

```markdown
# Nhật ký ngày 2026-09-12

### [07:00:20] User
Hello, how are you?

### [07:00:25] Assistant
I'm doing well, thanks for asking!
```

### HTML

- Dark theme (#1a1a2e background)
- User messages: blue border-left (#0f3460)
- Assistant messages: red/pink border-left (#e94560)
- Basic markdown: bold, italic, code, links

## Kết quả

| Phiên bản | Tin nhắn | Ngày | Cải tiến |
|-----------|----------|------|----------|
| V1 | 13,847 | 127 | Raw extraction |
| V7 | 5,736 | 127 | + message-level rules |
| V8 | 5,158 | 87 | + session-level rules |
| **V9** | **5,116** | **87** | **+ subagent filter** |

## Conversation extraction (v10 → v11)

`group_conversations_assistant.py` (v10) gom message thành conversation nhưng chỉ
đọc `<sid>.jsonl` + **một** checkpoint, không đọc `.trajectory.jsonl` và archive,
đồng thời lọc noise **trước khi** bóc metadata Telegram. Hậu quả trên agent
`assistant`: 662/1.885 (35%) unique user text, chỉ 19/291 session có user message.

`extract_assistant_v11.py` thay thế bằng union-of-sources + dedup theo entry id:

```bash
python3 openclaw/scripts/extract_assistant_v11.py \
  --sessions-dir /path/to/agents/assistant/sessions \
  --output openclaw/output_v10/assistant_conversations_v11
```

Nguồn dữ liệu:

1. `<sid>.jsonl` — transcript gốc.
2. `<sid>.jsonl.reset.*` / `.deleted.*` / `.bak-*` — bản archive bị rotate.
3. `<sid>.checkpoint.<uuid>.jsonl` — **chỉ bản mới nhất theo mtime** (checkpoint
   là snapshot cộng dồn; các bản cũ là tập con).
4. `<sid>.trajectory.jsonl` — `prompt.submitted` (user) + `model.completed`
   (assistant), nguồn duy nhất cho 2.658 session trajectory-only.

Quy tắc chính:

- **Clean trước, filter sau** → message có metadata Telegram / `System (untrusted):`
  / `[Fri 2026-...]` vẫn giữ được phần text thật.
- Dedup theo `message.id`; dedup chéo nguồn theo `(role, text)` trong cửa sổ 5 phút.
- Bỏ tool-call giả dạng text (`read(path=...)`, JSON function call), `<final>`,
  media-attachment boilerplate, bootstrap/cron/heartbeat/pre-compaction prompt.
- Session không có user message bị bỏ (dùng `--keep-assistant-only` để giữ).
- Tách conversation khi gap ≥ 12h (`--gap-hours`), hiển thị GMT+7 (`--tz-offset`).

Output: `NNNN_YYYYMMDD_slug.md`, `_index.md`, `messages.jsonl`,
`coverage_report.json`.

Kết quả chạy full backup assistant (2026-04-27 → 2026-08-15):

| Metric | v10 | v11 |
|--------|-----|-----|
| Conversations | 259 | 304 |
| User messages | 744 | 2.077 |
| Assistant messages | 2.099 | 2.055 |
| Gold unique user texts (per session) | 662/1.885 (35,1%) | **1.882/1.882 (100%)** |
| Sessions có user message | 19/291 | **291/291** |


## Session JSONL Format

```jsonl
{"type":"message","id":"abc","parentId":"def","timestamp":"2026-09-12T04:00:00Z","message":{"role":"user","content":[{"type":"text","text":"Hello"}]}}

{"type":"message","id":"ghi","parentId":"abc","timestamp":"2026-09-12T04:00:05Z","message":{"role":"assistant","content":[{"type":"toolCall","id":"call-1","name":"exec","arguments":{"command":"ls"}}],"stopReason":"toolUse"}}

{"type":"message","id":"jkl","parentId":"ghi","timestamp":"2026-09-12T04:00:06Z","message":{"role":"toolResult","toolCallId":"call-1","toolName":"exec","content":[{"type":"text","text":"file1.txt\nfile2.txt"}]}}
```

Fields quan trọng:
- `type`: message / context.compiled / model.completed
- `message.role`: user / assistant / toolResult / custom
- `message.content`: list of parts (text, thinking, toolCall)
- `message.stopReason`: stop / toolUse / length
- `message.provenance`: nếu có → internal context
