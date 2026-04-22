"""
TTS Service handles Text-to-Speech synthesis using Google TTS (gTTS).
It converts agent text responses into audio bytes for playback.
"""
import logging
import asyncio
from io import BytesIO
from gtts import gTTS

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self, lang="en"):
        self.lang = lang
        self.last_latency = 0

    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to MP3 audio using Google TTS.
        Returns complete MP3 bytes.
        """
        if not text or not text.strip():
            return b""

        import time
        start_time = time.time()
        try:
            audio = await asyncio.to_thread(self._generate_audio, text)
            self.last_latency = (time.time() - start_time) * 1000
            return audio

        except Exception as e:
            logger.error("TTS error: %s", e)
            return b""

    def _generate_audio(self, text: str) -> bytes:
        fp = BytesIO()

        tts = gTTS(
            text=text,
            lang=self.lang,
            slow=False
        )

        tts.write_to_fp(fp)

        return fp.getvalue()