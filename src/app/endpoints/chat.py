# src/app/endpoints/chat.py
import time
import uuid
import json
import asyncio
import httpx
import os
import base64
import tempfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.logger import logger
from schemas.request import GeminiRequest, OpenAIChatRequest
from app.services.gemini_client import get_gemini_client, init_gemini_client
from app.services.session_manager import get_translate_session_manager
from app.config import is_debug_mode

router = APIRouter()
DEBUG_MODE = is_debug_mode()


def _serialize_payload(payload):
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    return payload

@router.post("/translate")
async def translate_chat(request: GeminiRequest):
    gemini_client = get_gemini_client()
    session_manager = get_translate_session_manager()
    if not gemini_client or not session_manager:
        raise HTTPException(status_code=503, detail="Gemini client is not initialized.")
    if DEBUG_MODE:
        logger.debug("/translate request payload: %s", _serialize_payload(request))
    try:
        # This call now correctly uses the fixed session manager
        response = await session_manager.get_response(request.model, request.message, request.files)
        if DEBUG_MODE:
            logger.debug("/translate response text: %s", getattr(response, "text", response))
        return {"response": response.text}
    except Exception as e:
        logger.error(f"Error in /translate endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during translation: {str(e)}")

def convert_to_openai_format(response_text: str, model: str, stream: bool = False, reasoning_content: str = None):
    import uuid
    request_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())
    
    # Calculate crude token counts (approximation: 1 token ~= 4 chars)
    completion_tokens = len(response_text) // 4
    if reasoning_content:
        completion_tokens += len(reasoning_content) // 4
        
    prompt_tokens = 0 # We don't have easy access to input length here without passing it in
    total_tokens = completion_tokens + prompt_tokens

    choice_data = {
        "index": 0,
        "message": {
            "role": "assistant",
            "content": response_text,
        },
        "logprobs": None,
        "finish_reason": "stop",
    }
    
    # Add reasoning_content if present (supported by some clients for thought display)
    if reasoning_content:
        choice_data["message"]["reasoning_content"] = reasoning_content

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": created_time,
        "model": model,
        "choices": [
            choice_data
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
        return "gemini-3.0-flash" 
    return model

def build_context_prompt(messages: list) -> tuple[str, list]:
    """
    Constructs a single prompt string from the chat history and extracts any image files.
    """
    prompt_parts = []
    file_paths = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif part.get("type") == "image_url":
                    image_url = part.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image"):
                        try:
                            # Parse data URI: data:image/[ext];base64,[data]
                            header, encoded = image_url.split(",", 1)
                            ext = "png"
                            if "/" in header and ";" in header:
                                ext = header.split("/")[1].split(";")[0]
                            
                            # Create a temporary file
                            fd, path = tempfile.mkstemp(suffix=f".{ext}")
                            with os.fdopen(fd, 'wb') as tmp:
                                tmp.write(base64.b64decode(encoded))
                            file_paths.append(path)
                            if DEBUG_MODE:
                                logger.debug("Extracted image to temporary file: %s", path)
                        except Exception as e:
                            logger.error("Failed to decode base64 image: %s", e)
            
            text_content = " ".join(text_parts)
            prompt_parts.append(f"{role.capitalize()}: {text_content}")
        else:
            prompt_parts.append(f"{role.capitalize()}: {content}")
    
    return "\n\n".join(prompt_parts), file_paths

async def generate_openai_stream(data_source, model: str):
    """
    Generator that yields OpenAI-compatible stream chunks.
    Accepts either a full text string (simulation) or an async generator (real streaming).
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
    
    # 2. Process data source
    if isinstance(data_source, str):
        # Simulate streaming by splitting string
        chunk_size = 4 # characters
        for i in range(0, len(data_source), chunk_size):
            piece = data_source[i:i+chunk_size]
            chunk_content = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk_content)}\n\n"
    else:
        # Real streaming from async generator
        try:
            last_text_len = 0
            last_thought_len = 0
            
            async for chunk in data_source:
                # 1. Handle Thoughts (Reasoning Content)
                full_thoughts = getattr(chunk, "thoughts", "")
                if full_thoughts and len(full_thoughts) > last_thought_len:
                    piece = full_thoughts[last_thought_len:]
                    last_thought_len = len(full_thoughts)
                    
                    if piece:
                        chunk_thought = {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model,
                            "choices": [{"index": 0, "delta": {"reasoning_content": piece}, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(chunk_thought)}\n\n"

                # 2. Handle Text Content
                # Use total text length to calculate delta, ensuring no duplicates
                full_text = getattr(chunk, "text", "")
                if full_text and len(full_text) > last_text_len:
                    piece = full_text[last_text_len:]
                    last_text_len = len(full_text)
                    
                    if piece:
                        chunk_content = {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model,
                            "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(chunk_content)}\n\n"
        except Exception as e:
            logger.error(f"Error during streaming generation: {e}", exc_info=True)
            # Optionally yield an error chunk or just stop

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
    if DEBUG_MODE:
        logger.debug("/v1/chat/completions request payload: %s", _serialize_payload(request))
    
    target_model = normalize_model_name(request.model)
    full_prompt, extracted_files = build_context_prompt(request.messages)
    if DEBUG_MODE:
        logger.debug("Constructed prompt for Gemini (model=%s): %s", target_model, full_prompt)
        if extracted_files:
            logger.debug("Extracted %d file(s) for Gemini", len(extracted_files))

    try:
        if request.stream:
            if DEBUG_MODE:
                logger.debug("Beginning streaming response for /v1/chat/completions")
            
            stream_gen = gemini_client.generate_content_stream(
                message=full_prompt,
                model=target_model,
                files=extracted_files if extracted_files else None,
            )
            return StreamingResponse(
                generate_openai_stream(stream_gen, request.model),
                media_type="text/event-stream"
            )

        max_attempts = 2
        response = None
        last_transport_exc = None

        for attempt in range(max_attempts):
            try:
                # Currently we wait for full generation, then stream it if requested
                response = await gemini_client.generate_content(
                    message=full_prompt,
                    model=target_model,
                    files=extracted_files if extracted_files else None,
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

        if DEBUG_MODE:
            logger.debug("Raw Gemini response text: %s", response.text)

        # Extract reasoning content/thoughts if available
        reasoning_content = getattr(response, "thoughts", None)
        if DEBUG_MODE and reasoning_content:
             logger.debug("Raw Gemini response thoughts: %s", reasoning_content)

        openai_response = convert_to_openai_format(response.text, request.model, False, reasoning_content)
        if DEBUG_MODE:
            logger.debug("OpenAI-formatted response: %s", openai_response)
        return openai_response
            
    except Exception as e:
        logger.error(f"Error in /v1/chat/completions endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat completion: {str(e)}")
    finally:
        # Cleanup temporary files
        if 'extracted_files' in locals() and extracted_files:
            for file_path in extracted_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        if DEBUG_MODE:
                            logger.debug("Deleted temporary file: %s", file_path)
                except Exception as cleanup_exc:
                    logger.warning("Failed to delete temporary file %s: %s", file_path, cleanup_exc)
