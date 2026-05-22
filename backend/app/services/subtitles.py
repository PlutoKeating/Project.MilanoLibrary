import os
import random
import httpx
import subprocess
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from app.config import settings

import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


# ============== Local Audio Extraction & ASR ==============

async def _extract_audio(video_path: str, audio_path: str) -> None:
    """Extract audio track from video to mono 16kHz WAV for Whisper."""
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"FFmpeg audio extraction failed: {stderr.decode()}")


async def _transcribe_with_whisper_api(audio_path: str, api_key: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """Use OpenAI Whisper API to transcribe audio. Returns segments with start/end/text."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=base_url or "https://api.openai.com/v1")

    with open(audio_path, "rb") as f:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
        )

    # verbose_json returns segments
    segments = getattr(transcription, "segments", None)
    if segments is None and isinstance(transcription, dict):
        segments = transcription.get("segments", [])

    result = []
    if segments:
        for seg in segments:
            if hasattr(seg, "start"):
                result.append({
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": str(seg.text).strip(),
                })
            elif isinstance(seg, dict):
                result.append({
                    "start": float(seg.get("start", 0)),
                    "end": float(seg.get("end", 0)),
                    "text": str(seg.get("text", "")).strip(),
                })
    else:
        # Fallback: whole text as one segment
        text = getattr(transcription, "text", "")
        if isinstance(transcription, dict):
            text = transcription.get("text", "")
        result.append({"start": 0.0, "end": 0.0, "text": str(text).strip()})

    return result


def _reduce_local_subtitle_timestamp(subtitles: List[Dict[str, Any]], should_show_timestamp: bool = False) -> List[Dict[str, Any]]:
    """Group local ASR results into chunks similar to Bilibili/YouTube reducers."""
    total_group_count = 30
    minimum_count_one_group = 7
    each_group_count = (
        len(subtitles) / total_group_count
        if len(subtitles) > total_group_count
        else minimum_count_one_group
    )

    result = []
    for index, item in enumerate(subtitles):
        group_index = int(index // minimum_count_one_group)
        if len(result) <= group_index:
            result.append({
                "index": group_index,
                "s": item.get("start", 0),
                "text": f"{item.get('start', 0)} - " if should_show_timestamp else "",
            })
        result[group_index]["text"] += f"{item.get('text', '')} "

    return result


async def fetch_local_subtitle(
    local_path: str,
    should_show_timestamp: bool = False,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_type: Optional[str] = "online",
    local_model: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract audio from local video/audio and transcribe with Whisper API or local model."""
    audio_path = str(Path(local_path).with_suffix(".wav"))
    from app.services.status_tracker import update_step
    try:
        if task_id:
            update_step(task_id, "extract_audio", "running", message="正在通过 FFmpeg 提取并标准化音频 (单声道, 16kHz, PCM 16-bit)...")
        await _extract_audio(local_path, audio_path)
        if task_id:
            update_step(task_id, "extract_audio", "completed", message="音频提取与格式标准化完成")

        # Try Whisper API first if online mode and API key is provided
        if model_type != "local" and api_key:
            try:
                if task_id:
                    update_step(task_id, "transcribe", "running", message="正在通过 OpenAI Whisper API 识别语音...")
                segments = await _transcribe_with_whisper_api(audio_path, api_key, base_url)
                if task_id:
                    update_step(task_id, "transcribe", "completed", message="OpenAI Whisper API 识别完成")
                transcripts = _reduce_local_subtitle_timestamp(segments, should_show_timestamp)
                return {
                    "title": Path(local_path).stem,
                    "subtitles_array": transcripts,
                    "description_text": None,
                }
            except Exception as e:
                err_msg = str(e)[:300]
                err_type = type(e).__name__
                # Always fallback to local model if Whisper API fails (timeout, 404, 401, etc.)
                print(f"Warning: Whisper API failed ({err_type}: {err_msg}), falling back to local whisper...")
                pass

        # Use local faster-whisper (explicit local mode or API fallback)
        try:
            from app.services.local_whisper import transcribe_audio, cancel_task, clear_cancelled_task

            # Add a reasonable timeout (e.g., 30 minutes) to avoid hanging forever on CPU-heavy models
            if task_id:
                update_step(task_id, "transcribe", "running", message="正在载入语音识别组件并启动本地 Whisper 离线引擎...")

            transcribe_task = asyncio.create_task(
                transcribe_audio(audio_path, model_name=local_model, task_id=task_id)
            )

            if task_id:
                import time
                from app.services.status_tracker import get_task_status

                last_progress = 0.0
                last_progress_time = time.monotonic()
                timeout_seconds = 600.0  # 10 minutes

                try:
                    while not transcribe_task.done():
                        try:
                            # Wait for a short interval
                            await asyncio.wait_for(asyncio.shield(transcribe_task), timeout=5.0)
                        except asyncio.TimeoutError:
                            current_progress = 0.0
                            status = get_task_status(task_id)
                            if status and "steps" in status:
                                for step in status["steps"]:
                                    if step.get("id") == "transcribe":
                                        current_progress = step.get("progress", 0.0)
                                        break
                            
                            if current_progress > last_progress:
                                last_progress = current_progress
                                last_progress_time = time.monotonic()
                            else:
                                elapsed = time.monotonic() - last_progress_time
                                if elapsed > timeout_seconds:
                                    cancel_task(task_id)
                                    transcribe_task.cancel()
                                    try:
                                        await transcribe_task
                                    except asyncio.CancelledError:
                                        pass
                                    raise TimeoutError("本地 Whisper 10分钟内未更新进度，转录超时")
                        else:
                            break
                    
                    result = await transcribe_task
                finally:
                    clear_cancelled_task(task_id)
            else:
                result = await asyncio.wait_for(transcribe_task, timeout=1800)

            segments = result["segments"]
            if task_id:
                update_step(task_id, "transcribe", "completed", message="本地 Whisper 离线转录完成")
            transcripts = _reduce_local_subtitle_timestamp(segments, should_show_timestamp)
            return {
                "title": Path(local_path).stem,
                "subtitles_array": transcripts,
                "description_text": None,
            }
        except Exception as e:
            if task_id:
                update_step(task_id, "transcribe", "failed", message=f"本地 Whisper 识别失败: {str(e)[:150]}")
            return {
                "title": Path(local_path).stem,
                "subtitles_array": None,
                "description_text": None,
                "error": f"Local Whisper failed: {type(e).__name__}: {str(e)[:300]}",
            }
    except Exception as e:
        if task_id:
            update_step(task_id, "extract_audio", "failed", message=f"音频提取与标准化失败: {str(e)[:150]}")
        return {
            "title": Path(local_path).stem,
            "subtitles_array": None,
            "description_text": None,
            "error": f"Audio extraction failed: {type(e).__name__}: {str(e)[:300]}",
        }
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


# ============== Bilibili ==============

async def fetch_bilibili_subtitle_urls(video_id: str, page_number: Optional[str] = None) -> Dict[str, Any]:
    session_tokens = []
    if settings.bilibili_session_token:
        session_tokens = [t.strip() for t in settings.bilibili_session_token.split(",") if t.strip()]
    sessdata = random.choice(session_tokens) if session_tokens else None

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        ),
        "Host": "api.bilibili.com",
    }
    if sessdata:
        headers["Cookie"] = f"SESSDATA={sessdata}"

    params = f"?aid={video_id[2:]}" if video_id.startswith("av") else f"?bvid={video_id}"
    request_url = f"https://api.bilibili.com/x/web-interface/view{params}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(request_url, headers=headers)
        resp.raise_for_status()
        json_data = resp.json()

    data = json_data.get("data", {})

    # Multi-part video support
    if page_number or (data.get("pages") and len(data["pages"]) > 0):
        aid = data.get("aid")
        pages = data.get("pages", [])
        target_page = int(page_number or 1)
        page_item = next((p for p in pages if int(p.get("page", 0)) == target_page), None)
        cid = page_item.get("cid") if page_item else None

        if not aid or not cid:
            return data

        page_url = f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(page_url, headers=headers)
            resp.raise_for_status()
            j = resp.json()

        subtitle_list = j.get("data", {}).get("subtitle", {}).get("subtitles", [])
        return {**data, "subtitle": {"list": subtitle_list}}

    return data


async def fetch_bilibili_subtitle(
    video_id: str, page_number: Optional[str] = None, should_show_timestamp: bool = False
) -> Dict[str, Any]:
    res = await fetch_bilibili_subtitle_urls(video_id, page_number)
    title = res.get("title", "")
    desc = res.get("desc", "")
    dynamic = res.get("dynamic", "")
    description_text = f"{desc} {dynamic}".strip() if (desc or dynamic) else None
    subtitle_list = res.get("subtitle", {}).get("list", [])

    if not subtitle_list:
        return {"title": title, "subtitles_array": None, "description_text": description_text}

    better_subtitle = next(
        (s for s in subtitle_list if s.get("lan") == "zh-CN"),
        subtitle_list[0],
    )
    subtitle_url = better_subtitle.get("subtitle_url", "")
    if subtitle_url.startswith("//"):
        subtitle_url = f"https:{subtitle_url}"

    if not subtitle_url:
        return {"title": title, "subtitles_array": None, "description_text": description_text}

    async with httpx.AsyncClient() as client:
        resp = await client.get(subtitle_url)
        resp.raise_for_status()
        subtitles = resp.json()

    subtitle_body = subtitles.get("body", [])
    if isinstance(subtitle_body, list) and len(subtitle_body) > 0:
        first_text = str(subtitle_body[0].get("content", ""))[:100]
        last_text = str(subtitle_body[-1].get("content", ""))[:100]
        sample_text = (first_text + last_text).lower()
        title_keywords = [
            w for w in (
                str(title or "").lower()
                .replace(r"[^\u4e00-\u9fa5a-z0-9]+", " ")
                .split()
            )
            if len(w) >= 2
        ]
        matched = sum(1 for kw in title_keywords if kw in sample_text)
        if title_keywords and matched == 0:
            return {"title": title, "subtitles_array": None, "description_text": description_text}

    transcripts = reduce_bilibili_subtitle_timestamp(subtitle_body, should_show_timestamp)
    return {"title": title, "subtitles_array": transcripts, "description_text": description_text}


def reduce_bilibili_subtitle_timestamp(
    subtitles: List[Dict[str, Any]], should_show_timestamp: bool = False
) -> List[Dict[str, Any]]:
    total_group_count = 30
    minimum_count_one_group = 7
    each_group_count = (
        len(subtitles) / total_group_count
        if len(subtitles) > total_group_count
        else minimum_count_one_group
    )

    result = []
    for index, item in enumerate(subtitles):
        group_index = int(index // minimum_count_one_group)
        if len(result) <= group_index:
            result.append({
                "index": group_index,
                "s": item.get("from", 0),
                "text": f"{item.get('from', 0)} - " if should_show_timestamp else "",
            })
        result[group_index]["text"] += f"{item.get('content', '')} "

    return result


# ============== YouTube ==============

SUBTITLE_DOWNLOADER_URL = "https://savesubs.com"


async def fetch_youtube_subtitle_urls(video_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUBTITLE_DOWNLOADER_URL}/action/extract",
            json={"data": {"url": f"https://www.youtube.com/watch?v={video_id}"}},
            headers={
                "Content-Type": "text/plain",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
                ),
                "X-Auth-Token": settings.savesubs_x_auth_token or "",
                "X-Requested-Domain": "savesubs.com",
                "X-Requested-With": "xmlhttprequest",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    response_data = data.get("response", {})
    return {
        "title": response_data.get("title", ""),
        "subtitle_list": response_data.get("formats", []),
    }


async def fetch_youtube_subtitle(
    video_id: str, should_show_timestamp: bool = False
) -> Dict[str, Any]:
    result = await fetch_youtube_subtitle_urls(video_id)
    title = result.get("title", "")
    subtitle_list = result.get("subtitle_list", [])

    if not subtitle_list:
        return {"title": title, "subtitles_array": None}

    better_subtitle = (
        next((s for s in subtitle_list if s.get("quality") == "zh-CN"), None)
        or next((s for s in subtitle_list if s.get("quality") == "English"), None)
        or next((s for s in subtitle_list if s.get("quality") and s["quality"].startswith("English (auto")), None)
        or subtitle_list[0]
    )

    # Always attempt to fetch the JSON subtitle to get/preserve the timestamp records ("s" key)
    subtitle_url = f"{SUBTITLE_DOWNLOADER_URL}{better_subtitle['url']}?ext=json"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(subtitle_url)
            resp.raise_for_status()
            subtitles = resp.json()
        transcripts = reduce_youtube_subtitle_timestamp(subtitles, should_show_timestamp)
        return {"title": title, "subtitles_array": transcripts}
    except Exception as e:
        # Fallback to .txt if JSON subtitle fails
        print(f"Warning: JSON subtitle failed, falling back to txt. Error: {e}")
        subtitle_url = f"{SUBTITLE_DOWNLOADER_URL}{better_subtitle['url']}?ext=txt"
        async with httpx.AsyncClient() as client:
            resp = await client.get(subtitle_url)
            resp.raise_for_status()
            subtitles = resp.text

        texts = [t.strip() for t in subtitles.split("\r\n\r\n") if t.strip()]
        transcripts = [{"text": t, "index": i, "s": 0.0} for i, t in enumerate(texts)]
        return {"title": title, "subtitles_array": transcripts}


def reduce_youtube_subtitle_timestamp(
    subtitles: List[Dict[str, Any]], should_show_timestamp: bool = False
) -> List[Dict[str, Any]]:
    total_group_count = 30
    minimum_count_one_group = 7
    each_group_count = (
        len(subtitles) / total_group_count
        if len(subtitles) > total_group_count
        else minimum_count_one_group
    )

    result = []
    for index, item in enumerate(subtitles):
        group_index = int(index // minimum_count_one_group)
        if len(result) <= group_index:
            result.append({
                "index": group_index,
                "s": item.get("start", 0),
                "text": f"{item.get('start', 0)} - " if should_show_timestamp else "",
            })
        lines = " ".join(item.get("lines", []))
        result[group_index]["text"] += f"{lines} "

    return result


# ============== Unified ==============

async def fetch_subtitle(
    video_config: dict, should_show_timestamp: bool = False
) -> Dict[str, Any]:
    if "subtitles_array" in video_config:
        return {
            "title": video_config.get("title", "Video"),
            "subtitles_array": video_config["subtitles_array"],
            "description_text": video_config.get("description_text"),
        }
    service = video_config.get("service", "bilibili")
    video_id = video_config.get("video_id", "")
    page_number = video_config.get("page_number")

    if service == "youtube":
        return await fetch_youtube_subtitle(video_id, should_show_timestamp)
    if service in ("local-video", "local-audio"):
        local_path = video_config.get("local_path", "")
        api_key = video_config.get("whisper_api_key") or settings.openai_api_key or settings.openai_compatible_api_key
        base_url = video_config.get("whisper_base_url")
        model_type = video_config.get("model_type", "online")
        local_model = video_config.get("local_model")
        task_id = video_config.get("task_id")
        result = await fetch_local_subtitle(
            local_path, should_show_timestamp, api_key, base_url, model_type, local_model, task_id=task_id
        )
        if result.get("error"):
            return result
        return result
    return await fetch_bilibili_subtitle(video_id, page_number, should_show_timestamp)
