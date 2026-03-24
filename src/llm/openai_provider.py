import os
from openai import AsyncOpenAI

from src.llm.base_provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):

    def __init__(self, model_name: str | None = None):

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=api_key)

        self.model = model_name or os.getenv("MODEL_NAME", "gpt-4o")

    async def chat(self, messages, tools=None):

        # Build request kwargs - only include tools if provided
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        # Only add tools if provided (saves tokens)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)

        msg = response.choices[0].message

        tool_calls = []

        if msg.tool_calls:

            for call in msg.tool_calls:

                tool_calls.append(
                    {
                        "id": call.id,
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    }
                )

        return {
            "message": {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": tool_calls,
            },
            "tool_calls": tool_calls,
        }
