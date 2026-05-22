from typing import Optional, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.models import VideoConfig, UserConfig
from app.services.video_ingest import ingest_from_upload
from app.services.video_segment import segment_video
from app.services.segment_processor import process_segments
from app.services.composer import compose_summary, compose_summary_stream
from app.services.chapters import (
    _parse_youtube_chapters_from_description,
    _parse_bilibili_chapters,
    detect_chapters_from_subtitles,
)

router = APIRouter(prefix="/api", tags=["video_process"])


async def _detect_chapters_optimized(
    meta_video,
    video_config: dict,
    user_config: Optional[dict],
    subtitles_array: list,
) -> list:
    """Detect chapters from video metadata or subtitles."""
    chapters = []
    service = video_config.get("service", "")
    duration = meta_video.duration_seconds or 0

    # YouTube: try description-based chapters
    if service == "youtube":
        from app.services.subtitles import fetch_youtube_subtitle_urls
        try:
            yt_meta = await fetch_youtube_subtitle_urls(video_config.get("video_id", ""))
            desc = yt_meta.get("description", "")
            if desc:
                chapters = _parse_youtube_chapters_from_description(desc, duration)
        except Exception:
            pass

    # Bilibili: try multi-part pages as chapters
    elif service == "bilibili":
        from app.services.subtitles import fetch_bilibili_subtitle_urls
        try:
            bili_meta = await fetch_bilibili_subtitle_urls(
                video_config.get("video_id", ""),
                video_config.get("page_number"),
            )
            pages = bili_meta.get("pages", [])
            if pages and len(pages) > 1:
                chapters = _parse_bilibili_chapters(pages, duration)
        except Exception:
            pass

    # Fallback: try LLM-based chapter detection from already fetched subtitles
    if not chapters and subtitles_array:
        api_key = user_config.get("user_key") if user_config else None
        base_url = user_config.get("base_url") if user_config else None
        try:
            language = video_config.get("output_language", "zh")
            from app.services.prompts import PROMPT_LANGUAGE_MAP
            lang_name = PROMPT_LANGUAGE_MAP.get(language, language)
            chapters = await detect_chapters_from_subtitles(
                title=meta_video.title or "Video",
                subtitles=subtitles_array,
                language=lang_name,
                api_key=api_key,
                base_url=base_url,
                model=video_config.get("model"),
            )
        except Exception:
            pass

    return chapters


def get_chapter_field(ch, field_name: str, default: Any = None) -> Any:
    if hasattr(ch, field_name):
        return getattr(ch, field_name)
    if isinstance(ch, dict):
        return ch.get(field_name, default)
    return default


def logical_segment_video(
    subtitles_array: list,
    chapters: list,
    total_duration: float,
    step_seconds: float = 300.0,
) -> list:
    """Logical segmentation in-memory without physical files or FFmpeg slicing."""
    from typing import Any
    segments_with_subs = []
    
    # Safeguard duration
    if total_duration <= 0 and subtitles_array:
        try:
            total_duration = max(float(item.get("s", 0)) for item in subtitles_array)
        except Exception:
            total_duration = 300.0
    if total_duration <= 0:
        total_duration = 300.0
        
    # Case 1: Chapter-based segmentation
    if chapters and len(chapters) > 0:
        for i, ch in enumerate(chapters):
            start = float(get_chapter_field(ch, "start_seconds", 0))
            if i + 1 < len(chapters):
                next_ch = chapters[i + 1]
                end = float(get_chapter_field(next_ch, "start_seconds", total_duration))
            else:
                end = total_duration
            
            duration = max(0.0, end - start)
            
            # Filter subtitles in [start, end)
            seg_subs = [
                item for item in subtitles_array
                if start <= float(item.get("s", 0)) < end
            ]
            
            from app.services.video_segment import Segment
            seg = Segment(
                index=i,
                local_path="",  # No physical file
                start_seconds=start,
                duration_seconds=duration,
                chapter_title=get_chapter_field(ch, "title", f"Section {i+1}"),
            )
            segments_with_subs.append({
                "segment": seg,
                "subtitles_array": seg_subs
            })
            
    # Case 2: Fixed-duration segmentation
    else:
        # If total duration is shorter than step_seconds, just 1 segment
        if total_duration <= step_seconds:
            from app.services.video_segment import Segment
            seg = Segment(
                index=0,
                local_path="",
                start_seconds=0.0,
                duration_seconds=total_duration,
                chapter_title="",
            )
            segments_with_subs.append({
                "segment": seg,
                "subtitles_array": subtitles_array
            })
        else:
            start = 0.0
            index = 0
            while start < total_duration:
                end = min(start + step_seconds, total_duration)
                duration = end - start
                
                seg_subs = [
                    item for item in subtitles_array
                    if start <= float(item.get("s", 0)) < end
                ]
                
                from app.services.video_segment import Segment
                seg = Segment(
                    index=index,
                    local_path="",
                    start_seconds=start,
                    duration_seconds=duration,
                    chapter_title="",
                )
                segments_with_subs.append({
                    "segment": seg,
                    "subtitles_array": seg_subs
                })
                
                start = end
                index += 1
                
    return segments_with_subs


async def _run_pipeline(
    meta_video,
    video_config: dict,
    user_config: Optional[dict],
    enable_stream: bool,
):
    """Optimized pipeline: Fetch/transcribe once → LLM Outline (Phase 1) → Parallel Leaf Summarize (Phase 2) → DFS Assemble (Phase 3)."""
    task_id = video_config.get("task_id")
    api_key = user_config.get("user_key") if user_config else None
    base_url = user_config.get("base_url") if user_config else None

    # Determine final model
    from app.config import settings
    final_model = (user_config.get("model_name") if user_config else None) or video_config.get("model") or settings.openai_compatible_model

    from app.services.prompts import LANGUAGE_CODE_TO_ENGLISH_NAME
    lang_code = video_config.get("output_language", "zh")
    lang_name = LANGUAGE_CODE_TO_ENGLISH_NAME.get(lang_code, lang_code)

    # Ensure API key is selected
    from app.services._client import select_api_key
    selected_api = select_api_key(api_key)
    if not selected_api:
        raise HTTPException(status_code=400, detail="Missing API key for OpenAI-compatible provider")

    # 1. Fetch or transcribe entire video once
    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "extract_audio", "running", message="正在获取视频高精度语音文字/字幕...")

    from app.services.subtitles import fetch_subtitle
    subtitle_video_config = {
        **video_config,
        "local_path": meta_video.local_path,
        "whisper_api_key": selected_api,
        "whisper_base_url": base_url or video_config.get("whisper_base_url"),
    }
    
    subtitle_result = await fetch_subtitle(subtitle_video_config, should_show_timestamp=False)
    
    # Fallback to local whisper ASR if subtitle fetching fails for online platforms
    if (subtitle_result.get("error") or not subtitle_result.get("subtitles_array")) and video_config.get("service") in ("bilibili", "youtube"):
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "extract_audio", "running", message="无法获取在线字幕，准备通过 Whisper 提取视频语音文字...")
        fallback_config = {
            **subtitle_video_config,
            "service": "local-video",
        }
        subtitle_result = await fetch_subtitle(fallback_config, should_show_timestamp=False)

    if subtitle_result.get("error") or not subtitle_result.get("subtitles_array"):
        err_msg = subtitle_result.get("error") or "未能成功获取或识别视频的语音内容"
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "transcribe", "failed", message=err_msg)
        raise HTTPException(status_code=500, detail=err_msg)

    subtitles_array = subtitle_result.get("subtitles_array", [])
    title = meta_video.title or subtitle_result.get("title") or "Video Summary"

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "extract_audio", "completed", message="视频语音/字幕获取完成")
        update_step(task_id, "transcribe", "completed", message="视频语音转文字提取完成")
        update_step(task_id, "detect_chapters", "running", message="正在使用 LLM 分析并构建视频全局大纲树结构...")

    # Formulate full transcript with timestamps
    import re
    import asyncio
    transcript_lines = []
    for item in subtitles_array:
        s = item.get("s", 0.0)
        text = item.get("text", "")
        text = re.sub(r'^\d+(?:\.\d+)?\s*-\s*', '', text)
        transcript_lines.append(f"[{s:.1f}s] {text}")
    transcript_text = "\n".join(transcript_lines)

    # 2. Phase 1: Call robust LLM with JSON schema to get Chapter Outline and Overall Summary
    duration = meta_video.duration_seconds or (subtitles_array[-1].get("s", 0.0) if subtitles_array else 300.0)
    
    OUTLINE_SYSTEM_PROMPT = f"""
        You are an expert video content architect. Your task is to analyze the provided full transcript of a video (each line with a timestamp) and construct a highly precise, logically nested semantic outline.

        Rules:
        1. The outline must strictly reflect the actual flow and semantic structure of the video. Do not hallucinate topics.
        2. Carefully comprehense and identify the major thematic sections/chapters. If a chapter contains multiple sub‑topics, nest them inside a 'children' list.
        3. Carefully comprehense and identify 'Leaf Nodes' (which is one INDEPENDENT and INDIVISIBLE topical context range each, and will be fully transcripted later, terminal nodes where 'has_subchapters' is false. e.g. A knowledge point in a certain knowledge system, or a stage that includes multiple steps in a complete tutorial).
        4. For every Leaf Node, you MUST specify the exact starting and ending timestamp range `[start_seconds, end_seconds]` corresponding to that semantic segment. The entire video duration (from 0 to total duration) must be continuously covered by leaf nodes, with no gaps. Adjacent leaf nodes should have end_seconds equal to the next node's start_seconds (allow floating‑point tolerance <0.1s, but no missing intervals).
        5. Each leaf node should represent a self‑contained micro‑topic. Recommended minimum duration is 15 seconds, unless the segment is a very short but complete definition or data point.
        6. Handle typical speech transcription noise:
        - Ignore filler words like "um", "uh", "like", "you know", "so" when they do not carry semantic content.
        - If the speaker repeats the same idea with slightly different wording, merge it into a single semantic boundary.
        - If a sentence is cut off and rephrased, use the complete semantic unit to determine the time interval.
        7. Respond strictly in valid JSON conforming to the schema defined by the system (response_format). Do not include Markdown code fences, extra commentary, or conversational text. Output only the JSON object.
        8. Please output content using the language: {lang_name}, except for very few English proper nouns appearing in the text. / 请使用【{lang_name}】输出内容，除了文本中出现的极个别英文专有名词。

        The JSON structure is pre‑defined; you must follow the expected fields. Ensure all required fields are present and correctly typed.
    """
    
    outline_user_prompt = f"""Video Title: "{title}"
    Total Video Duration: {duration:.1f}s
    
    Transcript with Timestamps:
    {transcript_text[:120000]} # Protect context size limit
    
    Build the structured JSON outline according to the system rules and schema. Respond only in the requested JSON structure.
    """

    from app.services.openai_client import robust_llm_call
    from app.services.output_schema import OUTLINE_JSON_SCHEMA, parse_outline_json_output

    outline_data = None
    max_outline_attempts = 10
    for attempt in range(1, max_outline_attempts + 1):
        try:
            print(f"Outline generation attempt {attempt}/{max_outline_attempts}...")
            outline_raw = await robust_llm_call(
                messages=[
                    {"role": "system", "content": OUTLINE_SYSTEM_PROMPT},
                    {"role": "user", "content": outline_user_prompt},
                ],
                api_key=selected_api,
                base_url=base_url,
                model=final_model,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "chapter_outline",
                        "schema": OUTLINE_JSON_SCHEMA,
                        "strict": True,
                    },
                },
            )
            outline_data = parse_outline_json_output(outline_raw)
            if outline_data and "outline" in outline_data:
                print(f"Successfully generated and parsed structured outline on attempt {attempt}.")
                break
            else:
                raise ValueError("Parsed outline data is empty or missing 'outline' field.")
        except Exception as e:
            print(f"Warning: Outline attempt {attempt} failed: {str(e)}.")
            if attempt < max_outline_attempts:
                await asyncio.sleep(1.0)

    if not outline_data or "outline" not in outline_data:
        print("Warning: All 10 outline generation attempts failed. Falling back to basic outline.")
        outline_data = {
            "title": title,
            "overall_summary": "Video summary generated via fallback.",
            "outline": [
                {
                    "id": "node_1",
                    "title": "Full Summary",
                    "has_subchapters": False,
                    "start_seconds": 0.0,
                    "end_seconds": duration,
                }
            ]
        }

    overall_summary = outline_data.get("overall_summary", "")
    title = outline_data.get("title", title)

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "detect_chapters", "completed", message="已成功生成视频全景语义大纲树")
        update_step(task_id, "segment_video", "running", message="正在在内存中进行高保真逻辑分片规划...")

    # 3. Phase 2 Prep: Collect leaf nodes and logical segmenting in-memory
    def collect_leaf_nodes(node: dict) -> list:
        leaves = []
        if node.get("has_subchapters"):
            for child in node.get("children", []):
                leaves.extend(collect_leaf_nodes(child))
        else:
            leaves.append(node)
        return leaves

    all_leaves = []
    for item in outline_data.get("outline", []):
        all_leaves.extend(collect_leaf_nodes(item))

    if not all_leaves:
        # Fallback single leaf
        all_leaves = [{
            "id": "node_1",
            "title": "Highlights",
            "has_subchapters": False,
            "start_seconds": 0.0,
            "end_seconds": duration,
        }]

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "segment_video", "completed", message=f"已成功完成内存逻辑分片，共规划 {len(all_leaves)} 个叶子端点")
        update_step(task_id, "process_segments", "running", message=f"正在对全部分段内容进行多路高并发知识提炼 (0/{len(all_leaves)})...")

    # 4. Phase 2: Parallelized Leaf Node Summaries
    completed_leaves = 0
    failed_leaves = 0
    lock = asyncio.Lock()

    LEAF_SYSTEM_PROMPT = f"""
        You are a meticulous technical scribe. You are summarizing a specific, isolated segment of a larger video.

        Rules:
        1. Focus strictly and exclusively on the provided transcript segment. Summarize every key concept, formula, code block, definition, and specific fact mentioned.
        2. You must not skip technical details. Reproduce exactly:
        - Any numeric values, percentages, statistics (e.g., "37.2%", "10^6").
        - Formulas (use inline LaTeX, e.g., `$E=mc^2$`).
        - Code snippets (use Markdown code blocks with language annotation if known).
        - Definitional statements (e.g., "Causal convolution means that...")
        3. Output style: Write in a **knowledge‑lecture style** using natural paragraphs (single or multiple paragraphs). You may occasionally insert **small itemized fragments** (e.g., a short bullet list with `-`) to highlight a few key points within a paragraph, but the overall output MUST NOT consist entirely of bullet points or numbered lists. The default structure is prose paragraphs.
        4. If there surely are or might be transcription errors (homophones, mis‑segmented words, missing punctuation) that affect understanding:
        - If the correct word is CERTAIN, just correct them silently in the summary without calling attention to the error. Do not mention the correction or the existence of an error.
        - If the correct word is UNCERTAIN, keep the original with `[sic]` and explain the ambiguity in the note.
        5. If terminology mismatches or context ambiguities exist (not due to transcription errors), you may append a single paragraph labeled `💡 *Editor's Note*` or `💡 *Translator's Note*` at the very end. This note must be strictly limited to 1–2 concise sentences.
        6. Consistency check: Before writing, verify that the content of this segment actually matches the intended chapter title (provided in the user message). If there is a major mismatch (e.g., title says "Introduction to A" but 80% of the segment talks about B), you MUST warn in a `💡 *Editor's Note*` and suggest adjusting the outline.
        7. Your output must not contain any greetings, confirmations (e.g., "Sure, here is the summary"), titles, headers, or wrap‑up sentences. The first character of your output should be the first letter of the first paragraph (avoid using '-' at the very beginning, avoid using itemized fragment to compose the entire content). If the segment contains no substantive content (e.g., only "Um… let's move on"), output exactly: `*[Seems to have no substantive content. ]*`
        8. Please output content using the language: {lang_name}, except for very few English proper nouns appearing in the text. / 请使用【{lang_name}】输出内容，除了文本中出现的极个别英文专有名词。
    """

    async def summarize_leaf_with_progress(leaf: dict) -> tuple:
        nonlocal completed_leaves, failed_leaves
        leaf_id = leaf.get("id")
        leaf_title = leaf.get("title", "Segment")
        start_sec = float(leaf.get("start_seconds", 0.0))
        end_sec = float(leaf.get("end_seconds", duration))

        # Filter subtitles within segment range
        leaf_subs = [
            item for item in subtitles_array
            if start_sec <= float(item.get("s", 0.0)) < end_sec
        ]

        leaf_transcript_lines = []
        for item in leaf_subs:
            s = item.get("s", 0.0)
            text = item.get("text", "")
            text = re.sub(r'^\d+(?:\.\d+)?\s*-\s*', '', text)
            leaf_transcript_lines.append(f"[{s:.1f}s] {text}")
        leaf_transcript = "\n".join(leaf_transcript_lines)

        leaf_user_prompt = f"""Overall Video Title: "{title}"
        Current Segment Title: "{leaf_title}"
        Segment Time Range: {start_sec:.1f}s - {end_sec:.1f}s
        
        Segment Transcript:
        {leaf_transcript}
        
        Generate the highly detailed, fact-preserving bullet-point summary for this segment.
        """

        summary_md = ""
        max_leaf_attempts = 10
        for attempt in range(1, max_leaf_attempts + 1):
            try:
                print(f"Leaf summary attempt {attempt}/{max_leaf_attempts} for {leaf_title}...")
                summary_md = await robust_llm_call(
                    messages=[
                        {"role": "system", "content": LEAF_SYSTEM_PROMPT},
                        {"role": "user", "content": leaf_user_prompt},
                    ],
                    api_key=selected_api,
                    base_url=base_url,
                    model=final_model,
                )
                if summary_md and not summary_md.strip().startswith("*(Summary generation failed"):
                    break
                else:
                    raise ValueError("Generated summary is empty or contains failure indicators.")
            except Exception as e:
                print(f"Warning: Leaf summary attempt {attempt} failed for {leaf_title}: {str(e)}")
                if attempt == max_leaf_attempts:
                    summary_md = f"*(Summary generation failed after {max_leaf_attempts} attempts: {str(e)})*"
                else:
                    await asyncio.sleep(1.0)

        async with lock:
            if "failed" in summary_md:
                failed_leaves += 1
            else:
                completed_leaves += 1
            total_done = completed_leaves + failed_leaves
            progress = (total_done / len(all_leaves)) * 100.0

            if task_id:
                from app.services.status_tracker import update_step
                msg = f"正在分析分段音视频... 已完成 ({total_done}/{len(all_leaves)})"
                if failed_leaves > 0:
                    msg += f" (已跳过 {failed_leaves} 部分出错)"
                
                status = "running"
                if total_done == len(all_leaves):
                    status = "completed"
                    msg = f"所有 {len(all_leaves)} 个分段处理完成"
                    if failed_leaves > 0:
                        msg += f" ({completed_leaves} 成功, {failed_leaves} 失败)"
                update_step(task_id, "process_segments", status, progress=progress, message=msg)

        return leaf_id, summary_md

    # Run parallel leaf summaries
    tasks = [summarize_leaf_with_progress(leaf) for leaf in all_leaves]
    leaf_results = await asyncio.gather(*tasks)
    summaries_map = dict(leaf_results)

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "compose_summary", "running", message="正在从大纲树中进行深度优先递归编排拼装完整总结文档...")

    # 5. Phase 3: Recursive DFS Assembly in Memory (No LLM Call)
    def format_ts(seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def assemble_markdown(node: dict, summaries_map: dict, depth: int = 2) -> list:
        md_parts = []
        header_prefix = "#" * depth
        
        node_title = node.get("title", "Untitled")
        
        if node.get("has_subchapters"):
            md_parts.append(f"\n{header_prefix} {node_title}\n")
            for child in node.get("children", []):
                md_parts.extend(assemble_markdown(child, summaries_map, depth + 1))
        else:
            start = float(node.get("start_seconds", 0.0))
            ts_str = format_ts(start)
            md_parts.append(f"\n{header_prefix} {node_title} `[{ts_str}]`\n")
            
            node_id = node.get("id")
            summary_md = summaries_map.get(node_id, "*(Summary generation failed)*")
            md_parts.append(summary_md)
            
        return md_parts

    final_markdown_list = []
    
    # 5.1 Append overall summary if present
    if overall_summary:
        final_markdown_list.append("## Summary\n")
        final_markdown_list.append(f"{overall_summary}\n")
        final_markdown_list.append("## Highlights\n")

    # 5.2 Append assembled leaf nodes summaries recursively
    for chapter in outline_data.get("outline", []):
        final_markdown_list.extend(assemble_markdown(chapter, summaries_map, depth=3))

    final_markdown_text = "\n".join(final_markdown_list).strip()

    if enable_stream:
        # Stream the pre-assembled markdown as a single chunk (extremely fast and fully compatible with SSE)
        async def stream_generator():
            yield final_markdown_text
            if task_id:
                from app.services.status_tracker import update_step
                update_step(task_id, "compose_summary", "completed", message="AI 总结融合并生成完成")

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "no-cache"},
        )

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "compose_summary", "completed", message="AI 总结融合并生成完成")

    return {"result": final_markdown_text}


@router.post("/video/upload")
async def video_upload_endpoint(
    video_config: str = Form(...),
    user_config: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """Process an uploaded video: save → detect chapters → segment → summarize → compose."""
    vc = VideoConfig.model_validate_json(video_config)
    uc = UserConfig.model_validate_json(user_config) if user_config else None

    video_config_dict = vc.model_dump()
    user_config_dict = uc.model_dump() if uc else None

    # Force emoji, chapters, and remove generated timestamp text
    video_config_dict["show_emoji"] = True
    video_config_dict["respect_chapters"] = True
    video_config_dict["show_timestamp"] = False
    if user_config_dict:
        user_config_dict["should_show_timestamp"] = False

    enable_stream = video_config_dict.get("enable_stream", True)

    task_id = video_config_dict.get("task_id")
    if task_id:
        from app.services.status_tracker import init_task, update_step
        init_task(task_id, "local")
        update_step(task_id, "upload_file", "running", message=f"正在接收并保存上传文件: {file.filename}...")

    # Save uploaded file to a temp location first
    import tempfile
    import os

    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # 1. Ingest from upload
    meta_video = await ingest_from_upload(tmp_path, file.filename or "uploaded_video.mp4")
    video_config_dict["video_id"] = meta_video.video_id
    video_config_dict["service"] = "local-video"

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "upload_file", "completed", message="视频文件上传并保存成功")
        update_step(task_id, "extract_audio", "running", message="正在使用 Whisper 提取音频并转换文字...")

    return await _run_pipeline(meta_video, video_config_dict, user_config_dict, enable_stream)
