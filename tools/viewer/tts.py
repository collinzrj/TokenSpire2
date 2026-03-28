"""Text-to-speech via local faster-qwen3-tts with streaming support."""

import time
import struct
import numpy as np


class LocalTTS:
    """Local TTS using faster-qwen3-tts on GPU. Streams audio chunks."""

    def __init__(self, model_name: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice", voice: str = "vivian"):
        self.voice = voice
        self.model = None
        self.model_name = model_name
        self.sr = 24000

    def load(self):
        """Load model (call once at startup)."""
        print(f"[TTS] Loading {self.model_name}...")
        t0 = time.perf_counter()
        from faster_qwen3_tts import FasterQwen3TTS
        self.model = FasterQwen3TTS.from_pretrained(self.model_name)
        print(f"[TTS] Model loaded in {time.perf_counter()-t0:.1f}s, voice={self.voice}")

        # Warm up with a short text to capture CUDA graphs
        print("[TTS] Warming up...")
        t0 = time.perf_counter()
        self.model.generate_custom_voice(text="你好", language="Chinese", speaker=self.voice)
        print(f"[TTS] Warm up done in {time.perf_counter()-t0:.1f}s")

    def synthesize(self, text: str) -> bytes | None:
        """Generate complete WAV audio from text."""
        if not self.model:
            return None
        t0 = time.perf_counter()
        try:
            chunks = []
            for chunk, sr, timing in self.model.generate_custom_voice_streaming(
                text=text, language="Chinese", speaker=self.voice, chunk_size=8,
            ):
                chunks.append(chunk)
            if not chunks:
                return None
            audio = np.concatenate(chunks)
            pcm = (audio * 32767).astype(np.int16).tobytes() if audio.dtype != np.int16 else audio.tobytes()
            pcm = self._fade_in_out(pcm)
            wav = self._pcm_to_wav(pcm, sample_rate=sr)
            print(f"[TTS] {time.perf_counter()-t0:.2f}s, {len(wav)} bytes: {text[:40]}...")
            return wav
        except Exception as e:
            print(f"[TTS] Error after {time.perf_counter()-t0:.2f}s: {e}")
            import traceback; traceback.print_exc()
            return None

    def synthesize_stream(self, text: str):
        """Generator yielding PCM Int16 bytes chunks as they are generated."""
        if not self.model:
            return
        t0 = time.perf_counter()
        first = True
        try:
            for chunk, sr, timing in self.model.generate_custom_voice_streaming(
                text=text, language="Chinese", speaker=self.voice, chunk_size=8,
            ):
                pcm = (chunk * 32767).astype(np.int16).tobytes() if chunk.dtype != np.int16 else chunk.tobytes()
                if first:
                    pcm = self._fade_in_start(pcm)
                    first = False
                    print(f"[TTS] first chunk {time.perf_counter()-t0:.2f}s: {text[:40]}...")
                yield pcm
        except Exception as e:
            print(f"[TTS] Stream error: {e}")
        print(f"[TTS] total {time.perf_counter()-t0:.2f}s: {text[:40]}...")

    @staticmethod
    def _fade_in_start(pcm: bytes, fade_samples: int = 256) -> bytes:
        """Fade in only the start of a chunk."""
        import array
        samples = array.array('h')
        samples.frombytes(pcm)
        n = len(samples)
        for i in range(min(fade_samples, n)):
            samples[i] = int(samples[i] * (i / fade_samples))
        return samples.tobytes()

    @staticmethod
    def _fade_in_out(pcm: bytes, fade_samples: int = 512) -> bytes:
        import array
        samples = array.array('h')
        samples.frombytes(pcm)
        n = len(samples)
        for i in range(min(fade_samples, n)):
            samples[i] = int(samples[i] * (i / fade_samples))
        for i in range(min(fade_samples, n)):
            samples[n - 1 - i] = int(samples[n - 1 - i] * (i / fade_samples))
        return samples.tobytes()

    @staticmethod
    def _pcm_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
        data_size = len(pcm)
        header = struct.pack('<4sI4s4sIHHIIHH4sI',
            b'RIFF', 36 + data_size, b'WAVE',
            b'fmt ', 16, 1, channels,
            sample_rate, sample_rate * channels * sample_width,
            channels * sample_width, sample_width * 8,
            b'data', data_size)
        return header + pcm
