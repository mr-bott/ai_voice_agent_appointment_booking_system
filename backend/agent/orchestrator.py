"""
VoiceOrchestrator manages the real-time interaction loop.
It coordinates STT (Speech-to-Text), LLM reasoning, Tool execution, and TTS (Text-to-Speech).
"""
import asyncio
import logging
from datetime import datetime

from ..services.llm import LLMService
from ..services.stt import STTService
from ..services.tts import TTSService
from .prompts import SYSTEM_PROMPT
from .tool_router import ToolRouter
from .tools import TOOLS
from ..api.metrics import metrics_store

logger = logging.getLogger(__name__)


class VoiceOrchestrator:
    def __init__(self, websocket, session_memory, db_session):
        self.websocket = websocket
        self.session_memory = session_memory
        self.db = db_session

        self.stt = STTService(callback=self.on_transcript)
        self.tts = TTSService()
        self.llm = LLMService()
        self.tool_router = ToolRouter(self.db)

        self.is_speaking = False
        self.barge_in_flag = False
        self.agent_lock = asyncio.Lock()
        self.last_user_input: tuple[str, float] | None = None

    async def start(self):
        stt_ready = await self.stt.connect()
        messages = await self.session_memory.get_recent_messages()
        if not messages:
            await self.session_memory.add_message("system", SYSTEM_PROMPT)

        await self.websocket.send_json(
            {
                "type": "session_status",
                "stt_ready": stt_ready,
                "message": "Voice session ready." if stt_ready else "Browser STT fallback enabled.",
            }
        )

    async def process_audio(self, audio_data: bytes):
        await self.stt.process_audio(audio_data)


    async def process_text(self, text: str):
        await self.on_transcript(text, True, source="browser")

    async def on_transcript(self, text: str, is_final: bool, source: str = "stt"):
        cleaned_text = text.strip()
        if not cleaned_text:
            return

        # Barge-in: If user speaks while AI is "speaking", interrupt the AI
        if self.is_speaking:
            self.barge_in_flag = True
            await self.websocket.send_json({"type": "interrupt_tts"})
            logger.info("Barge-in detected: interrupting AI response.")


        await self.websocket.send_json(
            {
                "type": "transcript",
                "role": "user",
                "text": cleaned_text,
                "final": is_final,
                "source": source,
            }
        )

        if not is_final:
            return
            
        metrics_store.update_stt(120) # Estimated Deepgram latency

        now = datetime.utcnow().timestamp()
        if self.last_user_input:
            previous_text, previous_time = self.last_user_input
            if previous_text.lower() == cleaned_text.lower() and now - previous_time < 2:
                return
        self.last_user_input = (cleaned_text, now)

        await self.session_memory.add_message("user", cleaned_text)
        asyncio.create_task(self.run_agent_loop())

    async def run_agent_loop(self):
        async with self.agent_lock:
            self.barge_in_flag = False
            
            # Allow up to 3 consecutive tool calls
            for _ in range(3):
                messages = await self.session_memory.get_recent_messages(limit=25)
                
                # CRITICAL: Always ensure the system prompt is present to prevent hallucination
                if not any(m.get("role") == "system" for m in messages):
                    messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

                response = await self.llm.generate_response(messages, tools=TOOLS)

                metrics_store.update_llm(self.llm.last_latency)
                
                tool_calls = getattr(response, "tool_calls", None) or []
                
                if not tool_calls:
                    # No more tools to call, we have the final response
                    content = getattr(response, "content", None) or ""
                    
                    # Safety check: Remove hallucinated tool syntax or leaked XML/JSON from spoken response
                    import re
                    # Remove tags like <function=...>...</function> or [function=...]
                    clean_content = re.sub(r'<.*?>', '', content)
                    clean_content = re.sub(r'\[.*?\]', '', clean_content).strip()

                    
                    if not clean_content and content:
                         logger.warning("LLM only returned tool syntax in content: %s", content)
                         # If it's just a tool call leaked into content, we should try to ignore and continue
                         # but for now we just say we are processing.
                         return 

                    await self.speak(clean_content or "I am sorry, I could not process that request.")

                    return

                # Record the assistant's tool call intent
                await self.session_memory.add_message(
                    "assistant",
                    getattr(response, "content", "") or "",
                    tool_calls=[
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in tool_calls
                    ],
                )

                # Execute all tools requested in this turn
                for tool_call in tool_calls:
                    await self.websocket.send_json({"type": "tool_call", "name": tool_call.function.name})
                    result = await self.tool_router.execute_tool(tool_call)
                    
                    # Notify frontend of successful booking
                    if tool_call.function.name == "book_appointment" and "successfully" in result.lower():
                        await self.websocket.send_json({
                            "type": "booking_success",
                            "message": result
                        })

                    await self.session_memory.add_message(
                        "tool",
                        result,
                        tool_call_id=tool_call.id,
                        name=tool_call.function.name,
                    )
            
            # If we exit the loop, the agent tried to use tools too many times
            await self.speak("I am sorry, but I need to stop processing this request as it is taking too long.")

    async def speak(self, text: str):
        if self.barge_in_flag or not text:
            return

        await self.session_memory.add_message("assistant", text)
        await self.websocket.send_json(
            {
                "type": "transcript",
                "role": "assistant",
                "text": text,
                "final": True,
            }
        )

        self.is_speaking = True
        try:
            audio_bytes = await self.tts.synthesize(text)
            metrics_store.update_tts(self.tts.last_latency)
            if audio_bytes and not self.barge_in_flag:
                await self.websocket.send_bytes(audio_bytes)
        except Exception as exc:
            logger.error("TTS playback failed: %s", exc)
            await self.websocket.send_json(
                {
                    "type": "warning",
                    "message": "Text response ready, but audio playback generation failed.",
                }
            )
        finally:
            self.is_speaking = False

    async def stop(self):
        await self.stt.close()
