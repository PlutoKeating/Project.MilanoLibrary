from fastapi import APIRouter, HTTPException
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
