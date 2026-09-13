#!/usr/bin/env python3
import os, re, html

input_dir = "/home/diep/.openclaw/agents/assistant/.tmp/recovery_memory_v3/test_logs_v10"
output_dir = "/home/diep/.openclaw/agents/assistant/.tmp/recovery_memory_v3/test_logs_v10_html"
os.makedirs(output_dir, exist_ok=True)

msg_pattern = re.compile(r'^### \[(\d{2}:\d{2}:\d{2})\]\s+(User|Assistant)\s*$')

def escape_html(text):
    return html.escape(text)

def md_to_html_simple(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    text = text.replace('\n', '<br>\n')
    return text

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
    parts.append('<style>\n')
    parts.append('*{box-sizing:border-box;margin:0;padding:0}\n')
    parts.append('body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:20px;line-height:1.6}\n')
    parts.append('.container{max-width:800px;margin:0 auto}\n')
    parts.append('h1{text-align:center;padding:20px 0;color:#e94560;font-size:1.5em;border-bottom:1px solid #333;margin-bottom:20px}\n')
    parts.append('.msg{margin:12px 0;padding:12px 16px;border-radius:12px;max-width:75%;word-wrap:break-word}\n')
    parts.append('.msg.user{background:#16213e;border-left:3px solid #0f3460;margin-right:auto}\n')
    parts.append('.msg.assistant{background:#0f3460;border-left:3px solid #e94560;margin-left:auto}\n')
    parts.append('.msg .time{font-size:.75em;color:#888;margin-bottom:4px}\n')
    parts.append('.msg .role{font-size:.8em;font-weight:bold;margin-bottom:6px}\n')
    parts.append('.msg.user .role{color:#4ea8de}\n')
    parts.append('.msg.assistant .role{color:#e94560}\n')
    parts.append('.msg .content a{color:#4ea8de;text-decoration:none}\n')
    parts.append('.msg .content code{background:#1a1a2e;padding:2px 6px;border-radius:4px;font-size:.85em}\n')
    parts.append('.stats{text-align:center;color:#666;font-size:.85em;margin-bottom:15px}\n')
    parts.append('</style></head><body><div class="container">\n')
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

md_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.md')])
print(f"Converting {len(md_files)} files...")

for fn in md_files:
    md_path = os.path.join(input_dir, fn)
    html_name = fn.replace('.md', '.html')
    html_path = os.path.join(output_dir, html_name)
    count = convert_file(md_path, html_path)
    size_kb = os.path.getsize(html_path) // 1024
    print(f"  {html_name}: {count} msgs, {size_kb} KB")

print(f"\nDone! Output: {output_dir}")
