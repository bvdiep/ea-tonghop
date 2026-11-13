#!/usr/bin/env python3
"""Group assistant-agent messages into CONVERSATIONS (session-based).

Source: sessions/*.jsonl (v3 envelopes, type="message"). 16.733 files but
only ~1.292 sessions hold real conversation — the rest are cron/heartbeat/
subagent/empty, filtered at message level.

Rules (aligned with extract_v10 + skill pitfalls):
- user: skip metadata blocks (Conversation info/Sender/context history),
  cron prompts, heartbeat polls, runtime/internal banners.
- assistant: skip toolCall/stopReason=toolUse, NO_REPLY/<|finish|>/HEARTBEAT_OK,
  failed-turn prefixes, [[reply_to_current]], completion artifacts.
- Session = conversation; split at internal gap >= 12h (GAP_SPLIT_HOURS).

Output: <out>/NNNN_<day>_<slug>.md + _index.md
"""
import glob, json, os, re, sys
from datetime import datetime, timezone, timedelta

TZ7 = timedelta(hours=7)
GAP_SPLIT_HOURS = 12

SESSIONS_DIR = "/media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/assistant/sessions"

META_PAT = re.compile(
    r"Conversation info \(untrusted metadata\):\n```json\n\{.*?\}\n```"
    r"(?:\n+Sender \(untrusted metadata\):\n```json\n\{.*?\}\n```)?",
    re.S,
)
CTX_PAT = re.compile(
    r"Conversation context \(untrusted, chronological[^\n]*\n(?:#\d+[^\n]*\n)*")

NOISE_EXACT = {"[OpenClaw heartbeat poll]", "NO_REPLY", "<|finish|>", "HEARTBEAT_OK"}
USER_SKIP_PREFIXES = (
    "[cron:", "[OpenClaw", "[Startup", "[Subagent", "[Inter-session",
    "<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>",
    "A new session was started via /new or /reset",
    "/start",
    "Conversation info (untrusted metadata):",
    "Sender (untrusted metadata):",
    "Pre-compaction memory flush",
    "[Tue 20", "[Mon 20", "[Wed 20", "[Thu 20", "[Fri 20", "[Sat 20", "[Sun 20",
    "Continue the OpenClaw",
)
ASSISTANT_ARTIFACTS = re.compile(
    r"<\|thought\|>|<\|channel|<function-call>|\\begin\{center\}")


def clean_user(text):
    out = META_PAT.sub("", text)
    ctx = CTX_PAT.search(out)
    if ctx:
        out = out[:ctx.start()] + out[ctx.end():]
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def clean_assistant(text):
    t = text.strip()
    t = re.sub(r"\[\[reply_to_current\]\]\s*", "", t)
    if t.startswith("[assistant turn failed before producing content]"):
        t = t[len("[assistant turn failed before producing content]"):].strip()
    if t.startswith("[cron:") or t.startswith("# [cron:") or t.startswith("#[cron:"):
        return ""
    return t


def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(c.get("text", "") for c in content
                       if isinstance(c, dict) and c.get("type") == "text")
    if isinstance(content, dict):
        return content.get("text", "")
    return ""


def parse_ts(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")) + TZ7
    except Exception:
        return None


def load_events():
    events = {}  # sid -> [(dt, role, text)]
    all_jsonl = sorted(glob.glob(f"{SESSIONS_DIR}/*.jsonl"))
    # Checkpoint files are full snapshots of the same session — keep only the
    # base file when it exists, else the LATEST checkpoint per session.
    # NOTE: exclude *.trajectory.jsonl (also matches *.jsonl glob!) — the
    # trajectory format has no type="message" envelopes.
    by_sid = {}
    for fp in all_jsonl:
        base = os.path.basename(fp)
        if base.endswith(".trajectory.jsonl"):
            continue
        sid = base.split(".")[0]
        if ".checkpoint." in base:
            by_sid.setdefault(sid, {"base": None, "ckpts": []})["ckpts"].append(fp)
        else:
            by_sid.setdefault(sid, {"base": None, "ckpts": []})["base"] = fp
    chosen = []
    for sid, d in by_sid.items():
        if d["base"]:
            chosen.append(d["base"])
        elif d["ckpts"]:
            chosen.append(max(d["ckpts"]))  # latest snapshot
    for fp in chosen:
        sid = os.path.basename(fp).split(".")[0]
        try:
            with open(fp) as f:
                for line in f:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    if o.get("type") != "message":
                        continue
                    m = o.get("message") or {}
                    role = m.get("role")
                    if role not in ("user", "assistant"):
                        continue
                    dt = parse_ts(o.get("timestamp") or "")
                    if not dt:
                        continue
                    raw = extract_text(m.get("content"))
                    if not raw.strip():
                        continue
                    if role == "user":
                        if raw.strip() in NOISE_EXACT:
                            continue
                        if raw.lstrip().startswith(USER_SKIP_PREFIXES):
                            continue
                        if "heartbeat poll" in raw[:80]:
                            continue
                        text = clean_user(raw)
                        if not text:
                            continue
                    else:
                        if m.get("stopReason") in ("toolUse", "error"):
                            continue
                        text = clean_assistant(raw)
                        if not text or text in NOISE_EXACT:
                            continue
                        if ASSISTANT_ARTIFACTS.search(text) and len(text) < 400:
                            continue
                    events.setdefault(sid, []).append((dt, role, text.strip()))
        except Exception:
            continue
    for sid in events:
        events[sid].sort(key=lambda x: x[0])
    return events


def slugify(text, maxlen=40):
    words = re.sub(r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", " ", text.lower())
    words = "_".join(w for w in words.split()[:5] if w)
    return words[:maxlen] or "cuoc_tro_chuyen"


def main(out_dir):
    events = load_events()
    # drop sessions whose only content is assistant-only cron work? No — keep
    # (per Pitfall 5: assistant-only sessions contain valuable work).
    convos = []
    for sid, msgs in events.items():
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
    index = ["# Danh sách conversations (agent assistant)\n"]
    total_msgs = 0
    for n, (start, sid, msgs) in enumerate(convos, 1):
        end = msgs[-1][0]
        day_span = (end.date() - start.date()).days
        days_tag = f"+{day_span}ngay" if day_span else ""
        fname = f"{n:04d}_{start.strftime('%Y%m%d')}_{slugify(msgs[0][2])}{('_' + days_tag) if days_tag else ''}.md"
        total_msgs += len(msgs)
        first_user = next((m[2] for m in msgs if m[1] == "user"), "")
        nu = sum(1 for m in msgs if m[1] == "user")
        na = len(msgs) - nu
        lines = [
            f"# Conversation #{n:04d}",
            f"- Session: `{sid}`",
            f"- Bắt đầu: {start.strftime('%Y-%m-%d %H:%M:%S')} (GMT+7)",
            f"- Kết thúc: {end.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Số tin nhắn: {len(msgs)} (user {nu} / assistant {na})",
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
    multi_day = [c for c in convos if (c[2][-1][0].date() - c[0].date()).days >= 1]
    print(f"conversations: {len(convos)} | total messages: {total_msgs} | out: {out_dir}")
    print(f"conversations spanning >=2 days: {len(multi_day)}")
    return convos


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/assistant_conversations"
    main(out)
