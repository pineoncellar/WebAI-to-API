# src/app/endpoints/models.py
import time
import re
import asyncio
from fastapi import APIRouter
from app.logger import logger
from app.services.gemini_client import get_gemini_client

router = APIRouter()

# Global cache for discovered models
_CACHED_MODELS = None
_CACHE_TIMESTAMP = 0
_CACHE_TTL = 3600  # Refresh every hour in case new models appear

async def _discover_gemini_models():
    """
    Dynamically discovers available models by triggering a specific error
    in the underlying library which lists valid models.
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
        # Intentionally request an invalid model to trigger the validation error
        # which contains the list of available models.
        # We assume the library raises ValueError or similar with the list.
        await client.generate_content("test", model="FORCE_MODEL_DISCOVERY_HACK")
    except Exception as e:
        error_str = str(e)
        # Look for pattern: "Available models: unspecified, model1, model2, ..."
        # Example error: ValueError: Unknown model name: ... Available models: unspecified, gemini-3.0-pro, ...
        match = re.search(r"Available models:\s*(.+)", error_str)
        if match:
            models_str = match.group(1)
            # Split by comma and clean up
            models_list = [m.strip() for m in models_str.split(",")]
            # Filter out 'unspecified' and empty strings
            valid_models = [m for m in models_list if m and m.lower() != "unspecified"]
            
            if valid_models:
                logger.info(f"Dynamically discovered models: {valid_models}")
                _CACHED_MODELS = valid_models
                _CACHE_TIMESTAMP = current_time
                return valid_models
        else:
            logger.warning(f"Could not parse 'Available models' from error: {error_str}")

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
