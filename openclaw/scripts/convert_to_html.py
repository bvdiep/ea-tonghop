#!/usr/bin/env python3
"""
Convert daily markdown logs to HTML chat-bubble format.

Usage:
    python convert_to_html.py [md_dir] [html_dir]

Arguments:
    md_dir   Path to markdown files (default: ./test_logs)
    html_dir Path to output HTML files (default: ./test_logs_html)
"""
import os, re, html


def escape_html(text):
    return html.escape(text)


def md_to_html_simple(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    text = text.replace('\n', '<br>\n')
    return text


msg_pattern = re.compile(r'^### \[(\d{2}:\d{2}:\d{2})\]\s+(User|Assistant)\s*$')

DARK_THEME_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:20px;line-height:1.6}
.container{max-width:800px;margin:0 auto}
h1{text-align:center;padding:20px 0;color:#e94560;font-size:1.5em;border-bottom:1px solid #333;margin-bottom:20px}
.msg{margin:12px 0;padding:12px 16px;border-radius:12px;max-width:75%;word-wrap:break-word}
.msg.user{background:#16213e;border-left:3px solid #0f3460;margin-right:auto}
.msg.assistant{background:#0f3460;border-left:3px solid #e94560;margin-left:auto}
.msg .time{font-size:.75em;color:#888;margin-bottom:4px}
.msg .role{font-size:.8em;font-weight:bold;margin-bottom:6px}
.msg.user .role{color:#4ea8de}
.msg.assistant .role{color:#e94560}
.msg .content a{color:#4ea8de;text-decoration:none}
.msg .content code{background:#1a1a2e;padding:2px 6px;border-radius:4px;font-size:.85em}
.stats{text-align:center;color:#666;font-size:.85em;margin-bottom:15px}
"""


def convert_file(md_path, html_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    day_title = ""
    messages = []
    current_msg = None
    current_text = []
    for line in lines:
        if line.startswith('# Nhật ký ngày '):
            day_title = line.replace('# Nhật ký ngày ', '').strip()
            continue
        m = msg_pattern.match(line)
        if m:
            if current_msg:
                messages.append((current_msg[0], current_msg[1], '\n'.join(current_text).strip()))
            time_str = m.group(1)
            role = m.group(2)
            current_msg = (time_str, role)
            current_text = []
        elif current_msg is not None:
            current_text.append(line)
    if current_msg:
        messages.append((current_msg[0], current_msg[1], '\n'.join(current_text).strip()))

    parts = []
    parts.append('<!DOCTYPE html>\n<html lang="vi"><head><meta charset="utf-8">\n')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">\n')
    parts.append('<title>Nhat ky ' + escape_html(day_title) + '</title>\n')
    parts.append('<style>\n' + DARK_THEME_CSS + '</style></head><body><div class="container">\n')
    parts.append('<h1>📅 Nhật ký ngày ' + escape_html(day_title) + '</h1>\n')
    parts.append('<div class="stats">' + str(len(messages)) + ' tin nhắn</div>\n')

    for time_str, role, text in messages:
        role_class = 'user' if role == 'User' else 'assistant'
        role_name = '👤 User' if role == 'User' else '🤖 Assistant'
        content_html = md_to_html_simple(escape_html(text))
        parts.append('<div class="msg ' + role_class + '">\n')
        parts.append('  <div class="time">' + time_str + '</div>\n')
        parts.append('  <div class="role">' + role_name + '</div>\n')
        parts.append('  <div class="content">' + content_html + '</div>\n')
        parts.append('</div>\n')

    parts.append('</div></body></html>')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))
    return len(messages)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert daily markdown logs to HTML")
    parser.add_argument("md_dir", nargs="?", default="./test_logs", help="Path to markdown files")
    parser.add_argument("html_dir", nargs="?", default="./test_logs_html", help="Path to output HTML files")
    args = parser.parse_args()

    md_files = sorted([f for f in os.listdir(args.md_dir) if f.endswith('.md')])
    print(f"Converting {len(md_files)} files...")

    os.makedirs(args.html_dir, exist_ok=True)
    for fn in md_files:
        md_path = os.path.join(args.md_dir, fn)
        html_name = fn.replace('.md', '.html')
        html_path = os.path.join(args.html_dir, html_name)
        count = convert_file(md_path, html_path)
        size_kb = os.path.getsize(html_path) // 1024
        print(f"  {html_name}: {count} msgs, {size_kb} KB")

    print(f"\nDone! Output: {args.html_dir}")


if __name__ == "__main__":
    main()
