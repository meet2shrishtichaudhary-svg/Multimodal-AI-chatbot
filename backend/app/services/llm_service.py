import logging
import base64
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate completion for the given conversation messages and optional image payloads.
        images format: list of dicts with {"mime_type": str, "data": bytes}
        """
        pass

    @abstractmethod
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Yield streaming text deltas for the given messages and system prompt.
        """
        pass

class OpenAILLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        formatted_messages = [{"role": "system", "content": system_prompt}]

        for idx, msg in enumerate(messages):
            # If it's the last message from user and there are images, format as multimodal content
            if idx == len(messages) - 1 and msg["role"] == "user" and images:
                content_parts = [{"type": "text", "text": msg["content"]}]
                for img in images:
                    b64_data = base64.b64encode(img["data"]).decode("utf-8")
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img['mime_type']};base64,{b64_data}"
                        }
                    })
                formatted_messages.append({"role": "user", "content": content_parts})
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=1500
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI service error: {str(e)}")

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ):
        formatted_messages = [{"role": "system", "content": system_prompt}]

        for idx, msg in enumerate(messages):
            if idx == len(messages) - 1 and msg["role"] == "user" and images:
                content_parts = [{"type": "text", "text": msg["content"]}]
                for img in images:
                    b64_data = base64.b64encode(img["data"]).decode("utf-8")
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img['mime_type']};base64,{b64_data}"
                        }
                    })
                formatted_messages.append({"role": "user", "content": content_parts})
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=2048,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise RuntimeError(f"OpenAI streaming error: {str(e)}")

class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        # Build prompt sequence with system instruction
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(f"System Instructions:\n{system_prompt}\n")

        for msg in messages[:-1]:
            prompt_parts.append(f"{msg['role'].capitalize()}: {msg['content']}")

        last_msg = messages[-1] if messages else {"content": ""}
        prompt_parts.append(f"User: {last_msg['content']}")

        contents = ["\n\n".join(prompt_parts)]

        # If images attached, add image parts
        if images:
            from google.genai import types
            for img in images:
                contents.append(
                    types.Part.from_bytes(
                        data=img["data"],
                        mime_type=img["mime_type"]
                    )
                )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise RuntimeError(f"Gemini service error: {str(e)}")

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ):
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(f"System Instructions:\n{system_prompt}\n")

        for msg in messages[:-1]:
            prompt_parts.append(f"{msg['role'].capitalize()}: {msg['content']}")

        last_msg = messages[-1] if messages else {"content": ""}
        prompt_parts.append(f"User: {last_msg['content']}")

        contents = ["\n\n".join(prompt_parts)]

        if images:
            from google.genai import types
            for img in images:
                contents.append(
                    types.Part.from_bytes(
                        data=img["data"],
                        mime_type=img["mime_type"]
                    )
                )

        try:
            response_stream = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents
            )
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise RuntimeError(f"Gemini streaming error: {str(e)}")

class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic Mock LLM for automated testing and zero-cost local development.
    """
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        last_user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_msg = m["content"]
                break

        if images:
            return (
                f"[Mock Vision Response] I have analyzed the attached image(s). "
                f"Regarding your query '{last_user_msg}': The image visual contents have been processed successfully."
            )

        if "document" in system_prompt.lower() or "context" in system_prompt.lower():
            return (
                f"[Mock RAG Response] Based on the retrieved document context, "
                f"here is the information regarding '{last_user_msg}': All factual details match the indexed documentation."
            )

        if "search" in system_prompt.lower() or "sources" in system_prompt.lower():
            return (
                f"[Mock Web Search Response] Synthesizing recent web findings for '{last_user_msg}'. "
                f"According to verified search results, the latest updates are confirmed."
            )

        return (
            f"Hello! I am your Multimodal AI Assistant. I received your message: \"{last_user_msg}\". "
            "How can I help you explore documents, browse the web, or assist you today?"
        )

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        images: Optional[List[Dict[str, Any]]] = None
    ):
        import asyncio
        full_text = await self.generate_response(messages, system_prompt, images)
        words = full_text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.02)

def get_llm_provider() -> BaseLLMProvider:
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        model = settings.GEMINI_MODEL
        if model in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]:
            model = "gemini-3.5-flash-lite"
        return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model=model or "gemini-3.5-flash-lite")
    else:
        if provider != "mock":
            logger.warning(
                f"Configured provider '{provider}' API key is missing or not set. "
                "Using MockLLMProvider for offline/free testing."
            )
        return MockLLMProvider()
