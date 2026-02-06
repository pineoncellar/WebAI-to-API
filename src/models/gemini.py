# src/models/gemini.py
from typing import Optional, List, Union
from pathlib import Path
from gemini_webapi import GeminiClient as WebGeminiClient
from app.config import is_debug_mode
from app.logger import logger

class MyGeminiClient:
    """
    Wrapper for the Gemini Web API client.
    """
    def __init__(self, secure_1psid: str, secure_1psidts: str, proxy: str | None = None) -> None:
        self.client = WebGeminiClient(secure_1psid, secure_1psidts, proxy)
        self._debug = is_debug_mode()

    async def init(self) -> None:
        """Initialize the Gemini client."""
        await self.client.init()
    async def generate_content(self, message: str, model: str, files: Optional[List[Union[str, Path]]] = None):
        """
        Generate content using the Gemini client.
        """
        if self._debug:
            logger.debug("Gemini generate_content payload | model=%s | prompt=%s | files=%s", model, message, files)
        response = await self.client.generate_content(prompt=message, model=model, files=files)
        if self._debug:
            logger.debug("Gemini generate_content response text: %s", getattr(response, "text", response))
        return response

    async def generate_content_stream(self, message: str, model: str, files: Optional[List[Union[str, Path]]] = None):
        """
        Generate content using the Gemini client with streaming.
        """
        if self._debug:
            logger.debug("Gemini generate_content_stream payload | model=%s | prompt=%s | files=%s", model, message, files)
        async for chunk in self.client.generate_content_stream(prompt=message, model=model, files=files):
            yield chunk

    async def close(self) -> None:
        """Close the Gemini client."""
        await self.client.close()

    def start_chat(self, model: str):
        """
        Start a chat session with the given model.
        """
        if self._debug:
            logger.debug("Gemini start_chat initiated for model=%s", model)
        return self.client.start_chat(model=model)
