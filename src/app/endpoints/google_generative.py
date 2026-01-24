# src/app/endpoints/google_generative.py
from fastapi import APIRouter, HTTPException
from app.logger import logger
from schemas.request import GoogleGenerativeRequest
from app.services.gemini_client import get_gemini_client
from app.config import is_debug_mode

router = APIRouter()
DEBUG_MODE = is_debug_mode()


def _serialize_payload(payload):
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    return payload

# @router.post("/v1beta/models/{model}:generateContent")
@router.post("/v1beta/models/{model}")
async def google_generative_generate(model: str, request: GoogleGenerativeRequest):
    model = model.split(":")
    gemini_client = get_gemini_client()
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client is not initialized.")
    if DEBUG_MODE:
        logger.debug("/v1beta/models/%s request payload: %s", model[0], _serialize_payload(request))
    
    try:
        # Extract the text from the request
        prompt = ""
        if request.contents:
            for content in request.contents:
                if content.parts:
                    for part in content.parts:
                        prompt += part.text
        
        # Call the gemini_client with the extracted prompt
        response = await gemini_client.generate_content(prompt, model[0])
        if DEBUG_MODE:
            logger.debug("Google generative prompt sent to model %s: %s", model[0], prompt)
            logger.debug("Google generative raw response text: %s", getattr(response, "text", response))
        
        # Format the response to match the Google Generative API format
        google_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": response.text
                            }
                        ],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0,
                    "safetyRatings": [
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "probability": "NEGLIGIBLE"
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "probability": "NEGLIGIBLE"
                        }
                    ]
                }
            ],
            "promptFeedback": {
                "safetyRatings": [
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "probability": "NEGLIGIBLE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "probability": "NEGLIGIBLE"
                    },
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "probability": "NEGLIGIBLE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "probability": "NEGLIGIBLE"
                    }
                ]
            }
        }
        
        if DEBUG_MODE:
            logger.debug("Google generative formatted response: %s", google_response)
        return google_response
    except Exception as e:
        logger.error(f"Error in /google_generative endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")
