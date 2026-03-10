import os
from openai import AsyncOpenAI

from src.llm.base_provider import BaseLLMProvider


class GrokProvider(BaseLLMProvider):

    def __init__(self):

        api_key = os.getenv("GROK_API_KEY")

        if not api_key:
            raise RuntimeError("GROK_API_KEY missing")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        self.model = os.getenv("MODEL_NAME", "grok-2")

    async def chat(self, messages, tools=None):

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
        )

        msg = response.choices[0].message

        return {
            "message": {
                "role": "assistant",
                "content": msg.content,
            },
            "tool_calls": [],
        }