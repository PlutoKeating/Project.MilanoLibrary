from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio
from app.config import settings
from app.services._client import select_api_key, create_client
from app.services.local_whisper import (
    AVAILABLE_MODELS,
    list_local_models,
    is_model_installed,
    start_model_download,
    get_download_progress,
)

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/local")
async def get_local_models():
    """List all available local Whisper models and their installation status."""
    return {"models": list_local_models()}


@router.post("/local/{model_name}/download")
async def download_local_model(model_name: str):
    """Start downloading a local Whisper model in the background."""
    valid_names = {m["name"] for m in AVAILABLE_MODELS}
    if model_name not in valid_names:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")

    if is_model_installed(model_name):
        return {"status": "completed", "message": "Model already installed"}

    start_model_download(model_name)
    return {"status": "started", "message": f"Download started for {model_name}"}


@router.get("/local/{model_name}/status")
async def get_local_model_status(model_name: str):
    """Get download/installation status of a specific model."""
    valid_names = {m["name"] for m in AVAILABLE_MODELS}
    if model_name not in valid_names:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")

    installed = is_model_installed(model_name)
    progress = get_download_progress(model_name)

    if installed and (progress is None or progress.get("status") != "downloading"):
        return {"status": "installed", "progress": 100}

    if progress:
        return {
            "status": progress.get("status", "unknown"),
            "progress": progress.get("progress", 0),
            "error": progress.get("error"),
        }

    return {"status": "not_installed", "progress": 0}


class VerifyConfigRequest(BaseModel):
    user_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None


@router.post("/verify-connectivity")
async def verify_connectivity(req: VerifyConfigRequest):
    """Verify connectivity to the LLM API provider with given credentials."""
    api_key = select_api_key(req.user_key)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Missing API key for OpenAI-compatible provider. Please configure an API key."
        )

    # Create client
    client = create_client(req.base_url)
    client.api_key = api_key

    model = req.model_name or settings.openai_compatible_model

    try:
        # Request a quick completion to verify credentials and model
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                stream=False,
            ),
            timeout=10.0
        )
        content = response.choices[0].message.content or ""
        return {
            "status": "success",
            "message": f"Successfully connected to model '{model}'. Response: {content.strip()}"
        }
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Connection timed out (10s) while trying to reach the API provider. Please check your network or BASE URL."
        )
    except Exception as e:
        # Extract meaningful error details
        error_msg = str(e)
        raise HTTPException(
            status_code=400,
            detail=f"API connectivity test failed: {error_msg}"
        )
