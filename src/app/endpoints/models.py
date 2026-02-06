# src/app/endpoints/models.py
import time
import asyncio
from fastapi import APIRouter
from gemini_webapi.constants import Model as GeminiModel
from app.logger import logger
from app.services.gemini_client import get_gemini_client

router = APIRouter()

# Global cache for discovered models
_CACHED_MODELS = None
_CACHE_TIMESTAMP = 0
_CACHE_TTL = 3600  # Refresh every hour in case new models appear

async def _discover_gemini_models():
    """
    Dynamically lists available models by reading from the underlying library constants.
    """
    global _CACHED_MODELS, _CACHE_TIMESTAMP
    
    current_time = time.time()
    
    # Return cached if valid
    if _CACHED_MODELS is not None and (current_time - _CACHE_TIMESTAMP < _CACHE_TTL):
        return _CACHED_MODELS

    client = get_gemini_client()
    if not client:
        logger.warning("Gemini client not initialized, returning fallback models")
        return [
            "gemini-3.0-pro",
            "gemini-3.0-flash",
            "gemini-3.0-flash-thinking"
        ]

    try:
        # Check constants directly from the library instead of triggering an error
        valid_models = [
            m.model_name for m in GeminiModel 
            if m.model_name and m.model_name.lower() != "unspecified"
        ]

        if valid_models:
            logger.debug(f"Dynamically discovered models from library: {valid_models}")
            _CACHED_MODELS = valid_models
            _CACHE_TIMESTAMP = current_time
            return valid_models
            
    except Exception as e:
        logger.warning(f"Failed to extract models from library constants: {e}")

    # Fallback if discovery fails
    logger.warning("Model discovery failed, using hardcoded fallback")
    return [
        "gemini-3.0-pro",
        "gemini-3.0-flash",
        "gemini-3.0-flash-thinking",
        "gemini-2.0-flash-thinking-exp", 
        "gemini-2.0-pro-exp",
        "gemini-2.0-flash"
    ]

@router.get("/models")
@router.get("/v1/models")
async def list_models():
    """
    List currently available models.
    Dynamically fetches models available to the active Google account.
    """
    model_ids = await _discover_gemini_models()
    
    current_time = int(time.time())
    
    response_data = []
    for model_id in model_ids:
        response_data.append({
            "id": model_id,
            "object": "model",
            "created": current_time,
            "owned_by": "google",
            "permission": [],
            "root": model_id,
            "parent": None,
        })
        
    return {
        "object": "list",
        "data": response_data
    }
