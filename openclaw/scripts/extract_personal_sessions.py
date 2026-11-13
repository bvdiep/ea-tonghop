#!/usr/bin/env python3
"""
Extract daily conversation logs from the OpenClaw *personal* agent backup.

Reads three source types under the backup dir and merges them:
  1. sessions/*.jsonl* (reset + bak files)        -- type="message" envelopes
  2. session-sqlite-import-archive/archive-tier.*.trajectory.jsonl.imported-*
                                                   -- type="context.compiled" -> data.messages[]
  3. session-sqlite-import-archive/agent_personal_telegram_direct_*.jsonl.imported-*
                                                   -- type="message" envelopes

Structural facts about the personal agent (verified 2026-09-26):
  - role=user messages may be EITHER plain real user text OR prefixed metadata
    blocks ("Conversation info (untrusted metadata)" + Sender + Conversation
    context lines). When prefixed, the CURRENT user text is the tail after the
    context block; the "#id ... context" lines are history duplicates -> skip them.
  - role=assistant with stopReason=toolUse / error -> narration/noise, skip.
  - assistant texts may carry a "[[reply_to_current]]" prefix (streamed draft
    copy). Strip before dedup so the clean copy wins.
  - Noise user texts: heartbeat polls, "A new session was started...",
    "[OpenClaw heartbeat poll]", pre-compaction metadata.
Output: one Markdown file per day (GMT+7), written to <sessions>/tmp/nhatky_v2/
by default, next to the old v1 output (which is left untouched).

Usage:
  python3 extract_personal_sessions.py [--backup-dir DIR] [--out-dir DIR]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

TZ7 = timezone(timedelta(hours=7))
DEFAULT_BACKUP = "/media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/personal"

META_PREFIX = "Conversation info (untrusted metadata)"
NOISE_USER_EXACT = {
    "[OpenClaw heartbeat poll]",
}
NOISE_USER_SUBSTR = (
    "A new session was started via /new or /reset",
    "Pre-compaction memory flush",
    "Conversation info (untrusted metadata)",
)
NOISE_ASSISTANT_EXACT = {"NO_REPLY", "<|finish|>", "HEARTBEAT_OK"}

CTX_LINE_RE = re.compile(r"^#\d+\s+\w{3}\s+[\d\-]+\s+\d\d:\d\d\s+UTC\s+\S+:\s.*$")


def extract_text(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content
                 if isinstance(c, dict) and c.get("type") == "text"]
        return "".join(p for p in parts if p).strip()
    if isinstance(content, dict):
        return content.get("text", "")
    return ""


def strip_reply_prefix(text):
    if text.startswith("[[reply_to_current]]"):
        return text[len("[[reply_to_current]]"):].lstrip()
    return text


def is_noise_user(text):
    t = text.strip()
    if t in NOISE_USER_EXACT:
        return True
    return any(s in t for s in NOISE_USER_SUBSTR)


def is_noise_assistant(text):
    return text.strip() in NOISE_ASSISTANT_EXACT


def parse_meta_ts(meta_text):
    """Extract 'timestamp' from the Conversation info JSON block."""
    m = re.search(r'"timestamp"\s*:\s*"([^"]+)"', meta_text)
    if not m:
        return None
    raw = m.group(1)  # e.g. "Fri 2026-08-07 08:40 UTC"
    try:
        dt = datetime.strptime(raw, "%a %Y-%m-%d %H:%M %Z").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def user_current_text(text):
    """
    If text is a metadata block, return only the current user message (tail
    after the Conversation context block). If plain text, return it unchanged
    (unless it is noise -> "").
    """
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.startswith(META_PREFIX):
        # Drop the two JSON metadata blocks (Conversation info + Sender).
        rest = re.sub(
            r"Conversation info \(untrusted metadata\):\s*```json\s*\{.*?\}\s*```\s*"
            r"Sender \(untrusted metadata\):\s*```json\s*\{.*?\}\s*```",
            "", stripped, flags=re.S,
        )
        # Drop context header + context lines; keep the tail (current message).
        if "Conversation context (untrusted, chronological" in rest:
            parts = re.split(
                r"Conversation context \(untrusted, chronological[^:]*:*\s*\n", rest, maxsplit=1)
            if len(parts) == 2:
                body = parts[1]
                lines = body.splitlines()
                # consume context header lines (#id Day Date Time UTC sender: text)
                i = 0
                while i < len(lines) and CTX_LINE_RE.match(lines[i]):
                    i += 1
                rest = "\n".join(lines[i:])
        return rest.strip()
    # Plain text: keep real user input, drop known system noise.
    if is_noise_user(stripped):
        return ""
    return stripped


def msg_timestamp(d, m):
    """Message-level ms timestamp, else envelope timestamp, else None."""
    ts = m.get("timestamp") if isinstance(m, dict) else None
    if isinstance(ts, (int, float)):
        return int(ts)
    env_ts = d.get("timestamp")
    if isinstance(env_ts, str):
        try:
            dt = datetime.fromisoformat(env_ts.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass
    return None


def collect_from_envelope_file(filepath):
    """type='message' envelopes (jsonl reset/bak, direct telegram)."""
    out = []  # (ts_ms, role, text, src)
    try:
        fh = open(filepath, "r", errors="replace")
    except OSError:
        return out
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except (ValueError, json.JSONDecodeError):
                continue
            if d.get("type") != "message":
                continue
            m = d.get("message")
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue
            text = extract_text(m.get("content"))
            if not text:
                continue
            ts = msg_timestamp(d, m)
            if ts is None:
                ts = parse_meta_ts(text)
            if role == "user":
                cur = user_current_text(text)
                if not cur:
                    continue
                out.append((ts, "user", cur, os.path.basename(filepath)))
            else:  # assistant
                st = m.get("stopReason")
                if st in ("toolUse", "error"):
                    continue
                clean = strip_reply_prefix(text).strip()
                if is_noise_assistant(clean):
                    continue
                if not clean:
                    continue
                out.append((ts, "assistant", clean, os.path.basename(filepath)))
    return out


def collect_from_trajectory_file(filepath):
    """type='context.compiled' entries -> data.messages[]."""
    out = []
    try:
        fh = open(filepath, "r", errors="replace")
    except OSError:
        return out
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except (ValueError, json.JSONDecodeError):
                continue
            if d.get("type") != "context.compiled":
                continue
            data = d.get("data")
            if not isinstance(data, dict):
                continue
            for m in data.get("messages", []) or []:
                if not isinstance(m, dict):
                    continue
                role = m.get("role")
                if role not in ("user", "assistant"):
                    continue
                text = extract_text(m.get("content"))
                if not text:
                    continue
                ts = msg_timestamp(d, m)
                if role == "user":
                    cur = user_current_text(text)
                    if not cur:
                        continue
                    if ts is None:
                        ts = parse_meta_ts(text)
                    out.append((ts, "user", cur, os.path.basename(filepath)))
                else:
                    st = m.get("stopReason")
                    if st not in ("stop", None, "end_turn", "max_tokens"):
                        # trajectory keeps only valid final responses
                        if st not in (None,) and st != "stop":
                            continue
                    clean = strip_reply_prefix(text).strip()
                    if is_noise_assistant(clean) or not clean:
                        continue
                    out.append((ts, "assistant", clean, os.path.basename(filepath)))
    return out


def scan_backup(backup_dir):
    sessions_dir = os.path.join(backup_dir, "sessions")
    archive_dir = os.path.join(backup_dir, "session-sqlite-import-archive")
    all_msgs = []
    sources = {"envelope": 0, "trajectory": 0, "direct": 0}

    if os.path.isdir(sessions_dir):
        for fn in sorted(os.listdir(sessions_dir)):
            if "trajectory" in fn:
                continue
            if not (fn.endswith(".jsonl") or ".jsonl." in fn):
                continue
            fp = os.path.join(sessions_dir, fn)
            if not os.path.isfile(fp):
                continue
            all_msgs.extend(collect_from_envelope_file(fp))
            sources["envelope"] += 1

    if os.path.isdir(archive_dir):
        for fn in sorted(os.listdir(archive_dir)):
            fp = os.path.join(archive_dir, fn)
            if not os.path.isfile(fp):
                continue
            if ".trajectory.jsonl.imported-" in fn:
                all_msgs.extend(collect_from_trajectory_file(fp))
                sources["trajectory"] += 1
            elif "direct" in fn and ".jsonl.imported-" in fn and ".trajectory." not in fn:
                all_msgs.extend(collect_from_envelope_file(fp))
                sources["direct"] += 1

    return all_msgs, sources


def dedup(messages):
    """Dedup by (day, role, normalized text); keep the cleanest copy per day.

    Unlike the assistant-agent extractor (which dedups globally because cron
    jobs repeat identical content across days), personal-agent messages are
    real conversation: the same text can be an independent message on
    different days ("anh nhớ em" on Aug 14 AND Aug 30), so the key is
    scoped to the day (GMT+7). Within a day, normalization collapses
    whitespace so streamed draft vs delivered final (differing only by a
    stray space) collapse to one entry, and the 40+ trajectory-internal
    repeats of the same context message collapse to one. When two texts in
    the same day collide, prefer the non-[[reply_to_current]] copy, then the
    longer one; timestamps keep the earliest.
    """
    seen = {}
    for ts, role, text, src in messages:
        if not text or not text.strip():
            continue
        clean_text = text.strip()
        norm = re.sub(r"\s+", " ", clean_text)
        day = "nots"
        if ts is not None:
            day = datetime.fromtimestamp(ts / 1000, tz=TZ7).strftime("%Y-%m-%d")
        key = (day, role, hashlib.md5(norm.encode("utf-8")).hexdigest())
        had_prefix = text.lstrip().startswith("[[reply_to_current]]")
        cur = seen.get(key)
        if cur is None:
            seen[key] = (ts, role, clean_text, had_prefix, norm)
        else:
            cur_ts, cur_role, cur_text, cur_prefix, cur_norm = cur
            # priority: clean (no prefix) > longer; keep earliest ts
            better = False
            if cur_prefix and not had_prefix:
                better = True
            elif cur_prefix == had_prefix and len(clean_text) > len(cur_text):
                better = True
            if better:
                seen[key] = (ts, role, clean_text, had_prefix, norm)
            elif ts is not None and (cur_ts is None or ts < cur_ts):
                seen[key] = (ts, role, cur_text, cur_prefix, cur_norm)
    return [(v[0], v[1], v[2]) for v in seen.values()]


def main():
    ap = argparse.ArgumentParser(description="Extract personal-agent daily logs.")
    ap.add_argument("--backup-dir", default=DEFAULT_BACKUP)
    ap.add_argument("--out-dir", default=None,
                    help="default: <backup-dir>/.tmp/nhatky_v2")
    args = ap.parse_args()

    backup = args.backup_dir
    out_dir = args.out_dir or os.path.join(backup, ".tmp", "nhatky_v2")
    os.makedirs(out_dir, exist_ok=True)

    raw, sources = scan_backup(backup)
    print(f"sources scanned: {sources}")
    print(f"raw candidate messages: {len(raw)}")
    msgs = dedup(raw)
    print(f"after global dedup: {len(msgs)}")

    by_day = defaultdict(list)
    no_ts = 0
    for ts, role, text in msgs:
        if ts is None:
            no_ts += 1
            continue
        dt = datetime.fromtimestamp(ts / 1000, tz=TZ7)
        by_day[dt.strftime("%Y-%m-%d")].append((dt, role, text))
    print(f"messages without timestamp dropped: {no_ts}")

    total_out = 0
    for day in sorted(by_day):
        rows = sorted(by_day[day], key=lambda r: r[0])
        # adjacent consecutive duplicate guard (same role+text within 60s)
        merged = []
        last = None
        for dt, role, text in rows:
            if last and last[2] == text and abs((dt - last[0]).total_seconds()) < 60:
                continue
            merged.append((dt, role, text))
            last = (dt, role, text)
        fp = os.path.join(out_dir, f"{day}.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"# Nhật ký ngày {day}\n\n")
            for dt, role, text in merged:
                who = "User" if role == "user" else "Assistant"
                f.write(f"### [{dt.strftime('%H:%M:%S')}] {who}\n{text}\n\n")
        total_out += len(merged)
        print(f"  {day}: {len(merged)} turns -> {fp}")
    print(f"\nDone. {len(by_day)} days, {total_out} turns -> {out_dir}")


if __name__ == "__main__":
    main()