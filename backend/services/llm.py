"""
LLM Service handles communication with the Large Language Model (Groq/OpenAI).
It is responsible for generating responses and handling tool call suggestions.
"""
import os
import logging
from openai import AsyncOpenAI
from types import SimpleNamespace

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)


class LLMService:
    def __init__(self, model="llama-3.1-8b-instant"):
        self.model = model
        self.last_latency = 0

    async def generate_response(self, messages: list, tools: list = None):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
        }

        # Add tools only if present
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        import time
        start_time = time.time()
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**payload)
                self.last_latency = (time.time() - start_time) * 1000
                return response.choices[0].message
            except Exception as e:
                logger.error(f"LLM Error on attempt {attempt + 1}: {e}")
                if attempt == 2:
                    return SimpleNamespace(
                        content="I am sorry, my AI brain is currently disconnected.",
                        tool_calls=None
                    )

    async def generate_streaming_response(self, messages: list):
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )

            async for chunk in stream:
                if (
                    chunk.choices
                    and chunk.choices[0].delta
                    and chunk.choices[0].delta.content
                ):
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("Streaming Error: %s", e)
            yield "Sorry, AI response failed."