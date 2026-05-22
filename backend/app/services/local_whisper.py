import os
import shutil
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import settings

_WhisperModel = None
_model_instance = None

# --- Model registry ---
AVAILABLE_MODELS = [
    {"name": "tiny", "label": "Tiny", "size": "~39MB"},
    {"name": "base", "label": "Base", "size": "~74MB"},
    {"name": "small", "label": "Small", "size": "~466MB"},
    {"name": "medium", "label": "Medium", "size": "~1.5GB"},
    {"name": "large-v3", "label": "Large V3", "size": "~3GB"},
]

_download_progress: Dict[str, Dict[str, Any]] = {}
_download_lock = threading.Lock()

# --- Cancelled tasks registry ---
_cancelled_tasks = set()
_cancelled_lock = threading.Lock()


def cancel_task(task_id: str):
    if not task_id:
        return
    with _cancelled_lock:
        _cancelled_tasks.add(task_id)


def is_task_cancelled(task_id: str) -> bool:
    if not task_id:
        return False
    with _cancelled_lock:
        return task_id in _cancelled_tasks


def clear_cancelled_task(task_id: str):
    if not task_id:
        return
    with _cancelled_lock:
        _cancelled_tasks.discard(task_id)


def _get_model_base_dir() -> str:
    return "/app/models"


def get_model_path(model_name: str) -> str:
    return f"{_get_model_base_dir()}/faster-whisper-{model_name}"


def _get_download_marker_path(model_name: str) -> str:
    """Filesystem marker to survive container restarts."""
    return os.path.join(_get_model_base_dir(), f".downloading-{model_name}")


def _set_downloading_marker(model_name: str):
    Path(_get_download_marker_path(model_name)).touch()


def _remove_downloading_marker(model_name: str):
    try:
        os.remove(_get_download_marker_path(model_name))
    except FileNotFoundError:
        pass


def _has_downloading_marker(model_name: str) -> bool:
    return os.path.exists(_get_download_marker_path(model_name))


def _is_valid_model_dir(model_path: str) -> bool:
    """Check if a directory contains the required model.bin for CTranslate2."""
    if not os.path.isdir(model_path):
        return False
    return os.path.isfile(os.path.join(model_path, "model.bin"))


def is_model_installed(model_name: str) -> bool:
    return _is_valid_model_dir(get_model_path(model_name))


def list_local_models() -> List[Dict[str, Any]]:
    result = []
    for m in AVAILABLE_MODELS:
        result.append(
            {
                "name": m["name"],
                "label": m["label"],
                "size": m["size"],
                "installed": is_model_installed(m["name"]),
            }
        )
    return result


def get_download_progress(model_name: str) -> Optional[Dict[str, Any]]:
    with _download_lock:
        progress = _download_progress.get(model_name)

    if progress is None and _has_downloading_marker(model_name):
        model_path = get_model_path(model_name)
        expected_size = _MODEL_SIZE_BYTES.get(model_name, 0)
        cache_size = _get_cache_size(os.path.join(model_path, ".cache"))
        pct = min(99, int(cache_size / expected_size * 100)) if expected_size > 0 else 0
        return {"status": "downloading", "progress": pct, "error": None}

    if progress and progress.get("status") == "downloading" and not _has_downloading_marker(model_name):
        _set_download_progress(model_name, {"status": "failed", "progress": 0, "error": "Previous download crashed. Please retry."})
        return _download_progress.get(model_name)

    if progress and progress.get("status") == "downloading":
        model_path = get_model_path(model_name)
        expected_size = _MODEL_SIZE_BYTES.get(model_name, 0)
        cache_size = _get_cache_size(os.path.join(model_path, ".cache"))
        pct = min(99, int(cache_size / expected_size * 100)) if expected_size > 0 else progress.get("progress", 0)
        if pct != progress.get("progress"):
            progress = {**progress, "progress": pct}
            _set_download_progress(model_name, progress)

    return progress


def _set_download_progress(model_name: str, progress: Dict[str, Any]):
    with _download_lock:
        _download_progress[model_name] = progress


# Approximate total bytes for each model (model.bin + tokenizer + vocab + config)
_MODEL_SIZE_BYTES = {
    "tiny": 44_000_000,
    "base": 81_000_000,
    "small": 470_000_000,
    "medium": 1_540_000_000,
    "large-v3": 3_100_000_000,
}


def _get_cache_size(path: str) -> int:
    """Return total byte size of all files under path."""
    total = 0
    for dp, _dn, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dp, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def _download_model_thread(model_name: str):
    """Run download in a background thread with stalled-download detection and live progress."""
    import time

    model_path = get_model_path(model_name)

    # If already valid, clean up marker and mark completed
    if _is_valid_model_dir(model_path):
        _remove_downloading_marker(model_name)
        _set_download_progress(model_name, {"status": "completed", "progress": 100, "error": None})
        return

    # Create marker so container restarts can detect in-progress downloads
    _set_downloading_marker(model_name)
    os.makedirs(model_path, exist_ok=True)
    _set_download_progress(model_name, {"status": "downloading", "progress": 0, "error": None})

    # Prevent huggingface_hub HTTP calls from hanging indefinitely
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")

    cache_dir = os.path.join(model_path, ".cache")
    expected_size = _MODEL_SIZE_BYTES.get(model_name, 0)
    stop_progress = threading.Event()
    exception_holder = [None]
    done_event = threading.Event()

    def _do_download():
        try:
            from faster_whisper import download_model
            download_model(model_name, output_dir=model_path)
        except Exception as e:
            exception_holder[0] = e
        finally:
            done_event.set()

    def _monitor_progress():
        try:
            last_size = 0
            stagnant_count = 0
            while True:
                time.sleep(30)
                current_size = _get_cache_size(cache_dir)
                if current_size > last_size:
                    last_size = current_size
                    stagnant_count = 0
                else:
                    stagnant_count += 1
                    if stagnant_count >= 4:
                        raise RuntimeError(
                            "Download stalled for 2 minutes. "
                            "Hugging Face rate-limits unauthenticated requests. "
                            "Set HF_TOKEN in backend/.env to speed up downloads."
                        )
        except Exception as e:
            exception_holder[0] = e
        finally:
            done_event.set()

    def _update_progress():
        """Poll cache size every 2s and update progress percentage."""
        while not stop_progress.is_set():
            time.sleep(2)
            cache_size = _get_cache_size(cache_dir)
            if expected_size > 0:
                pct = min(99, int(cache_size / expected_size * 100))
            else:
                pct = 0
            _set_download_progress(
                model_name,
                {"status": "downloading", "progress": pct, "error": None},
            )

    try:
        progress_thread = threading.Thread(target=_update_progress, daemon=True)
        progress_thread.start()

        download_thread = threading.Thread(target=_do_download, daemon=True)
        monitor_thread = threading.Thread(target=_monitor_progress, daemon=True)
        download_thread.start()
        monitor_thread.start()

        done_event.wait()  # Wait for either download or monitor to finish
        stop_progress.set()
        progress_thread.join(timeout=3)

        if exception_holder[0] is not None:
            raise exception_holder[0]

        if not _is_valid_model_dir(model_path):
            raise RuntimeError("Download finished but model.bin is missing.")

        _set_download_progress(model_name, {"status": "completed", "progress": 100, "error": None})
    except Exception as e:
        stop_progress.set()
        if os.path.isdir(model_path):
            shutil.rmtree(model_path, ignore_errors=True)
        _set_download_progress(model_name, {"status": "failed", "progress": 0, "error": str(e)})
    finally:
        _remove_downloading_marker(model_name)


def start_model_download(model_name: str):
    """Kick off a background download thread for the given model.

    If a previous download was interrupted (marker exists but model not installed),
    clean up and restart automatically.
    """
    if model_name not in {m["name"] for m in AVAILABLE_MODELS}:
        raise ValueError(f"Unknown model: {model_name}")

    # If already installed, mark as completed
    if is_model_installed(model_name):
        _remove_downloading_marker(model_name)
        _set_download_progress(model_name, {"status": "completed", "progress": 100, "error": None})
        return

    progress = get_download_progress(model_name)
    if progress and progress["status"] == "downloading":
        # Memory state says downloading — also verify the marker file exists.
        # If no marker, the stale memory state was left by a previous crash.
        if _has_downloading_marker(model_name):
            return  # Already in progress
        _set_download_progress(model_name, {"status": "not_installed", "progress": 0, "error": None})

    # If marker exists but model not installed, previous download was interrupted.
    # Clean up partial files and restart.
    if _has_downloading_marker(model_name):
        model_path = get_model_path(model_name)
        if os.path.isdir(model_path):
            shutil.rmtree(model_path, ignore_errors=True)
        _remove_downloading_marker(model_name)

    thread = threading.Thread(target=_download_model_thread, args=(model_name,), daemon=True)
    thread.start()


def _get_model_class():
    global _WhisperModel
    if _WhisperModel is None:
        from faster_whisper import WhisperModel

        _WhisperModel = WhisperModel
    return _WhisperModel


def _get_device_and_compute_type():
    device = settings.local_whisper_device
    compute_type = settings.local_whisper_compute_type

    if device == "auto":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                device = "cuda"
            else:
                device = "cpu"
        except Exception:
            device = "cpu"

    if compute_type == "auto":
        if device == "cuda":
            compute_type = "float16"
        else:
            compute_type = "int8"

    return device, compute_type


def _try_load_model(model_size: str, device: str, compute_type: str):
    """Try to load model with given config; fallback to cpu+int8 on failure."""
    WhisperModel = _get_model_class()
    try:
        return WhisperModel(model_size, device=device, compute_type=compute_type)
    except RuntimeError as e:
        if "cublas" in str(e).lower() or "cuda" in str(e).lower():
            # CUDA runtime missing — fallback to CPU
            return WhisperModel(model_size, device="cpu", compute_type="int8")
        raise


def _resolve_model_path() -> str:
    """Resolve model config value to an absolute path.

    If the value is already an absolute path or exists on disk, use it directly.
    Otherwise treat it as a model size name (small, medium, etc.) and map to
    /app/models/faster-whisper-<size> so the mapped volume can persist it.
    """
    model = settings.local_whisper_model
    if model.startswith("/") or os.path.exists(model):
        return model
    return f"/app/models/faster-whisper-{model}"


def _ensure_model_downloaded(model_path: str):
    """Download model from Hugging Face if directory is missing or invalid."""
    if _is_valid_model_dir(model_path):
        return  # Model already present

    os.makedirs(model_path, exist_ok=True)

    size = os.path.basename(model_path).replace("faster-whisper-", "")
    from faster_whisper import download_model

    try:
        download_model(size, output_dir=model_path)
        if not _is_valid_model_dir(model_path):
            raise RuntimeError("Download finished but model.bin is missing.")
    except Exception:
        # Clean up partial download so we don't falsely appear installed
        if os.path.isdir(model_path):
            shutil.rmtree(model_path, ignore_errors=True)
        raise


def _load_model(model_name: Optional[str] = None):
    """Load a Whisper model. If model_name is given, use that specific model.
    Otherwise fall back to settings.local_whisper_model."""
    global _model_instance
    if _model_instance is not None and model_name is None:
        return _model_instance

    target = model_name or settings.local_whisper_model
    if target.startswith("/") or os.path.exists(target):
        model_path = target
    else:
        model_path = get_model_path(target)
        if not is_model_installed(target):
            raise RuntimeError(f"Model '{target}' is not installed. Please download it first.")

    device, compute_type = _get_device_and_compute_type()
    loaded = _try_load_model(model_path, device, compute_type)
    if model_name is None:
        _model_instance = loaded
    return loaded


def _segments_to_dicts(segments, duration: float, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
    from app.services.status_tracker import update_step
    result = []
    for seg in segments:
        if task_id and is_task_cancelled(task_id):
            break
        result.append(
            {
                "start": float(seg.start),
                "end": float(seg.end),
                "text": str(seg.text).strip(),
            }
        )
        if task_id and duration > 0:
            progress = min(99.0, (float(seg.end) / duration) * 100)
            update_step(
                task_id,
                "transcribe",
                "running",
                progress=progress,
                message=f"正在转录语音... {progress:.1f}% [已处理: {seg.end:.1f}秒 / 总长: {duration:.1f}秒]"
            )
    return result


def _run_transcribe_sync(audio_path: str, model_name: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
    model = _load_model(model_name)
    try:
        segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
        # We must iterate segments to actually execute the transcription
        duration = getattr(info, "duration", 0.0) or 0.0
        segments_list = _segments_to_dicts(segments, duration, task_id)
    except RuntimeError as e:
        err_text = str(e).lower()
        if "cublas" in err_text or "cuda" in err_text:
            fallback = model_name or settings.local_whisper_model
            model = _try_load_model(get_model_path(fallback), "cpu", "int8")
            segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
            duration = getattr(info, "duration", 0.0) or 0.0
            segments_list = _segments_to_dicts(segments, duration, task_id)
        else:
            raise

    return {
        "segments": segments_list,
        "language": info.language,
        "language_probability": info.language_probability,
    }


async def transcribe_audio(audio_path: str, model_name: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Transcribe audio file using local faster-whisper model.

    Args:
        audio_path: Path to the audio file.
        model_name: Specific local model to use (e.g. 'small'). Uses settings fallback if None.
        task_id: Task ID for progress tracking.

    Returns:
        {
            "segments": [{"start": float, "end": float, "text": str}, ...],
            "language": str,
            "language_probability": float,
        }
    """
    import asyncio
    return await asyncio.to_thread(_run_transcribe_sync, audio_path, model_name, task_id)
