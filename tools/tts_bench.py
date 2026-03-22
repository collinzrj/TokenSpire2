#!/usr/bin/env python3
"""Benchmark TTS: REST non-stream, REST stream, WebSocket realtime."""

import asyncio
import base64
import json
import time
import dashscope

API_KEY = "sk-xxx"
TEXT = "哈哈，这个怪物太强了，我们还是先防御吧，保命要紧啊兄弟们！"


def bench_rest_no_stream():
    t0 = time.perf_counter()
    resp = dashscope.MultiModalConversation.call(
        model="qwen3-tts-flash",
        api_key=API_KEY,
        text=TEXT,
        voice="Cherry",
        language_type="Chinese",
        stream=False
    )
    t1 = time.perf_counter()
    url = resp.get("output", {}).get("audio", {}).get("url", "")
    print(f"[REST no-stream]  total={t1-t0:.3f}s url={bool(url)}")


def bench_rest_stream():
    t0 = time.perf_counter()
    first = None
    total_bytes = 0
    chunks = 0
    resp = dashscope.MultiModalConversation.call(
        model="qwen3-tts-flash",
        api_key=API_KEY,
        text=TEXT,
        voice="Cherry",
        language_type="Chinese",
        stream=True
    )
    for chunk in resp:
        if chunk.output is not None:
            audio = chunk.output.audio
            if audio.data is not None:
                wav_bytes = base64.b64decode(audio.data)
                total_bytes += len(wav_bytes)
                chunks += 1
                if first is None:
                    first = time.perf_counter()
            if chunk.output.finish_reason == "stop":
                break
    t1 = time.perf_counter()
    first_t = f"{first-t0:.3f}s" if first else "N/A"
    print(f"[REST stream]     first={first_t} total={t1-t0:.3f}s chunks={chunks} bytes={total_bytes}")


async def bench_ws():
    import websockets
    t0 = time.perf_counter()
    uri = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-tts-flash-realtime"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    total = 0
    first = None
    async with websockets.connect(uri, additional_headers=headers) as ws:
        await ws.send(json.dumps({"type": "session.update", "session": {"mode": "server_commit", "voice": "Cherry", "response_format": "pcm", "sample_rate": 24000}}))
        await ws.send(json.dumps({"type": "input_text_buffer.append", "text": TEXT}))
        await ws.send(json.dumps({"type": "input_text_buffer.commit"}))
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                d = json.loads(msg)
                if d.get("type") == "response.audio.delta":
                    total += len(base64.b64decode(d.get("delta", "")))
                    if first is None: first = time.perf_counter()
                elif d.get("type") in ("response.audio.done", "response.done"): break
            except: break
    t1 = time.perf_counter()
    print(f"[WS  realtime]    first={first-t0:.3f}s total={t1-t0:.3f}s bytes={total}")


if __name__ == "__main__":
    print(f"Text: {TEXT} ({len(TEXT)} chars)\n")
    bench_rest_no_stream()
    bench_rest_stream()
    asyncio.run(bench_ws())
