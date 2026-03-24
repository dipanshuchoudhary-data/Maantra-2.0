import os
from openai import AsyncOpenAI

from src.llm.base_provider import BaseLLMProvider


class GrokProvider(BaseLLMProvider):

    def __init__(self, model_name: str | None = None):

        api_key = os.getenv("GROK_API_KEY")

        if not api_key:
            raise RuntimeError("GROK_API_KEY missing")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        self.model = model_name or os.getenv("MODEL_NAME", "grok-2")

    async def chat(self, messages, tools=None):

        # Build request kwargs - only include tools if provided
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        # Only add tools if provided (saves tokens)
        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)

        msg = response.choices[0].message

        return {
            "message": {
                "role": "assistant",
                "content": msg.content,
            },
            "tool_calls": [],
        }