"""WebSocket TTS server — streams PCM chunks from local or cloud TTS to browser."""

import asyncio
import json
import threading
import time


class WsTTSServer:
    """Runs a WebSocket server that accepts text, streams PCM audio back."""

    def __init__(self, tts, port: int = 5556):
        self.tts = tts
        self.port = port
        self._loop = None

    @property
    def _is_cloud(self):
        from .cloud_tts import CloudTTS
        return isinstance(self.tts, CloudTTS)

    def start(self):
        """Start WebSocket server in a background thread."""
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        print(f"[WS-TTS] WebSocket server starting on ws://localhost:{self.port}")

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        import websockets
        async with websockets.serve(self._handle, "127.0.0.1", self.port):
            print(f"[WS-TTS] Listening on ws://localhost:{self.port}")
            # Pre-establish cloud TTS connection
            if self._is_cloud:
                await self.tts.warmup()
            await asyncio.Future()  # run forever

    async def _handle(self, ws):
        try:
            t_ws_open = time.time()
            msg = await ws.recv()
            data = json.loads(msg)
            text = data.get("text", "")
            scene_t = data.get("scene_t")
            if scene_t:
                print(f"[Timing] scene_ready→ws_open: {(t_ws_open - scene_t)*1000:.0f} ms")
            if not text or not self.tts or not self.tts.model:
                await ws.close()
                return

            print(f"[WS-TTS] Generating: {text[:40]}...")

            if self._is_cloud:
                await self._handle_cloud(ws, text)
            else:
                await self._handle_local(ws, text)

        except Exception as e:
            print(f"[WS-TTS] Error: {e}")

    async def _handle_cloud(self, ws, text: str):
        """Stream audio from cloud TTS (async native)."""
        t0 = time.perf_counter()
        first = True
        async for pcm in self.tts.stream_async(text):
            if first:
                first = False
                print(f"[WS-TTS] First chunk: {time.perf_counter()-t0:.2f}s")
            await ws.send(pcm)
        await ws.send(b"")
        print(f"[WS-TTS] Done: {time.perf_counter()-t0:.2f}s")

    async def _handle_local(self, ws, text: str):
        """Stream audio from local TTS model (sync generator, runs in executor)."""
        t0 = time.perf_counter()
        first = True

        for chunk, sr, timing in self.tts.model.generate_custom_voice_streaming(
            text=text, language="Chinese", speaker=self.tts.voice, chunk_size=8,
        ):
            import numpy as np
            pcm = (chunk * 32767).astype(np.int16).tobytes() if chunk.dtype != np.int16 else chunk.tobytes()
            if first:
                # Fade in first chunk
                import array
                samples = array.array('h')
                samples.frombytes(pcm)
                fade = min(256, len(samples))
                for i in range(fade):
                    samples[i] = int(samples[i] * (i / fade))
                pcm = samples.tobytes()
                first = False
                print(f"[WS-TTS] First chunk: {time.perf_counter()-t0:.2f}s")

            await ws.send(pcm)

        # Send empty message to signal end
        await ws.send(b"")
        print(f"[WS-TTS] Done: {time.perf_counter()-t0:.2f}s")
