#!/usr/bin/env python3
import json, os, hashlib, re, argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser(description='Extract clean daily memory logs from OpenClaw JSONL sessions')
    parser.add_argument('--day', type=str, help='Extract a specific day (YYYY-MM-DD)')
    parser.add_argument('--from', dest='from_date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to', dest='to_date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--sessions-dir', type=str, default='/home/diep/.openclaw/agents/assistant/sessions',
                        help='Path to sessions directory (default: ~/.openclaw/agents/assistant/sessions)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output directory (default: ./test_logs_v10 or ./test_logs_v10_<day>)')
    return parser.parse_args()

args = parse_args()

tz7 = timezone(timedelta(hours=7))

def safe_json(line):
    try:
        return json.loads(line)
    except:
        return None

def has_tool_call(content):
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "toolCall":
                return True
    return False

def extract_text(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    parts.append(c.get("text", ""))
        return "".join(p for p in parts if p).strip()
    if isinstance(content, dict):
        return content.get("text", str(content))
    return str(content)

def parse_ts_ms(d, msg):
    ts = msg.get("timestamp") if isinstance(msg, dict) else None
    if isinstance(ts, (int, float)):
        return int(ts)
    ts_iso = d.get("timestamp")
    if ts_iso and isinstance(ts_iso, str):
        try:
            dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except:
            pass
    return None

def is_cron_message(role, text):
    if role == "user":
        return text.strip().startswith("[cron:")
    if role == "assistant":
        txt = text.strip()
        return txt in ("NO_REPLY", "<|finish|>", "HEARTBEAT_OK")
    return False

def is_internal_context(d, msg):
    if "provenance" in msg:
        return True
    return False

def is_heartbeat_poll(role, text):
    if role == "user":
        return "[OpenClaw heartbeat poll]" in text.strip()
    return False

def is_status_report_text(text):
    if "HEARTBEAT_OK" in text:
        return True
    if "NO_REPLY" in text:
        return True
    return False

def is_thinking_artifact(text):
    if "</think>" in text or "</thinking>" in text:
        return True
    return False

def is_prompt_leak(text):
    markers = [
        "those tools are policy-filtered",
        "TOOLS.md is usage guidance",
        "Your working directory is:",
        "Runtime: agent=",
        "Workspace Files (injected)",
        "Current Date & Time",
        "Time zone: Asia/Saigon",
        "Current model identity:",
        "Reasoning: off (hidden unless on",
    ]
    count = sum(1 for m in markers if m in text)
    return count >= 2

def is_thinking_text(text):
    return text.strip().startswith("Thinking Process:")

def is_tool_result_noise(text):
    txt = text.strip()
    return txt.startswith("[STATUS]")

def is_inter_session_text(text):
    if not text:
        return False
    markers = [
        "[Inter-session message]",
        "<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>",
        "[Internal task completion event]",
    ]
    for m in markers:
        if m in text:
            return True
    return False

def is_subagent_session(user_text):
    if not user_text:
        return False
    markers = [
        "[Subagent Context]",
        "[Subagent Task]",
    ]
    for m in markers:
        if m in user_text:
            return True
    return False

def is_pre_compaction_metadata(role, text):
    if role != "user":
        return False
    if not text:
        return False
    if text.startswith("Conversation info (untrusted metadata):"):
        return True
    if text.startswith("Sender (untrusted metadata):"):
        return True
    if text.startswith("Pre-compaction memory flush"):
        return True
    return False

def is_phantom_greeting(text):
    if not text:
        return False
    greetings = [
        "How can I help you today",
        "I have received the runtime context",
        "I don't see a preceding user message",
        "I'm ready to assist you",
        "I'm ready to help",
        "I am ready. How can I help",
        "Dạ, em đã sẵn sàng",
    ]
    for g in greetings:
        if g in text:
            return True
    return False

def extract_messages_from_file(filepath):
    results = []
    is_trajectory = '.trajectory.' in filepath
    # Note: checkpoint files are now included; dedup handles duplicates
    
    with open(filepath, "r", errors="replace") as fh:
        lines = fh.readlines()
    
    # First pass: analyze session structure (message type only)
    all_msgs = []
    user_msg_count = 0
    assistant_msg_count = 0
    has_cron_prompt = False
    has_heartbeat_poll = False
    has_subagent_context = False
    
    # Also check trajectory content (context.compiled)
    has_trajectory_msgs = False
    trajectory_user_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        d = safe_json(line)
        if not d:
            continue
        dtype = d.get("type")
        
        if dtype == "message":
            msg = d.get("message", {})
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            if role not in ("user", "assistant", "toolResult"):
                continue
            
            all_msgs.append((d, msg))
            if role == "user":
                user_msg_count += 1
                content = msg.get("content", [])
                txt = extract_text(content)
                if txt.strip().startswith("[cron:"):
                    has_cron_prompt = True
                if "[OpenClaw heartbeat poll]" in txt.strip():
                    has_heartbeat_poll = True
                if is_subagent_session(txt):
                    has_subagent_context = True
            elif role == "assistant":
                assistant_msg_count += 1
        
        elif dtype == "context.compiled":
            data = d.get("data", {}) or {}
            msgs = data.get("messages", []) or []
            for m in msgs:
                if isinstance(m, dict) and m.get("role") == "user":
                    trajectory_user_count += 1
                    has_trajectory_msgs = True
    
    # SKIP 11: Remove sessions with 0 messages total (empty/noise sessions)
    # Keep sessions with only assistant messages (cron morning greetings, etc.)
    if user_msg_count == 0 and assistant_msg_count == 0 and not has_trajectory_msgs:
        return results
    
    # Session-level filtering
    if has_cron_prompt and user_msg_count <= 1:
        return results
    
    if has_heartbeat_poll and not has_cron_prompt and user_msg_count <= 2:
        all_heartbeat = True
        for d, msg in all_msgs:
            if msg.get("role") == "user":
                content = msg.get("content", [])
                txt = extract_text(content)
                if "[OpenClaw heartbeat poll]" not in txt.strip():
                    all_heartbeat = False
                    break
        if all_heartbeat:
            return results
    
    if has_subagent_context:
        return results
    
    # Second pass: extract from message-type entries
    for d, msg in all_msgs:
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        
        content = msg.get("content")
        text = extract_text(content)
        if not text:
            continue
        
        if role == "assistant" and has_tool_call(content):
            continue
        if role == "assistant" and msg.get("stopReason") == "toolUse" and not has_tool_call(content):
            continue
        
        # SKIP 10: Remove error turns
        if role == "assistant" and msg.get("stopReason") == "error":
            continue
        
        if role == "assistant" and is_status_report_text(text):
            continue
        if role == "assistant" and is_thinking_artifact(text):
            continue
        if role == "assistant" and is_prompt_leak(text):
            continue
        if is_cron_message(role, text):
            continue
        if role == "assistant" and is_thinking_text(text):
            continue
        if role == "toolResult" and is_tool_result_noise(text):
            continue
        if is_internal_context(d, msg):
            continue
        if is_inter_session_text(text):
            continue
        if is_pre_compaction_metadata(role, text):
            continue
        if role == "assistant" and is_phantom_greeting(text):
            continue
        
        ts_ms = parse_ts_ms(d, msg)
        results.append((ts_ms, role, text, filepath))
    
    # Trajectory handling
    if is_trajectory:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            d = safe_json(line)
            if not d or d.get("type") != "context.compiled":
                continue
            data = d.get("data", {}) or {}
            msgs = data.get("messages", []) or []
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                role = m.get("role")
                if role not in ("user", "assistant"):
                    continue
                content = m.get("content")
                text = extract_text(content)
                if not text:
                    continue
                
                # Apply same filters
                if role == "assistant" and has_tool_call(content):
                    continue
                if role == "assistant" and m.get("stopReason") == "toolUse" and not has_tool_call(content):
                    continue
                if role == "assistant" and m.get("stopReason") == "error":
                    continue
                if role == "assistant" and is_status_report_text(text):
                    continue
                if role == "assistant" and is_thinking_artifact(text):
                    continue
                if role == "assistant" and is_prompt_leak(text):
                    continue
                if is_cron_message(role, text):
                    continue
                if role == "assistant" and is_thinking_text(text):
                    continue
                if is_inter_session_text(text):
                    continue
                if is_pre_compaction_metadata(role, text):
                    continue
                if role == "assistant" and is_phantom_greeting(text):
                    continue
                
                ts_ms = parse_ts_ms(d, m)
                results.append((ts_ms, role, text, filepath))
    
    return results

# Scan all files
sessions_dir = args.sessions_dir
all_files = []
for fn in os.listdir(sessions_dir):
    fp = os.path.join(sessions_dir, fn)
    if not os.path.isfile(fp):
        continue
    if fn.endswith('.jsonl') or fn.endswith('.trajectory.jsonl') or '.jsonl.reset.' in fn:
        all_files.append(fp)

print(f'Total files to scan: {len(all_files)}')

all_messages = []
for i, fp in enumerate(sorted(all_files)):
    msgs = extract_messages_from_file(fp)
    all_messages.extend(msgs)
    if (i+1) % 2000 == 0:
        print(f"  scanned {i+1}/{len(all_files)} files, {len(all_messages)} messages so far")

print(f"\nTotal raw messages: {len(all_messages)}")

# Dedup
seen = set()
unique = []
for ts_ms, role, text, fp in all_messages:
    key = (role, hashlib.md5(text.encode("utf-8")).hexdigest())
    if key not in seen:
        seen.add(key)
        unique.append((ts_ms, role, text))

print(f"Unique messages after dedup: {len(unique)}")

# Group by day
by_day = defaultdict(list)
for ts_ms, role, text in unique:
    if ts_ms:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=tz7)
    else:
        continue
    day = dt.strftime("%Y-%m-%d")
    
    # Date filtering
    if args.day:
        if day != args.day:
            continue
    else:
        if args.from_date and day < args.from_date:
            continue
        if args.to_date and day > args.to_date:
            continue
    
    by_day[day].append((dt, role, text))

# Determine output directory
if args.output:
    out_dir = args.output
elif args.day:
    out_dir = f"./test_logs_v10_{args.day.replace('-', '')}"
else:
    out_dir = "./test_logs_v10"
os.makedirs(out_dir, exist_ok=True)

total_turns = 0
for day in sorted(by_day.keys()):
    msgs = sorted(by_day[day], key=lambda x: x[0])
    deduped = []
    last_key = None
    for dt, role, text in msgs:
        key = (dt.strftime("%Y-%m-%dT%H:%M:%S"), role, text[:100])
        if key != last_key:
            deduped.append((dt, role, text))
            last_key = key
    out_path = os.path.join(out_dir, f"{day}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Nhật ký ngày {day}\n\n")
        for dt, role, text in deduped:
            who = "User" if role == "user" else "Assistant"
            f.write(f"### [{dt.strftime('%H:%M:%S')}] {who}\n{text}\n\n")
    print(f"  {day}: {len(deduped)} turns")
    total_turns += len(deduped)

print(f"\nDone! {len(by_day)} days, {total_turns} total turns")
