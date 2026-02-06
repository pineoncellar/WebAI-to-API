# src/models/gemini.py
from typing import Optional, List, Union, Dict, Any
from pathlib import Path
import json
import re
import random
import base64
import time
import httpx
from gemini_webapi import GeminiClient as WebGeminiClient
from app.config import is_debug_mode
from app.logger import logger

class MyGeminiClient:
    """
    Wrapper for the Gemini Web API client.
    """
    def __init__(self, secure_1psid: str, secure_1psidts: str, proxy: str | None = None) -> None:
        self.proxy = proxy
        self.client = WebGeminiClient(secure_1psid, secure_1psidts, proxy)
        self._debug = is_debug_mode()

    async def init(self) -> None:
        """Initialize the Gemini client."""
        await self.client.init(timeout=10)

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

    async def generate_image(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Generate an image using Gemini's internal tool (Nano Banana).
        Mimics the StreamGenerate2 request.
        Downloads the image and returns dict with url, base64, and local_path.
        """
        if self._debug:
            logger.debug("Gemini generate_image prompt=%s", prompt)

        # Ensure initialized
        if not self.client.access_token:
            if self._debug:
                logger.debug("Gemini client not initialized, calling init()")
            await self.client.init()
        
        # Prepare params
        self.client._reqid += 100000
        req_id = self.client._reqid
        
        params = {
            "bl": self.client.build_label,
            "f.sid": self.client.session_id,
            "_reqid": str(req_id),
            "rt": "c",
            "hl": "en"
        }
        
        # Construct payload
        message_content = [
            prompt,
            0,
            None,
            None,
            None,
            None,
            0,
        ]
        
        inner_req_list = [None] * 69
        inner_req_list[0] = message_content
        inner_req_list[1] = ["en"] 
        inner_req_list[2] = ["", "", "", None, None, None, None, None, None, ""]
        inner_req_list[7] = 1 
        
        request_data = {
            "at": self.client.access_token,
            "f.req": json.dumps([None, json.dumps(inner_req_list)])
        }
        
        # FIX: Try using StreamGenerate instead of StreamGenerate2 based on logs/capture
        url = "https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"
        
        try:
            # Re-use the underlying httpx client
            response = await self.client.client.post(
                url,
                params=params,
                data=request_data,
                headers=self.client.client.headers
            )
            
            if response.status_code != 200:
                logger.error(f"Generate image failed. Status: {response.status_code}")
                return None
                
            text = response.text
            # Simple regex search for the full resolution image URL
            urls = re.findall(r"https://lh3\.googleusercontent\.com/gg-dl/[A-Za-z0-9_-]+", text)
            
            if urls:
                image_url = urls[0]
                if self._debug:
                    logger.debug(f"Found {len(urls)} image URLs. Downloading first: {image_url}")
                
                result = {"url": image_url}
                
                # Download and save
                try:
                    # Use a fresh client for the download to avoid conflicting headers from the API client
                    # We only reuse the proxy configuration and cookies
                    cookies = self.client.client.cookies
                    # Basic headers to look like a browser
                    headers = {
                        "User-Agent": self.client.client.headers.get("User-Agent", "Mozilla/5.0"),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                    }

                    async with httpx.AsyncClient(proxy=self.proxy, follow_redirects=True, cookies=cookies) as dl_client:
                        if self._debug:
                            logger.debug(f"Downloading image from {image_url}")
                        img_resp = await dl_client.get(image_url, headers=headers)
                    
                    if img_resp.status_code == 200:
                        img_data = img_resp.content
                        
                        # Ensure assets/generated_images exists
                        save_dir = Path("assets/generated_images")
                        save_dir.mkdir(parents=True, exist_ok=True)
                        
                        timestamp = int(time.time() * 1000)
                        filename = f"gen_{timestamp}_{random.randint(100, 999)}.png"
                        file_path = save_dir / filename
                        
                        with open(file_path, "wb") as f:
                            f.write(img_data)
                            
                        b64_str = base64.b64encode(img_data).decode("utf-8")
                        
                        result["base64"] = b64_str
                        result["local_path"] = str(file_path)
                        if self._debug:
                            logger.debug(f"Image saved to {file_path}")
                    else:
                        logger.warning(f"Failed to download image from {image_url}. Status: {img_resp.status_code}")
                except Exception as down_err:
                    logger.error(f"Failed to download/save image: {down_err}")
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error in generate_image: {e}")
            return None

    def start_chat(self, model: str):
        """
        Start a chat session with the given model.
        """
        if self._debug:
            logger.debug("Gemini start_chat initiated for model=%s", model)
        return self.client.start_chat(model=model)
