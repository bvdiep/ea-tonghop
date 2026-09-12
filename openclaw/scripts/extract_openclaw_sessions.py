#!/usr/bin/env python3
"""
Extract clean daily memory logs from OpenClaw session JSONL files.

Usage:
    python extract_openclaw_sessions.py [sessions_dir] [output_dir]

Arguments:
    sessions_dir  Path to OpenClaw sessions directory (default: ~/.openclaw/agents/assistant/sessions)
    output_dir    Path to output markdown files (default: ./test_logs)

Rules (3 session-level + 9 message-level):
    Session-level (remove entire session):
        - Cron-only: [cron: + <=1 user msg
        - Heartbeat-only: [OpenClaw heartbeat poll] + <=2 user msg
        - Subagent-only: [Subagent Context] or [Subagent Task]

    Message-level (remove individual messages):
        1. Assistant with toolCall (narration before tool execution)
        2. stopReason=toolUse + no toolCall (corrupted artifact)
        3. HEARTBEAT_OK/NO_REPLY status reports
        4. </think>/</thinking> artifacts
        5. Prompt leak (>=2 system prompt markers)
        6. Cron/heartbeat messages
        7. Thinking Process: leaked text
        8. Internal context (provenance field)
        9. Inter-session messages

Output:
    Markdown files (one per day) with format:
    ### [hh:mm:ss] User|Assistant
    message content...

Author: OpenClaw extraction pipeline
"""
import json, os, hashlib
from datetime import datetime, timezone, timedelta
from collections import defaultdict

tz7 = timezone(timedelta(hours=7))


def safe_json(line):
    try:
        return json.loads(line)
    except:
        return None


def has_tool_call(content):
    """Check if content list has a toolCall part"""
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
    """Check if message is a cron job message"""
    if role == "user":
        return text.strip().startswith("[cron:")
    if role == "assistant":
        txt = text.strip()
        return txt in ("NO_REPLY", "<|finish|>", "HEARTBEAT_OK")
    return False


def is_internal_context(d, msg):
    """Check if message is an internal runtime context (subagent completion, etc.)"""
    if "provenance" in msg:
        return True
    return False


def is_heartbeat_poll(role, text):
    """Check if message is a heartbeat poll"""
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
    """Check if tool result is just [STATUS] noise"""
    txt = text.strip()
    return txt.startswith("[STATUS]")


def is_inter_session_text(text):
    """Check if text is inter-session/internal context noise"""
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
    """Check if session is a subagent session"""
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


def extract_messages_from_file(filepath):
    """Extract messages, filtering by session-level and message-level rules"""
    results = []
    is_trajectory = ".trajectory." in filepath
    with open(filepath, "r", errors="replace") as fh:
        lines = fh.readlines()

    # First pass: analyze session structure
    all_msgs = []
    user_msg_count = 0
    has_cron_prompt = False
    has_heartbeat_poll = False
    has_subagent_context = False
    first_user_text = ''

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
                if not first_user_text:
                    first_user_text = txt
                if txt.strip().startswith("[cron:"):
                    has_cron_prompt = True
                if "[OpenClaw heartbeat poll]" in txt.strip():
                    has_heartbeat_poll = True
                if is_subagent_session(txt):
                    has_subagent_context = True

    # Session-level filtering
    # Remove cron-only sessions
    if has_cron_prompt and user_msg_count <= 1:
        return results

    # Remove heartbeat-only sessions
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

    # Remove subagent sessions
    if has_subagent_context:
        return results

    # Second pass: extract messages from remaining sessions
    for d, msg in all_msgs:
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue

        content = msg.get("content")
        text = extract_text(content)
        if not text:
            continue

        # Message-level filtering
        if role == "assistant" and has_tool_call(content):
            continue
        if role == "assistant" and msg.get("stopReason") == "toolUse" and not has_tool_call(content):
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
                if role == "assistant" and has_tool_call(content):
                    continue
                if role == "assistant" and m.get("stopReason") == "toolUse" and not has_tool_call(content):
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
                ts_ms = parse_ts_ms(d, m)
                results.append((ts_ms, role, text, filepath))

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract clean daily memory logs from OpenClaw sessions")
    parser.add_argument("sessions_dir", nargs="?", default=os.path.expanduser("~/.openclaw/agents/assistant/sessions"),
                        help="Path to sessions directory")
    parser.add_argument("output_dir", nargs="?", default="./test_logs",
                        help="Path to output markdown files")
    parser.add_argument("--timezone", type=int, default=7, help="Timezone offset (default: 7 for GMT+7)")
    args = parser.parse_args()

    global tz7
    tz7 = timezone(timedelta(hours=args.timezone))

    sessions_dir = args.sessions_dir
    out_dir = args.output_dir

    all_files = []
    for fn in os.listdir(sessions_dir):
        fp = os.path.join(sessions_dir, fn)
        if os.path.isfile(fp) and (fn.endswith('.jsonl') or fn.endswith('.trajectory.jsonl') or '.jsonl.reset.' in fn):
            all_files.append(fp)

    print(f"Total files to scan: {len(all_files)}")

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
        by_day[day].append((dt, role, text))

    # Output
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


if __name__ == "__main__":
    main()
