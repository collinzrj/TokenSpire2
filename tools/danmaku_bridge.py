#!/usr/bin/env python3
"""
Danmaku bridge: opens Xiaohongshu live dashboard, scrapes comments,
writes them to instruction.txt.

Usage:
    python danmaku_bridge.py [url] [--mod-dir path] [--interval N]
"""

import sys
import time
import os
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="https://redlive.xiaohongshu.com/live_center_control")
    parser.add_argument("--mod-dir", default=r"D:\SteamLibrary\steamapps\common\Slay the Spire 2\mods\TokenSpire2")
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()

    instruction_path = os.path.join(args.mod_dir, "instruction.txt")
    print(f"Writing to: {instruction_path}")
    print(f"Opening: {args.url}")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(args.url, timeout=60000)
        print("Page loaded. Polling for comments...\n")

        seen = set()
        initialized = False

        while True:
            time.sleep(args.interval)
            try:
                comments = page.evaluate("""() => {
                    const items = document.querySelectorAll('.comment-list-item');
                    const results = [];
                    items.forEach(el => {
                        const spans = el.querySelectorAll('span');
                        let name = '', msg = '';
                        spans.forEach(s => {
                            const color = s.style.color;
                            if (color === 'rgba(0, 0, 0, 0.45)') name = s.textContent.trim();
                            if (color === 'rgba(0, 0, 0, 0.85)') msg = s.textContent.trim();
                        });
                        if (name && msg) results.push(name + msg);
                        else if (msg) results.push(msg);
                    });
                    return results;
                }""")

                if not initialized:
                    for c in comments:
                        seen.add(c)
                    initialized = True
                    print(f"[Init] {len(seen)} existing comments skipped")
                    continue

                new_comments = [c for c in comments if c not in seen]
                for c in new_comments:
                    seen.add(c)

                if new_comments:
                    print(f"[New] {len(new_comments)}:")
                    for c in new_comments:
                        print(f"  {c}")
                    with open(instruction_path, "a", encoding="utf-8") as f:
                        for c in new_comments:
                            f.write(f"[观众] {c}\n")

            except Exception as e:
                print(f"[Error] {e}")


if __name__ == "__main__":
    main()
