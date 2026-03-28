"""Cloud TTS via Dashscope qwen3-tts-flash-realtime WebSocket API.

Opens a fresh WSS connection per call. Retries up to 3 times with a 4s
timeout on first audio chunk. Skips audio if all retries fail.

Streams PCM s16le mono 24kHz chunks to the caller.
"""

import asyncio
import base64
import json
import time

MAX_RETRIES = 3
FIRST_CHUNK_TIMEOUT = 4.0  # seconds to wait for first audio chunk


class CloudTTS:
    """Dashscope real-time TTS with timeout and retry."""

    WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-tts-instruct-flash-realtime"

    def __init__(self, api_key: str, voice: str = "Cherry"):
        self.api_key = api_key
        self.voice = voice
        self.sr = 24000
        self.model = True  # WsTTSServer checks this
        self._lock = asyncio.Lock()

    def load(self):
        print(f"[CloudTTS] Ready (voice={self.voice})")

    async def _connect(self):
        """Open a new WSS connection and configure the session."""
        import websockets

        t0 = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        ws = await asyncio.wait_for(
            websockets.connect(self.WS_URL, additional_headers=headers),
            timeout=FIRST_CHUNK_TIMEOUT,
        )

        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=FIRST_CHUNK_TIMEOUT))
        if msg["type"] != "session.created":
            print(f"[CloudTTS] Unexpected on connect: {msg}")
            await ws.close()
            return None

        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "mode": "server_commit",
                "voice": self.voice,
                "language_type": "Auto",
                "response_format": "pcm",
                "sample_rate": self.sr,
            },
        }))
        print(f"[CloudTTS] Connected in {(time.perf_counter()-t0)*1000:.0f} ms")
        return ws

    async def warmup(self):
        pass

    async def _try_stream(self, text: str):
        """Single attempt: connect, send text, yield audio with timeout on first chunk."""
        ws = None
        t0 = time.perf_counter()
        first = True
        try:
            ws = await self._connect()
            if ws is None:
                return

            await ws.send(json.dumps({
                "type": "input_text_buffer.append",
                "text": text,
            }))
            await ws.send(json.dumps({
                "type": "session.finish",
            }))

            # Wait for first chunk with timeout
            while True:
                if first:
                    raw = await asyncio.wait_for(ws.recv(), timeout=FIRST_CHUNK_TIMEOUT)
                else:
                    raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                msg = json.loads(raw)
                mtype = msg["type"]
                if mtype == "response.audio.delta":
                    pcm = base64.b64decode(msg["delta"])
                    if first:
                        pcm = _fade_in(pcm)
                        first = False
                        print(f"[CloudTTS] First chunk: {time.perf_counter()-t0:.2f}s")
                    yield pcm
                elif mtype == "session.finished":
                    break
                elif mtype == "error":
                    print(f"[CloudTTS] Error: {msg}")
                    break

        finally:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

    async def stream_async(self, text: str):
        """Async generator with retry. Serialized via lock."""
        async with self._lock:
            t0 = time.perf_counter()
            for attempt in range(1, MAX_RETRIES + 1):
                got_audio = False
                try:
                    async for pcm in self._try_stream(text):
                        got_audio = True
                        yield pcm
                    if got_audio:
                        print(f"[CloudTTS] Done: {time.perf_counter()-t0:.2f}s")
                        return
                    else:
                        print(f"[CloudTTS] Attempt {attempt}/{MAX_RETRIES}: no audio received")
                except asyncio.TimeoutError:
                    print(f"[CloudTTS] Attempt {attempt}/{MAX_RETRIES}: timeout after {time.perf_counter()-t0:.1f}s")
                except Exception as e:
                    print(f"[CloudTTS] Attempt {attempt}/{MAX_RETRIES}: {e}")

            print(f"[CloudTTS] All {MAX_RETRIES} attempts failed, skipping audio")


def _fade_in(pcm: bytes, fade_samples: int = 256) -> bytes:
    """Fade in the start of a PCM chunk to avoid click."""
    import array
    samples = array.array('h')
    samples.frombytes(pcm)
    n = len(samples)
    for i in range(min(fade_samples, n)):
        samples[i] = int(samples[i] * (i / fade_samples))
    return samples.tobytes()
