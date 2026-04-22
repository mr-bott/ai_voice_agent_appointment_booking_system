"""
STT Service handles Speech-to-Text conversion using Deepgram.
It processes live audio streams and returns transcribed text.
"""
import logging
import asyncio
import os

from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


class STTService:
    def __init__(self, callback):
        self.callback = callback
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY) if DEEPGRAM_API_KEY else None
        self.dg_connection = None
        self.is_available = False

    async def connect(self) -> bool:
        if not self.deepgram:
            logger.warning("Deepgram API key missing. STT unavailable; browser fallback may be used.")
            self.is_available = False
            return False

        try:
            self.dg_connection = self.deepgram.listen.asynclive.v("1")
            callback = self.callback

            def on_message(_self, result, **kwargs):
                try:
                    sentence = result.channel.alternatives[0].transcript
                    if sentence:
                        asyncio.create_task(
                            callback(sentence, result.is_final)
                        )
                        print("📝 TEXT:", sentence)
                except Exception as exc:
                    logger.error("Deepgram transcript callback error: %s", exc)

            async def on_error(_self, error, **kwargs):
                logger.error("Deepgram error: %s", error)

            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)

            options = LiveOptions(
                model="nova-2",
                language="en",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                endpointing=300,
            )

            await self.dg_connection.start(options)
            self.is_available = True
            logger.info("Deepgram STT connected successfully.")
            return True
        except Exception as exc:
            self.dg_connection = None
            self.is_available = False
            logger.error("Deepgram STT failed to connect: %s", exc)
            return False

    async def process_audio(self, audio_data: bytes):
        if not self.dg_connection or not self.is_available:
            return

        try:
            await self.dg_connection.send(audio_data)
        except Exception as exc:
            self.is_available = False
            logger.error("Deepgram audio send failed: %s", exc)

    async def close(self):
        if self.dg_connection:
            try:
                await self.dg_connection.finish()
            except Exception as exc:
                logger.warning("Deepgram close failed: %s", exc)
        self.dg_connection = None
        self.is_available = False
