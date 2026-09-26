#!/usr/bin/env python3
"""Create clean version of the 27 real conversations from nhatky_conversations_real."""

import os
import re
import glob
import shutil
from datetime import datetime

SRC_DIR = "/media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/assistant/.tmp/nhatky_conversations_real"
OUT_DIR = "/media/diep/hdd555/backup_openclaw_20260920/.openclaw/agents/assistant/.tmp/nhatky_conversations_clean"

ARTIFACT_PATTERNS = [
    r'^Conversation info \(untrusted metadata\).*$',
    r'^\[cron:.*$',
    r'^\[OpenClaw.*$',
    r'^\[Startup.*$',
    r'^\[Subagent.*$',
    r'^\[Inter-session.*$',
    r'^<<<BEGIN.*$',
    r'^A new session was started.*$',
    r'^Continue the OpenClaw.*$',
    r'^Sender \(untrusted metadata\).*$',
    r'^\[STATUS\] KHÔNG CẦN BÁO.*$',
    r'^HEARTBEAT_OK.*$',
    r'heartbeat poll',
    r'\[\[reply_to_current\]\]',
    r'<\|thought\|>.*?<\|/thought\|>',
    r'<\|channel\|>.*?<\|/channel\|>',
    r'<function=.*?>.*?'
]

def clean_text(text):
    """Remove artifact patterns from text."""
    for pattern in ARTIFACT_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
    # Remove empty lines at start/end
    text = text.strip()
    return text

def process_file(src_path, out_path, idx):
    """Process a single conversation file."""
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into header and messages
    parts = content.split('---\n\n', 1)
    header = parts[0] if len(parts) > 0 else ''
    messages = parts[1] if len(parts) > 1 else ''
    
    # Clean messages
    cleaned_messages = clean_text(messages)
    
    # Write output
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(header + '\n---\n\n' + cleaned_messages + '\n')

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    files = sorted(glob.glob(os.path.join(SRC_DIR, '*.md')))
    files = [f for f in files if not f.endswith('_index.md')]
    
    print(f"Processing {len(files)} conversations...")
    
    index_lines = [
        "# Assistant Conversations (Clean Version)",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Source: {SRC_DIR}",
        f"Total conversations: {len(files)}",
        ""
    ]
    
    for i, src_path in enumerate(files, 1):
        fname = os.path.basename(src_path)
        out_path = os.path.join(OUT_DIR, fname)
        process_file(src_path, out_path, i)
        
        # Extract stats from header for index
        with open(src_path, 'r', encoding='utf-8') as f:
            header = f.read().split('---\n\n')[0]
        
        # Extract message count
        msg_count = 0
        for line in header.split('\n'):
            if 'Số tin nhắn:' in line:
                msg_count = line.split(':')[-1].strip()
                break
        
        date_match = re.search(r'(\d{8})_', fname)
        date_str = date_match.group(1) if date_match else ''
        index_lines.append(f"- [{fname}]({fname}) — {msg_count} msgs ({date_str})")
    
    with open(os.path.join(OUT_DIR, '_index.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(index_lines))
    
    print(f"Done! Output: {OUT_DIR}")

if __name__ == '__main__':
    main()