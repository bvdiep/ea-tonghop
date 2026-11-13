#!/usr/bin/env python3
"""Extract conversations from OpenClaw assistant sqlite import archive.

Source: /media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/assistant/session-sqlite-import-archive/
Filter: keep telegram + main sessions, skip cron/heartbeat/subagent
Output: conversation-level markdown files grouped by session + time gaps (12h)
"""

import glob, json, os, re, shutil
from datetime import datetime, timedelta
from collections import defaultdict

ARCHIVE = "/media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/assistant/session-sqlite-import-archive"
OUT_DIR = "/media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/assistant/.tmp/nhatky_conversations_sqlite"

# Filter patterns
SKIP_PREFIXES = (
    "Conversation info", "[cron:", "[OpenClaw", "[Startup", "[Subagent",
    "[Inter-session", "<<<BEGIN", "A new session was started",
    "Continue the OpenClaw", "Sender (untrusted metadata)",
    "[STATUS] KHÔNG CẦN BÁO", "HEARTBEAT_OK"
)
SKIP_SESSION_TYPES = ("cron", "heartbeat", "subagent")

def is_real_user_text(txt: str) -> bool:
    if not txt or not txt.strip():
        return False
    t = txt.strip()
    if t.startswith(SKIP_PREFIXES):
        return False
    if "heartbeat poll" in t[:80]:
        return False
    return True

def is_real_session_file(fname: str) -> bool:
    """Keep telegram and main sessions, skip cron/heartbeat/subagent."""
    if fname.startswith("agent_assistant_cron_"):
        return False
    if fname.startswith("agent_assistant_main_heartbeat"):
        return False
    if fname.startswith("agent_assistant_subagent_"):
        return False
    if "heartbeat" in fname:
        return False
    if fname == "legacy-store.sessions.json.imported-1789809105461":
        return False
    # Keep: telegram_direct, telegram_assistant_direct, and any main session
    # Files end with .imported-TIMESTAMP not .jsonl.imported-
    is_trajectory = fname.endswith(".trajectory.jsonl.imported-") or fname.endswith(".trajectory-path.json.imported-")
    is_jsonl = ".jsonl.imported-" in fname or ".jsonl.imported-" in fname
    return (".jsonl.imported-" in fname or fname.endswith(".jsonl.imported-") or fname.count(".imported-") == 1) and not is_trajectory

def extract_session_id(fname: str) -> str:
    """Extract session UUID from filename."""
    # Format: agent_assistant_telegram_direct_2139923586.4c81fc3d-59f4-45f5-92e3-413ac25d8549.jsonl.imported-1789809098185
    m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', fname)
    return m.group(1) if m else fname.split('.')[2] if len(fname.split('.')) > 2 else fname

def parse_ts(ts_str: str) -> datetime:
    """Parse ISO timestamp string to datetime."""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except:
        return datetime.min

def format_dt(dt: datetime) -> str:
    """Format datetime in GMT+7."""
    return (dt + timedelta(hours=7)).strftime("%H:%M:%S")

def slugify(text: str, max_len: int = 50) -> str:
    """Create slug from first user message."""
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text[:max_len] or "conversation"

# 1. Find all relevant session files
files = sorted(glob.glob(f"{ARCHIVE}/*.jsonl.imported-*"))
session_files = [f for f in files if is_real_session_file(os.path.basename(f))]
print(f"Found {len(session_files)} relevant session files")

# 2. Parse all messages from all sessions
sessions = defaultdict(list)  # sid -> list of (dt, role, text, raw_data)

for fp in session_files:
    fname = os.path.basename(fp)
    sid = extract_session_id(fname)
    print(f"  Parsing {fname[:60]} -> sid={sid[:12]}")
    with open(fp, encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except:
                continue
            if o.get("type") != "message":
                continue
            m = o.get("message") or {}
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue
            ts = parse_ts(o.get("timestamp", ""))
            c = m.get("content")
            if isinstance(c, str):
                txt = c
            elif isinstance(c, list):
                txt = "".join(x.get("text","") for x in c if isinstance(x,dict) and x.get("type")=="text")
            else:
                txt = str(c or "")
            if role == "user" and not is_real_user_text(txt):
                continue
            # For assistant, extract from text blocks
            if role == "assistant" and isinstance(c, list):
                asst_texts = [x.get("text","") for x in c if isinstance(x,dict) and x.get("type")=="text"]
                if not asst_texts:
                    continue
                txt = asst_texts[-1]  # last text block = final response
            sessions[sid].append((ts, role, txt))

print(f"\nTotal sessions with messages: {len(sessions)}")
total_msgs = sum(len(msgs) for msgs in sessions.values())
print(f"Total messages: {total_msgs}")

# 3. Group into conversations per session (split on 12h gaps)
conversations = []  # list of (start_dt, end_dt, sid, msgs_list)
for sid, msgs in sessions.items():
    if not msgs:
        continue
    msgs.sort(key=lambda x: x[0])
    current = [msgs[0]]
    for i in range(1, len(msgs)):
        prev_dt = msgs[i-1][0]
        cur_dt = msgs[i][0]
        if (cur_dt - prev_dt) >= timedelta(hours=12):
            conversations.append((current[0][0], current[-1][0], sid, current))
            current = [msgs[i]]
        else:
            current.append(msgs[i])
    if current:
        conversations.append((current[0][0], current[-1][0], sid, current))

print(f"Conversations after 12h gap split: {len(conversations)}")

# 4. Filter out conversations with < 2 user messages (likely cron/noise)
real_conversations = []
for start, end, sid, msgs in conversations:
    user_count = sum(1 for _, role, _ in msgs if role == "user")
    if user_count >= 2:
        real_conversations.append((start, end, sid, msgs))
    else:
        print(f"  Skip (user_msgs={user_count}): {sid[:12]} {format_dt(start)} - {format_dt(end)}")

print(f"Real conversations (>=2 user msgs): {len(real_conversations)}")

# 5. Write output files
os.makedirs(OUT_DIR, exist_ok=True)
real_conversations.sort(key=lambda x: x[0])

index_lines = ["# Assistant Conversations (from sqlite archive)\n",
               f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
               f"Source: {ARCHIVE}",
               f"Total conversations: {len(real_conversations)}",
               f"Total messages: {sum(len(msgs) for _,_,_,msgs in real_conversations)}\n"]

for i, (start, end, sid, msgs) in enumerate(real_conversations, 1):
    # Build slug from first user message
    first_user = next((txt for _, role, txt in msgs if role == "user"), "")
    slug = slugify(first_user)
    cross_day = start.date() != end.date()
    date_str = start.strftime("%Y%m%d")
    fname = f"{i:04d}_{date_str}_{slug}{'_+1ngay' if cross_day else ''}.md"
    fpath = os.path.join(OUT_DIR, fname)
    
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"# Conversation {i:04d}\n\n")
        f.write(f"- Session ID: {sid}\n")
        f.write(f"- Bắt đầu: {format_dt(start)} {start.strftime('%Y-%m-%d')} (GMT+7)\n")
        f.write(f"- Kết thúc: {format_dt(end)} {end.strftime('%Y-%m-%d')} (GMT+7)\n")
        f.write(f"- Số tin nhắn: {len(msgs)}\n")
        f.write(f"- Xuyên ngày: {'Có' if cross_day else 'Không'}\n\n")
        f.write("---\n\n")
        for dt, role, txt in msgs:
            f.write(f"### [{format_dt(dt)}] {role.capitalize()}\n\n{txt}\n\n")
    
    index_lines.append(f"- [{fname}]({fname}) — {len(msgs)} msgs ({format_dt(start)}–{format_dt(end)})")

# Write index
with open(os.path.join(OUT_DIR, "_index.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(index_lines))

print(f"\nDone! Output: {OUT_DIR}")
print(f"Files: {len(real_conversations)} conversations + _index.md")