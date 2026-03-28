#!/usr/bin/env python3
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
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
from viewer.ws_tts import WsTTSServer
from viewer.server import ViewerHandler, background_loop


def main():
    parser = argparse.ArgumentParser(description="TokenSpire2 Live Conversation Viewer")
    parser.add_argument("path", nargs="?", help="Path to llm_history JSON file or mod folder")
    parser.add_argument("--port", type=int, default=5555, help="HTTP port (default: 5555)")
    parser.add_argument("--no-summary", action="store_true", help="Disable thinking summarization")
    parser.add_argument("--tts", choices=["local", "cloud", "none"], default="local",
                        help="TTS backend: local (GPU), cloud (Dashscope API), or none")
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
    tts_voice = (config or {}).get("tts_voice", "serena")
    if args.tts == "local":
        from viewer.tts import LocalTTS
        tts = LocalTTS(voice=tts_voice)
        tts.load()
    elif args.tts == "cloud":
        from viewer.cloud_tts import CloudTTS
        api_key = (config or {}).get("key", "")
        tts = CloudTTS(api_key=api_key, voice=tts_voice)
        tts.load()

    # Start WebSocket TTS server
    ws_tts = WsTTSServer(tts, port=5556)
    ws_tts.start()

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
