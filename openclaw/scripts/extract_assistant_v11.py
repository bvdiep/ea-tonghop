#!/usr/bin/env python3
"""Extract clean conversations from legacy OpenClaw v3 session directories.

Why this script exists
----------------------
``group_conversations_assistant.py`` only reads ``<sid>.jsonl`` plus a single
checkpoint, never reads ``.trajectory.jsonl`` / rotated archives, and applies
skip-prefixes *before* stripping Telegram metadata. On the assistant agent
that loses roughly two thirds of the real user turns.

This extractor merges every available source and deduplicates messages by
their entry id:

1. ``<sid>.jsonl``                              base transcript
2. ``<sid>.jsonl.reset.*`` / ``.deleted.*`` / ``.bak-*``
                                                 rotated/archived transcripts
3. ``<sid>.checkpoint.<uuid>.jsonl``             latest snapshot (by mtime;
                                                 checkpoints are cumulative,
                                                 older ones are subsets)
4. ``<sid>.trajectory.jsonl``                    ``prompt.submitted`` (user)
                                                 and ``model.completed``
                                                 (assistant)

Filtering happens *after* cleaning, so a real user message that happens to be
wrapped in ``System (untrusted): ...`` or prefixed with
``Conversation info (untrusted metadata):`` is kept.

Usage
-----
    python3 extract_assistant_v11.py \
        --sessions-dir /path/to/agents/assistant/sessions \
        --output ./openclaw/output_v10/assistant_conversations_v11

    # debug a few sessions only
    python3 extract_assistant_v11.py --sessions-dir ... --output ... \
        --session 5d3539a4-0513-43a8-86a6-a160629e44dd

Output
------
- ``NNNN_YYYYMMDD_slug.md`` conversation transcripts (+ ``_index.md``)
- ``messages.jsonl``        one JSON record per message (machine readable)
- ``coverage_report.json``  per-session source/kept/dropped counters
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

# Silence/structure that must never reach the conversation output.
META_PAT = re.compile(
    r"(?:Conversation info|Sender) \(untrusted metadata\):\n"
    r"```(?:json)?\n.*?\n```\n?",
    re.S,
)
CONTEXT_PAT = re.compile(
    r"Conversation context \(untrusted, chronological[^\n]*\n"
    r"(?:#\d+[^\n]*\n?)*"
)
STARTUP_PAT = re.compile(
    r"^A new session was started via /new or /reset\..*", re.S | re.M
)
CURRENT_TIME_PAT = re.compile(r"^Current time: .*$", re.M)
CONTINUE_PAT = re.compile(r"^Continue the OpenClaw.*$", re.M)
UTC_PREFIX_PAT = re.compile(
    r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})? UTC\]\s*"
)
DATE_PREFIX_PAT = re.compile(
    r"^\[(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})? [^\]]*\]\s*"
)
SYSTEM_PREFIX_PAT = re.compile(r"(?m)^System \(untrusted\):\s*")
WRAPPER_PREFIX_PAT = re.compile(
    r"^\[(?:Retry after the previous model attempt failed or timed out|"
    r"Queued user message that arrived while the previous turn was still active)\]\s*"
)
REPLY_TO_CURRENT_PAT = re.compile(r"\[\[reply_to_current\]\]\s*")
FINAL_TAG_PAT = re.compile(r"</?final>")
FAILED_TURN_PAT = re.compile(
    r"^\[assistant turn failed before producing content\]\s*"
)
MEDIA_LINE_PAT = re.compile(r"^\[media attached:[^\n]*\]\n?", re.M)
MEDIA_HINT_PAT = re.compile(
    r"^To send an image back,.*?(?:\n\n|\Z)", re.S | re.M
)
TOOL_CALL_TEXT_PAT = re.compile(
    r"^(?:read|write|edit|exec|bash|glob|grep|ls|cat|apply_patch|"
    r"web_search|web_fetch|message|sessions_spawn|memory_search|"
    r"memory_get|cron|browser|process|nodes)\s*(?:=\s*)?[\(\{].*$",
    re.S | re.I,
)
TOOL_JSON_PREFIXES = ('{"type": "function"', '{"type":"function"')

NOISE_EXACT = {"NO_REPLY", "HEARTBEAT_OK", "<|finish|>", "[OpenClaw heartbeat poll]"}
NOISE_PREFIXES = (
    "[cron:",
    "[OpenClaw",
    "[Startup",
    "[Subagent",
    "[Inter-session",
    "<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>",
    "A new session was started",
    "Continue the OpenClaw",
    "Pre-compaction memory flush",
    "[Bootstrap pending]",
    "System: [",
    "[System]",
    "Read HEARTBEAT.md",
    "/start",
    "HEARTBEAT_OK",
    "NO_REPLY",
    "The script `",
    "The execution of `",
)

SOURCE_PRIORITY = {"base": 0, "archive": 0, "checkpoint": 0, "trajectory": 1}
DEDUP_WINDOW_SECONDS = 300
UNKNOWN_TS = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def parse_ts(value: Any) -> datetime | None:
    """Parse an ISO-8601 string or a Unix-ms integer into an aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def text_of(content: Any) -> str:
    """Flatten OpenClaw message content (str / list of parts / dict)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    if isinstance(content, dict):
        return str(content.get("text", ""))
    return ""


def has_tool_call(content: Any) -> bool:
    if isinstance(content, list):
        return any(
            isinstance(part, dict) and part.get("type") == "toolCall"
            for part in content
        )
    return False


def clean_user_text(raw: str) -> str:
    """Remove transport/runtime boilerplate but keep the actual user text."""
    text = (raw or "").replace("\r\n", "\n")
    text = MEDIA_LINE_PAT.sub("", text)
    text = MEDIA_HINT_PAT.sub("", text)
    while True:
        stripped = WRAPPER_PREFIX_PAT.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped
    text = REPLY_TO_CURRENT_PAT.sub("", text)
    text = STARTUP_PAT.sub("", text)
    text = CURRENT_TIME_PAT.sub("", text)
    text = CONTINUE_PAT.sub("", text)
    text = META_PAT.sub("", text)

    match = CONTEXT_PAT.search(text)
    if match:
        # The current message follows the quoted history block.
        text = text[: match.start()] + text[match.end():]

    text = SYSTEM_PREFIX_PAT.sub("", text)
    text = UTC_PREFIX_PAT.sub("", text)
    text = DATE_PREFIX_PAT.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def clean_assistant_text(raw: str) -> str:
    text = (raw or "").strip()
    text = REPLY_TO_CURRENT_PAT.sub("", text)
    text = FINAL_TAG_PAT.sub("", text)
    text = FAILED_TURN_PAT.sub("", text)
    if looks_like_tool_call(text):
        return ""
    if text.startswith(("[cron:", "# [cron:", "#[cron:")):
        return ""
    return text.strip()


def looks_like_tool_call(text: str) -> bool:
    """Detect legacy tool-call payloads that were stored as assistant text."""
    stripped = text.strip()
    if stripped.startswith(TOOL_JSON_PREFIXES):
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            return True
        if isinstance(obj, dict):
            return "name" in obj or "function_name" in obj
        return True
    return bool(TOOL_CALL_TEXT_PAT.match(stripped))


def user_noise_reason(text: str) -> str | None:
    """Return a reason when a cleaned user message is not a real user turn."""
    stripped = text.strip()
    if not stripped:
        return "empty"
    if stripped in NOISE_EXACT:
        return "status"
    if stripped.startswith(NOISE_PREFIXES):
        return "boilerplate"
    if "heartbeat poll" in stripped[:80]:
        return "heartbeat"
    return None


def assistant_noise_reason(text: str) -> str | None:
    if not text:
        return "empty"
    if text in NOISE_EXACT:
        return "status"
    return None


# ---------------------------------------------------------------------------
# Session inventory
# ---------------------------------------------------------------------------
def classify_file(name: str) -> tuple[str, str] | None:
    """Map a session-directory file name to (session_id, kind)."""
    if name.endswith(".trajectory.jsonl"):
        return None  # handled by load_trajectory
    if ".jsonl" not in name:
        return None
    sid = name.split(".")[0]
    if ".checkpoint." in name and name.endswith(".jsonl"):
        return sid, "checkpoint"
    if any(marker in name for marker in (".reset.", ".deleted.", ".bak")):
        return sid, "archive"
    if name == f"{sid}.jsonl":
        return sid, "base"
    return None


def build_inventory(sessions_dir: str) -> dict[str, dict[str, list[str]]]:
    inventory: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for entry in os.scandir(sessions_dir):
        if not entry.is_file():
            continue
        name = entry.name
        if name.endswith(".trajectory.jsonl"):
            sid = name.split(".")[0]
            inventory[sid]["trajectory"].append(entry.path)
            continue
        classified = classify_file(name)
        if classified is None:
            continue
        sid, kind = classified
        inventory[sid][kind].append(entry.path)
    return {sid: dict(files) for sid, files in inventory.items()}


def iter_records(path: str) -> Iterable[dict]:
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def extract_envelopes(
    path: str,
    source: str,
    messages: dict[tuple, dict],
    dropped: Counter,
    seen: set[tuple],
) -> None:
    for obj in iter_records(path):
        if obj.get("type") != "message":
            continue
        message = obj.get("message") or {}
        role = message.get("role")
        if role not in ("user", "assistant"):
            continue

        # Snapshots repeat entries; skip duplicates before recording drop stats.
        entry_id = obj.get("id")
        dedup_key = ("env", entry_id) if entry_id else None
        if dedup_key is not None:
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

        raw = text_of(message.get("content"))
        timestamp = parse_ts(obj.get("timestamp")) or parse_ts(
            message.get("timestamp")
        )

        if role == "user":
            text = clean_user_text(raw)
            reason = user_noise_reason(text)
            if reason:
                dropped[f"user:{reason}"] += 1
                continue
        else:
            if message.get("stopReason") in ("toolUse", "error"):
                dropped["assistant:toolUse_or_error"] += 1
                continue
            if has_tool_call(message.get("content")):
                dropped["assistant:toolCall"] += 1
                continue
            text = clean_assistant_text(raw)
            reason = assistant_noise_reason(text)
            if reason:
                dropped[f"assistant:{reason}"] += 1
                continue

        if dedup_key is None:
            digest = hashlib.sha1(f"{role}|{timestamp}|{text}".encode()).hexdigest()
            dedup_key = ("env", digest)
        if dedup_key in messages:
            continue
        messages[dedup_key] = {
            "ts": timestamp,
            "role": role,
            "text": text,
            "source": source,
        }


def extract_trajectory(
    path: str,
    messages: dict[tuple, dict],
    dropped: Counter,
) -> None:
    for obj in iter_records(path):
        event_type = obj.get("type")
        if event_type not in ("prompt.submitted", "model.completed"):
            continue
        data = obj.get("data") or {}
        timestamp = parse_ts(obj.get("ts"))

        if event_type == "prompt.submitted":
            text = clean_user_text(str(data.get("prompt") or ""))
            reason = user_noise_reason(text)
            if reason:
                dropped[f"user:{reason}"] += 1
                continue
            role = "user"
        else:
            texts = [
                item
                for item in (data.get("assistantTexts") or [])
                if isinstance(item, str) and item.strip()
            ]
            if not texts:
                dropped["assistant:empty"] += 1
                continue
            text = clean_assistant_text(texts[-1])
            reason = assistant_noise_reason(text)
            if reason:
                dropped[f"assistant:{reason}"] += 1
                continue
            role = "assistant"

        digest = hashlib.sha1(text.encode()).hexdigest()
        ts_key = timestamp.isoformat() if timestamp else ""
        key = ("traj", role, ts_key, digest)
        if key in messages:
            continue
        messages[key] = {
            "ts": timestamp,
            "role": role,
            "text": text,
            "source": "trajectory",
        }


def dedup_across_sources(rows: list[dict]) -> tuple[list[dict], int]:
    """Drop the same role/text reported by both a transcript and trajectory."""
    rows.sort(
        key=lambda row: (
            row["ts"] or datetime.min.replace(tzinfo=timezone.utc),
            SOURCE_PRIORITY.get(row["source"], 9),
        )
    )
    seen: dict[tuple[str, str], datetime | None] = {}
    kept: list[dict] = []
    removed = 0
    for row in rows:
        signature = (row["role"], row["text"])
        previous = seen.get(signature)
        if (
            previous is not None
            and row["ts"] is not None
            and abs((row["ts"] - previous).total_seconds())
            <= DEDUP_WINDOW_SECONDS
        ):
            removed += 1
            continue
        seen[signature] = row["ts"]
        kept.append(row)
    return kept, removed


def extract_session(
    sid: str,
    files: dict[str, list[str]],
    keep_assistant_only: bool,
) -> tuple[list[dict], dict]:
    messages: dict[tuple, dict] = {}
    dropped: Counter = Counter()
    sources: Counter = Counter()
    seen: set[tuple] = set()

    for kind in ("base", "archive"):
        for path in files.get(kind, []):
            extract_envelopes(path, kind, messages, dropped, seen)
            sources[kind] += 1

    checkpoints = files.get("checkpoint", [])
    if checkpoints:
        # A checkpoint is a cumulative snapshot: only the newest one is needed.
        latest = max(checkpoints, key=os.path.getmtime)
        extract_envelopes(latest, "checkpoint", messages, dropped, seen)
        sources["checkpoint"] = 1

    trajectories = files.get("trajectory", [])
    for path in trajectories:
        extract_trajectory(path, messages, dropped)
        sources["trajectory"] += 1

    rows = list(messages.values())
    rows, cross_source_dupes = dedup_across_sources(rows)

    user_count = sum(1 for row in rows if row["role"] == "user")
    assistant_count = len(rows) - user_count
    report = {
        "session": sid,
        "sources": dict(sources),
        "messages": len(rows),
        "user": user_count,
        "assistant": assistant_count,
        "cross_source_duplicates": cross_source_dupes,
        "dropped": dict(dropped),
        "skipped_reason": None,
    }

    if not rows:
        report["skipped_reason"] = "no messages"
        return [], report
    if not user_count and not keep_assistant_only:
        report["skipped_reason"] = "assistant-only"
        return [], report
    return rows, report


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def slugify(text: str, maxlen: int = 40) -> str:
    words = re.sub(
        r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗ"
        r"ơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
        " ",
        text.lower(),
    )
    result = "_".join(word for word in words.split()[:5] if word)
    return result[:maxlen] or "cuoc_tro_chuyen"


def split_conversations(
    rows: list[dict], gap_hours: float
) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    current: list[dict] = []
    for row in rows:
        if not current:
            current = [row]
            continue
        previous = current[-1]
        if (
            previous["ts"] is not None
            and row["ts"] is not None
            and (row["ts"] - previous["ts"]).total_seconds() / 3600 >= gap_hours
        ):
            chunks.append(current)
            current = []
        current.append(row)
    if current:
        chunks.append(current)
    return chunks


def write_output(
    conversations: list[tuple],
    output_dir: str,
    tz: timezone,
    write_jsonl: bool,
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    index = ["# Danh sách conversations\n"]
    jsonl_path = os.path.join(output_dir, "messages.jsonl")
    jsonl_handle = open(jsonl_path, "w", encoding="utf-8") if write_jsonl else None

    try:
        for number, (sid, chunk) in enumerate(conversations, 1):
            start, end = chunk[0]["ts"], chunk[-1]["ts"]
            local_start = (start or UNKNOWN_TS).astimezone(tz)
            local_end = (end or UNKNOWN_TS).astimezone(tz)
            day_span = (local_end.date() - local_start.date()).days
            days_tag = f"+{day_span}ngay" if day_span else ""
            first_user = next(
                (row["text"] for row in chunk if row["role"] == "user"), ""
            )
            file_name = (
                f"{number:04d}_{local_start.strftime('%Y%m%d')}_"
                f"{slugify(first_user)}{('_' + days_tag) if days_tag else ''}.md"
            )
            user_count = sum(1 for row in chunk if row["role"] == "user")
            assistant_count = len(chunk) - user_count

            lines = [
                f"# Conversation #{number:04d}",
                f"- Session: `{sid}`",
                f"- Bắt đầu: {local_start.strftime('%Y-%m-%d %H:%M:%S')} ({local_start.strftime('%z')})",
                f"- Kết thúc: {local_end.strftime('%Y-%m-%d %H:%M:%S')}",
                f"- Số tin nhắn: {len(chunk)} (user {user_count} / assistant {assistant_count})",
                f"- Xuyên ngày: {'có — ' + days_tag if day_span else 'không'}",
                "",
            ]
            for row in chunk:
                local_ts = (row["ts"] or UNKNOWN_TS).astimezone(tz)
                lines.append(
                    f"### [{local_ts.strftime('%H:%M:%S')}] "
                    f"{'User' if row['role'] == 'user' else 'Assistant'}"
                )
                lines.append("")
                lines.append(row["text"])
                lines.append("")
            with open(
                os.path.join(output_dir, file_name), "w", encoding="utf-8"
            ) as handle:
                handle.write("\n".join(lines))

            if jsonl_handle is not None:
                for row in chunk:
                    jsonl_handle.write(
                        json.dumps(
                            {
                                "conversation": number,
                                "session": sid,
                                "role": row["role"],
                                "ts": (row["ts"] or UNKNOWN_TS)
                                .astimezone(tz)
                                .isoformat(),
                                "source": row["source"],
                                "text": row["text"],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

            index.append(
                f"- [{file_name}]({file_name}) — "
                f"{local_start.strftime('%Y-%m-%d %H:%M')} | {len(chunk)} msgs | "
                f"{first_user[:60]}"
            )
    finally:
        if jsonl_handle is not None:
            jsonl_handle.close()

    with open(os.path.join(output_dir, "_index.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(index) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract clean conversations from legacy OpenClaw v3 session "
            "directories (base + archives + latest checkpoint + trajectory)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # full extraction
  python3 extract_assistant_v11.py \\
    --sessions-dir /backup/agents/assistant/sessions \\
    --output ./openclaw/output_v10/assistant_conversations_v11

  # only a few sessions (debug)
  python3 extract_assistant_v11.py --sessions-dir ... --output ... \\
    --session 5d3539a4-0513-43a8-86a6-a160629e44dd

  # date range, keep assistant-only cron work
  python3 extract_assistant_v11.py --sessions-dir ... --output ... \\
    --since 2026-05-01 --until 2026-06-30 --keep-assistant-only
""",
    )
    parser.add_argument("--sessions-dir", required=True, help="Legacy sessions directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--since", help="Keep conversations starting on/after YYYY-MM-DD")
    parser.add_argument("--until", help="Keep conversations starting on/before YYYY-MM-DD")
    parser.add_argument(
        "--gap-hours",
        type=float,
        default=12.0,
        help="Split a session into conversations at gaps >= N hours (default: 12)",
    )
    parser.add_argument(
        "--min-messages",
        type=int,
        default=1,
        help="Skip conversations with fewer messages (default: 1)",
    )
    parser.add_argument(
        "--keep-assistant-only",
        action="store_true",
        help="Keep sessions without any user message (cron work)",
    )
    parser.add_argument(
        "--tz-offset",
        type=float,
        default=7.0,
        help="Display timezone offset in hours (default: 7, GMT+7)",
    )
    parser.add_argument(
        "--session",
        action="append",
        default=[],
        help="Only extract this session id (repeatable)",
    )
    parser.add_argument(
        "--no-jsonl",
        action="store_true",
        help="Do not write messages.jsonl",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tz = timezone(timedelta(hours=args.tz_offset))
    since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=tz) if args.since else None
    until = (
        datetime.strptime(args.until, "%Y-%m-%d").replace(tzinfo=tz)
        + timedelta(days=1)
        if args.until
        else None
    )

    inventory = build_inventory(args.sessions_dir)
    if args.session:
        wanted = set(args.session)
        inventory = {sid: files for sid, files in inventory.items() if sid in wanted}
        missing = wanted - set(inventory)
        for sid in sorted(missing):
            print(f"warning: session not found: {sid}", file=sys.stderr)

    conversations: list[tuple[str, list[dict]]] = []
    reports: list[dict] = []
    totals = Counter()

    for sid in sorted(inventory):
        rows, report = extract_session(
            sid, inventory[sid], args.keep_assistant_only
        )
        reports.append(report)
        totals["sessions"] += 1
        totals["messages"] += report["messages"]
        totals["user"] += report["user"]
        totals["assistant"] += report["assistant"]
        if report["skipped_reason"]:
            totals[f"skipped:{report['skipped_reason']}"] += 1
            continue

        chunks = split_conversations(rows, args.gap_hours)
        for chunk in chunks:
            start_ts = chunk[0]["ts"]
            if start_ts is not None:
                start = start_ts.astimezone(tz)
                if since and start < since:
                    continue
                if until and start >= until:
                    continue
            if len(chunk) < args.min_messages:
                continue
            conversations.append((sid, chunk))

    conversations.sort(
        key=lambda item: item[1][0]["ts"]
        or datetime.max.replace(tzinfo=timezone.utc)
    )
    write_output(conversations, args.output, tz, not args.no_jsonl)

    total_user = sum(
        1 for _, chunk in conversations for row in chunk if row["role"] == "user"
    )
    total_assistant = sum(len(chunk) for _, chunk in conversations) - total_user
    report = {
        "sessions_scanned": totals["sessions"],
        "sessions_skipped": {
            key.split(":", 1)[1]: value
            for key, value in totals.items()
            if key.startswith("skipped:")
        },
        "conversations": len(conversations),
        "messages": {"user": total_user, "assistant": total_assistant},
        "sources": {
            "sessions_with_base": sum(
                1 for files in inventory.values() if files.get("base")
            ),
            "sessions_with_archive": sum(
                1 for files in inventory.values() if files.get("archive")
            ),
            "sessions_with_checkpoint": sum(
                1 for files in inventory.values() if files.get("checkpoint")
            ),
            "sessions_with_trajectory": sum(
                1 for files in inventory.values() if files.get("trajectory")
            ),
        },
        "per_session": reports,
    }
    with open(
        os.path.join(args.output, "coverage_report.json"), "w", encoding="utf-8"
    ) as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(
        f"sessions: {totals['sessions']} | conversations: {len(conversations)} | "
        f"user: {total_user} | assistant: {total_assistant} | out: {args.output}"
    )
    if totals["skipped:assistant-only"]:
        print(
            f"skipped assistant-only sessions: {totals['skipped:assistant-only']} "
            "(use --keep-assistant-only to include)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
