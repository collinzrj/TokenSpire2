#!/usr/bin/env python3
"""
TokenSpire2 Live Conversation Viewer

Usage:
    python viewer.py                          # auto-find latest JSON in default mod folder
    python viewer.py path/to/llm_history.json # watch a specific file
    python viewer.py --port 8080              # custom port
    python viewer.py --no-summary             # disable thinking summarization
"""

import argparse
import threading
from http.server import HTTPServer

from viewer.config import find_json_file, load_llm_config
from viewer.state import EnrichedState
from viewer.summarizer import LLMSummarizer
from viewer.tts import AliyunTTS
from viewer.server import ViewerHandler, background_loop


def main():
    parser = argparse.ArgumentParser(description="TokenSpire2 Live Conversation Viewer")
    parser.add_argument("path", nargs="?", help="Path to llm_history JSON file or mod folder")
    parser.add_argument("--port", type=int, default=5555, help="HTTP port (default: 5555)")
    parser.add_argument("--no-summary", action="store_true", help="Disable thinking summarization")
    args = parser.parse_args()

    json_path, watch_dir = find_json_file(args.path)
    if json_path:
        print(f"Watching: {json_path}")
    elif watch_dir:
        print(f"Watching folder: {watch_dir} (waiting for game to start...)")

    config = load_llm_config(watch_dir)
    summarizer = None
    if not args.no_summary:
        if config and config.get("key") and config.get("url"):
            summary_model = config.get("summary_model") or config.get("model", "gpt-4o")
            summarizer = LLMSummarizer(config["url"], config["key"], summary_model)
            print(f"Thinking summarizer enabled (model: {summary_model})")
        else:
            print("No llm_config.json found — thinking summarizer disabled")

    tts = None
    if config and config.get("key"):
        tts_model = config.get("tts_model", "qwen3-tts-flash")
        tts_voice = config.get("tts_voice", "Cherry")
        tts = AliyunTTS(config["key"], model=tts_model, voice=tts_voice)
        print(f"TTS enabled (model: {tts_model}, voice: {tts_voice})")

    state = EnrichedState(summarizer)
    ViewerHandler.json_path = json_path
    ViewerHandler.watch_dir = watch_dir
    ViewerHandler.state = state
    ViewerHandler.tts = tts

    t = threading.Thread(target=background_loop, args=(state, ViewerHandler), daemon=True)
    t.start()

    print(f"Open http://localhost:{args.port} in your browser\n")
    server = HTTPServer(("127.0.0.1", args.port), ViewerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
