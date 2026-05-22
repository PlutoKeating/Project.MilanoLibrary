from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional
from app.models import SummarizeRequest
from app.services.openai_client import generate_summary_stream, generate_summary
from app.services.chapters import (
    _parse_youtube_chapters_from_description,
    _parse_bilibili_chapters,
    detect_chapters_from_subtitles,
)
from app.services.subtitles import (
    fetch_youtube_subtitle_urls,
    fetch_bilibili_subtitle_urls,
    fetch_subtitle,
)

router = APIRouter(prefix="/api", tags=["summarize"])


async def _detect_chapters_for_url(video_config: dict, user_config: Optional[dict]) -> list:
    """Detect chapters for URL-based videos."""
    chapters = []
    service = video_config.get("service", "")
    video_id = video_config.get("video_id", "")
    page_number = video_config.get("page_number")

    if service == "youtube":
        try:
            yt_meta = await fetch_youtube_subtitle_urls(video_id)
            desc = yt_meta.get("description", "")
            # We don't have duration here, pass 0 as fallback
            if desc:
                chapters = _parse_youtube_chapters_from_description(desc, 0)
        except Exception:
            pass

    elif service == "bilibili":
        try:
            bili_meta = await fetch_bilibili_subtitle_urls(video_id, page_number)
            pages = bili_meta.get("pages", [])
            if pages and len(pages) > 1:
                # Estimate total duration from subtitle data
                duration = 0
                try:
                    sub_result = await fetch_subtitle(video_config, False)
                    if sub_result.get("subtitles_array"):
                        last = sub_result["subtitles_array"][-1]
                        duration = last.get("s", 0)
                except Exception:
                    pass
                chapters = _parse_bilibili_chapters(pages, duration)
        except Exception:
            pass

    # Fallback: detect from subtitles via LLM
    if not chapters:
        try:
            sub_result = await fetch_subtitle(video_config, False)
            subtitles = sub_result.get("subtitles_array", [])
            title = sub_result.get("title", "Video")
            if subtitles:
                language = video_config.get("output_language", "zh")
                from app.services.prompts import PROMPT_LANGUAGE_MAP
                lang_name = PROMPT_LANGUAGE_MAP.get(language, language)
                api_key = user_config.get("user_key") if user_config else None
                base_url = user_config.get("base_url") if user_config else None
                model = user_config.get("model_name") if user_config else None
                chapters = await detect_chapters_from_subtitles(
                    title=title,
                    subtitles=subtitles,
                    language=lang_name,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                )
        except Exception:
            pass

    return chapters


@router.post("/summarize")
async def summarize_endpoint(req: SummarizeRequest):
    video_config = req.video_config.model_dump()
    user_config = req.user_config.model_dump() if req.user_config else None

    # Force emoji, chapters, and remove generated timestamp text
    video_config["show_emoji"] = True
    video_config["respect_chapters"] = True
    video_config["show_timestamp"] = False
    if user_config:
        user_config["should_show_timestamp"] = False

    task_id = video_config.get("task_id")
    if task_id:
        from app.services.status_tracker import init_task, update_step
        init_task(task_id, "url")
        update_step(task_id, "fetch_metadata", "running", message="正在获取网页视频元数据与平台信息...")

    # 1. Adapt and fetch metadata & play url
    service = video_config.get("service", "bilibili")
    video_id = video_config.get("video_id", "")
    page_number = video_config.get("page_number")

    from app.services.adapter_manager import get_adapter_instance, download_video_from_adapter
    adapter = get_adapter_instance(service, video_id, page_number)

    metadata = {}
    if adapter:
        metadata = await adapter.get_metadata()
        video_config["metadata"] = metadata

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "fetch_metadata", "completed", message=f"已成功获取平台元数据: {metadata.get('title', '视频')}")
        update_step(task_id, "download_video", "running", message="正在获取视频下载连接并下载视频流数据...")

    # Create temporary storage for downloaded video
    import tempfile
    from pathlib import Path
    temp_dir = Path(tempfile.gettempdir()) / "milanolibrary"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if adapter:
        # Download video to local path
        local_path = await download_video_from_adapter(adapter, temp_dir)
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform service")

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "download_video", "completed", message="视频流数据下载完成，即将进行音频提取")
        update_step(task_id, "extract_audio", "running", message="正在提取并标准化视频音频...")

    # Ingest the downloaded video file
    from app.services.video_ingest import MetaVideo, _probe_media_duration
    duration = _probe_media_duration(local_path)
    meta_video = MetaVideo(
        video_id=video_id,
        source_type="link",
        original_url=None,
        local_path=local_path,
        title=metadata.get("title", "Video"),
        duration_seconds=duration,
        format=Path(local_path).suffix.lstrip("."),
    )

    # Route downloaded video directly through the unified _run_pipeline!
    from app.routers.upload import _run_pipeline
    enable_stream = video_config.get("enable_stream", True)
    return await _run_pipeline(meta_video, video_config, user_config, enable_stream)


@router.get("/status/{task_id}")
async def get_status_endpoint(task_id: str):
    from app.services.status_tracker import get_task_status
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.get("/adapters")
async def get_adapters_endpoint():
    from app.services.adapter_manager import get_all_adapters
    return get_all_adapters()


@router.post("/adapters/upload")
async def upload_adapter_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are supported")
    
    content = await file.read()
    try:
        content_str = content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Must be UTF-8")

    from app.services.adapter_manager import save_adapter_file
    res = save_adapter_file(file.filename, content_str)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to validate adapter"))
    return res


@router.delete("/adapters/{service_id}")
async def delete_adapter_endpoint(service_id: str):
    from app.services.adapter_manager import delete_adapter_file
    res = delete_adapter_file(service_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to delete adapter"))
    return res
