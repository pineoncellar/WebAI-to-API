# src/app/endpoints/gemini.py
from fastapi import APIRouter, HTTPException
from app.logger import logger
from schemas.request import GeminiRequest
from app.services.gemini_client import get_gemini_client
from app.services.session_manager import get_gemini_chat_manager
from app.config import is_debug_mode

from pathlib import Path
from typing import Union, List, Optional

router = APIRouter()
DEBUG_MODE = is_debug_mode()


def _serialize_payload(payload):
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    return payload

@router.post("/gemini")
async def gemini_generate(request: GeminiRequest):
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client is not initialized.")
    if DEBUG_MODE:
        logger.debug("/gemini request payload: %s", _serialize_payload(request))
    try:
        # Use the value attribute for the model (since GeminiRequest.model is an Enum)
        files: Optional[List[Union[str, Path]]] = [Path(f) for f in request.files] if request.files else None
        response = await gemini_client.generate_content(request.message, request.model.value, files=files)
        if DEBUG_MODE:
            logger.debug("/gemini response text: %s", getattr(response, "text", response))
        return {"response": response.text}
    except Exception as e:
        logger.error(f"Error in /gemini endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")

@router.post("/gemini-chat")
async def gemini_chat(request: GeminiRequest):
    gemini_client = get_gemini_client()
    session_manager = get_gemini_chat_manager()
    if not gemini_client or not session_manager:
        raise HTTPException(status_code=503, detail="Gemini client is not initialized.")
    if DEBUG_MODE:
        logger.debug("/gemini-chat request payload: %s", _serialize_payload(request))
    try:
        response = await session_manager.get_response(request.model, request.message, request.files)
        if DEBUG_MODE:
            logger.debug("/gemini-chat response text: %s", getattr(response, "text", response))
        return {"response": response.text}
    except Exception as e:
        logger.error(f"Error in /gemini-chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@router.post("/gemini-image")
async def gemini_image(request: GeminiRequest):
    """
    Experimental endpoint for image generation using Gemini's internal tool (Nano Banana).
    """
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client is not initialized.")
    if DEBUG_MODE:
        logger.debug("/gemini-image request payload: %s", _serialize_payload(request))
    
    try:
        # Check if the method works, it uses internal state of the client
        result = await gemini_client.generate_image(request.message)
        
        if result and result.get("url"):
            resp_data = {
                # "url": result["url"], 
                # "response": f"Image generated: {result['url']}",
                "local_path": result.get("local_path")
            }
            if result.get("base64"):
                resp_data["base64"] = result["base64"]
            return resp_data
        else:
            raise HTTPException(status_code=424, detail="Failed to generate image. Please checking logs or your account permissions.")

    except Exception as e:
        logger.error(f"Error in /gemini-image endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")

