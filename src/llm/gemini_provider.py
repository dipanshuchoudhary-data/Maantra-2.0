import os
from google import genai

from src.llm.base_provider import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):

    def __init__(self, model_name: str | None = None):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY missing")

        self.client = genai.Client(api_key=api_key)

        self.model = model_name or os.getenv("MODEL_NAME", "gemini-1.5-pro")

    async def chat(self, messages, tools=None):

        prompt = "\n".join([m["content"] for m in messages if m.get("content")])

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return {
            "message": {
                "role": "assistant",
                "content": response.text,
            },
            "tool_calls": [],
        }