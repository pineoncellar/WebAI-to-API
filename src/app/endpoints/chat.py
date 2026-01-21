# src/app/endpoints/chat.py
import time
import uuid
import json
import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.logger import logger
from schemas.request import GeminiRequest, OpenAIChatRequest
from app.services.gemini_client import get_gemini_client, init_gemini_client
from app.services.session_manager import get_translate_session_manager

router = APIRouter()

@router.post("/translate")
async def translate_chat(request: GeminiRequest):
    gemini_client = get_gemini_client()
    session_manager = get_translate_session_manager()
    if not gemini_client or not session_manager:
        raise HTTPException(status_code=503, detail="Gemini client is not initialized.")
    try:
        # This call now correctly uses the fixed session manager
        response = await session_manager.get_response(request.model, request.message, request.files)
        return {"response": response.text}
    except Exception as e:
        logger.error(f"Error in /translate endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during translation: {str(e)}")

def convert_to_openai_format(response_text: str, model: str, stream: bool = False):
    import uuid
    request_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())
    
    # Calculate crude token counts (approximation: 1 token ~= 4 chars)
    completion_tokens = len(response_text) // 4
    prompt_tokens = 0 # We don't have easy access to input length here without passing it in
    total_tokens = completion_tokens + prompt_tokens

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": created_time,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text,
                },
                "logprobs": None,
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "system_fingerprint": None
    }

def normalize_model_name(model: str) -> str:
    # If the model is an OpenAI model name, map it to a default Gemini model
    if model.startswith("gpt-") or model.startswith("text-"):
        return "gemini-2.0-flash" 
    return model

def build_context_prompt(messages: list) -> str:
    """
    Constructs a single prompt string from the chat history.
    """
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
             # Handle multimodal content (list of dicts) if present, simplistic approach for now
             text_content = " ".join([part.get("text", "") for part in content if part.get("type") == "text"])
             prompt_parts.append(f"{role.capitalize()}: {text_content}")
        else:
             prompt_parts.append(f"{role.capitalize()}: {content}")
    
    return "\n\n".join(prompt_parts)

async def generate_openai_stream(response_text: str, model: str):
    """
    Generator that yields OpenAI-compatible stream chunks.
    This simulates streaming by splitting the full response.
    """
    request_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())
    
    # 1. Send initial chunk with role
    chunk_role = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
    }
    yield f"data: {json.dumps(chunk_role)}\n\n"
    
    # 2. Split text and send chunks (simulating stream)
    # Split by words or small chunks to make it look like streaming
    chunk_size = 4 # characters
    for i in range(0, len(response_text), chunk_size):
        piece = response_text[i:i+chunk_size]
        chunk_content = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(chunk_content)}\n\n"
        # Optional: Add tiny delay to simulate network/processing, but better keep it fast for responsiveness
        # await asyncio.sleep(0.01)

    # 3. Send final chunk
    chunk_finish = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
    }
    yield f"data: {json.dumps(chunk_finish)}\n\n"
    yield "data: [DONE]\n\n"

@router.post("/v1/chat/completions")
async def chat_completions(request: OpenAIChatRequest):
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client is not initialized.")
    
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")
    
    target_model = normalize_model_name(request.model)
    full_prompt = build_context_prompt(request.messages)

    try:
        max_attempts = 2
        response = None
        last_transport_exc = None

        for attempt in range(max_attempts):
            try:
                # Currently we wait for full generation, then stream it if requested
                response = await gemini_client.generate_content(
                    message=full_prompt,
                    model=target_model,
                    files=None,
                )
                break
            except httpx.RemoteProtocolError as transport_exc:
                last_transport_exc = transport_exc
                logger.warning(
                    "Gemini transport error during chat completion (attempt %d/%d): %s",
                    attempt + 1,
                    max_attempts,
                    transport_exc,
                )
                if attempt + 1 >= max_attempts:
                    raise

                reinit_ok = await init_gemini_client()
                gemini_client = get_gemini_client()
                if not reinit_ok or not gemini_client:
                    logger.error("Failed to reinitialize Gemini client after transport error.")
                    raise transport_exc

                # Small delay to give the upstream service time to settle
                await asyncio.sleep(0.5)
        
        if response is None:
            raise last_transport_exc or RuntimeError("Gemini client returned no response")

        if not response.text:
            logger.error("Gemini returned empty response text. This usually means the parsing layout changed/failed.")
            raise ValueError("Empty response from Gemini. Check server logs for parsing errors.")

        if request.stream:
            return StreamingResponse(
                generate_openai_stream(response.text, request.model),
                media_type="text/event-stream"
            )
        else:
            return convert_to_openai_format(response.text, request.model, False)
            
    except Exception as e:
        logger.error(f"Error in /v1/chat/completions endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat completion: {str(e)}")
