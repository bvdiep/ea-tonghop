#!/usr/bin/env python3
"""Group personal-agent messages into CONVERSATIONS (session-based).

Logic:
- Unit = OpenClaw session (real conversation container; 33 sessions total).
- Long-lived session with an internal gap >= GAP_SPLIT_HOURS is split into
  separate conversations at the gap (90fa4a83: one 308h gap -> 2 convos).
- Cross-day sessions stay as ONE conversation (dated by start day).
- Messages come from prompt.submitted (role=user, tail after metadata block)
  and model.completed (role=assistant) events.

Output: conversations/NNNN_<day>_<slug>.md + _index.md
"""
import glob, json, os, re, sys
from datetime import datetime, timezone, timedelta

TZ7 = timedelta(hours=7)
GAP_SPLIT_HOURS = 12  # sessions naturally reset after ~12h idle

ARCHIVE_DIR = "/media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/personal/session-sqlite-import-archive"

META_PAT = re.compile(
    r"Conversation info \(untrusted metadata\):\n```json\n\{.*?\}\n```"
    r"(?:\n+Sender \(untrusted metadata\):\n```json\n\{.*?\}\n```)?",
    re.S,
)
CTX_PAT = re.compile(
    r"Conversation context \(untrusted, chronological[^\n]*\n(?:#\d+[^\n]*\n)*")

NOISE_EXACT = {"[OpenClaw heartbeat poll]", "NO_REPLY", "<|finish|>", "HEARTBEAT_OK"}


def clean_user(text):
    if not text:
        return ""
    out = META_PAT.sub("", text)
    ctx = CTX_PAT.search(out)
    if ctx:
        out = out[:ctx.start()] + out[ctx.end():]
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def clean_assistant(text):
    if not text:
        return ""
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    t = text.strip()
    if t.startswith("[[reply_to_current]]"):
        t = t[len("[[reply_to_current]]"):].strip()
    return t


def parse_ts(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")) + TZ7
    except Exception:
        return None


def load_events():
    events = {}  # sid -> list of (dt, role, text)
    for fp in sorted(glob.glob(f"{ARCHIVE_DIR}/*.trajectory.jsonl.imported-*")):
        with open(fp) as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                sid = o.get("sessionId")
                t = o.get("type")
                if not sid or t not in ("prompt.submitted", "model.completed"):
                    continue
                dt = parse_ts(o.get("ts") or "")
                if not dt:
                    continue
                d = o.get("data") or {}
                if t == "prompt.submitted":
                    text = clean_user(str(d.get("prompt") or ""))
                    if not text or text in NOISE_EXACT:
                        continue
                    if text.startswith("[cron:"):
                        continue
                    events.setdefault(sid, []).append((dt, "user", text))
                else:
                    texts = d.get("assistantTexts") or []
                    text = clean_assistant(texts[-1] if texts else (d.get("text") or ""))
                    if not text or text in NOISE_EXACT:
                        continue
                    events.setdefault(sid, []).append((dt, "assistant", text))
    for sid in events:
        events[sid].sort(key=lambda x: x[0])
    return events


def slugify(text, maxlen=40):
    words = re.sub(r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", " ", text.lower())
    words = "_".join(w for w in words.split()[:5] if w)
    return words[:maxlen] or "cuoc_tro_chuyen"


def main(out_dir):
    events = load_events()
    convos = []  # (start_dt, sid, [msgs])
    for sid, msgs in events.items():
        # split long-lived sessions at big internal gaps
        chunks, cur = [], [msgs[0]]
        for i in range(1, len(msgs)):
            gap = (msgs[i][0] - msgs[i-1][0]).total_seconds() / 3600
            if gap >= GAP_SPLIT_HOURS:
                chunks.append(cur)
                cur = []
            cur.append(msgs[i])
        chunks.append(cur)
        for ch in chunks:
            convos.append((ch[0][0], sid, ch))
    convos.sort(key=lambda c: c[0])

    os.makedirs(out_dir, exist_ok=True)
    index = ["# Danh sách conversations (agent personal)\n"]
    total_msgs = 0
    for n, (start, sid, msgs) in enumerate(convos, 1):
        end = msgs[-1][0]
        day_span = (end.date() - start.date()).days
        days_tag = f"+{day_span}ngay" if day_span else ""
        fname = f"{n:04d}_{start.strftime('%Y%m%d')}_{slugify(msgs[0][2])}{('_' + days_tag) if days_tag else ''}.md"
        total_msgs += len(msgs)
        first_user = next((m[2] for m in msgs if m[1] == "user"), "")
        lines = [
            f"# Conversation #{n:04d}",
            f"- Session: `{sid}`",
            f"- Bắt đầu: {start.strftime('%Y-%m-%d %H:%M:%S')} (GMT+7)",
            f"- Kết thúc: {end.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Số tin nhắn: {len(msgs)} (user {sum(1 for m in msgs if m[1]=='user')} / assistant {sum(1 for m in msgs if m[1]=='assistant')})",
            f"- Xuyên ngày: {'có — ' + days_tag if day_span else 'không'}",
            "",
        ]
        for dt, role, text in msgs:
            lines.append(f"### [{dt.strftime('%H:%M:%S')}] {'User' if role=='user' else 'Assistant'}")
            lines.append("")
            lines.append(text)
            lines.append("")
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        index.append(f"- [{fname}](conversations/{fname}) — {start.strftime('%Y-%m-%d %H:%M')}"
                     f" | {len(msgs)} msgs | {first_user[:60]}")
    with open(os.path.join(out_dir, "_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index) + "\n")
    print(f"conversations: {len(convos)} | total messages: {total_msgs} | out: {out_dir}")
    # report multi-session days and multi-day convos
    multi_day = [c for c in convos if (c[2][-1][0].date() - c[0].date()).days >= 1]
    print(f"conversations spanning >=2 days: {len(multi_day)}")
    return convos


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/personal_conversations"
    main(out)
