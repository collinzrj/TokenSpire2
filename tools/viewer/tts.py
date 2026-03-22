"""Text-to-speech via Aliyun Qwen TTS REST streaming API."""

import base64
import dashscope


class AliyunTTS:
    def __init__(self, api_key: str, model: str = "qwen3-tts-flash", voice: str = "Cherry"):
        self.api_key = api_key
        self.model = model
        self.voice = voice

    def synthesize(self, text: str) -> bytes | None:
        """Collect all streaming chunks into one WAV. Returns complete audio bytes."""
        try:
            chunks = []
            resp = dashscope.MultiModalConversation.call(
                model=self.model,
                api_key=self.api_key,
                text=text,
                voice=self.voice,
                language_type="Chinese",
                stream=True
            )
            for chunk in resp:
                if chunk.output is not None:
                    audio = chunk.output.audio
                    if audio.data is not None:
                        chunks.append(base64.b64decode(audio.data))
                    if chunk.output.finish_reason == "stop":
                        break
            if not chunks:
                return None
            pcm = b"".join(chunks)
            pcm = self._fade_in_out(pcm)
            return self._pcm_to_wav(pcm)
        except Exception as e:
            print(f"[TTS] Error: {e}")
            return None

    @staticmethod
    def _fade_in_out(pcm: bytes, fade_samples: int = 512) -> bytes:
        """Apply fade-in/out to avoid click/pop at start and end."""
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
        import struct
        data_size = len(pcm)
        header = struct.pack('<4sI4s4sIHHIIHH4sI',
            b'RIFF', 36 + data_size, b'WAVE',
            b'fmt ', 16, 1, channels,
            sample_rate, sample_rate * channels * sample_width,
            channels * sample_width, sample_width * 8,
            b'data', data_size)
        return header + pcm
