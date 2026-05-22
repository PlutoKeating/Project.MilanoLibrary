import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.video_segment import Segment
from app.services.openai_client import generate_summary


class SegmentResult(BaseModel):
    segment: Segment
    subtitles_array: Optional[List[Dict[str, Any]]] = None
    ai_summary: Optional[str] = None
    error: Optional[str] = None


async def process_single_segment(
    seg_item: dict,
    video_config: dict,
    user_config: Optional[dict],
    chapters: Optional[List[dict]],
    total_segments: int,
) -> SegmentResult:
    seg = seg_item["segment"]
    seg_subs = seg_item["subtitles_array"]
    task_id = video_config.get("task_id")

    # Build segment-specific video config
    seg_video_config = {
        **video_config,
        "video_id": f"{video_config.get('video_id', 'seg')}_{seg.index}",
        "title": video_config.get("metadata", {}).get("title", "Video"),
        "subtitles_array": seg_subs,  # Pass pre-sliced subtitles directly
        "description_text": None,
    }

    # If this segment belongs to a chapter, pass chapter context
    seg_chapters = None
    if seg.chapter_title:
        seg_chapters = [{
            "title": seg.chapter_title,
            "start_seconds": seg.start_seconds,
        }]
    elif chapters and seg.index < len(chapters):
        seg_chapters = [chapters[seg.index]]

    try:
        summary_text = await generate_summary(
            seg_video_config,
            user_config,
            chapters=seg_chapters,
            use_structured_output=False,  # Segments use text mode for simpler merging
        )

        if summary_text.startswith("Error:"):
            error_msg = summary_text.replace("Error: ", "")
            return SegmentResult(segment=seg, subtitles_array=None, ai_summary=None, error=error_msg)

        # Adjust timestamps in summary if timestamp mode is on
        should_show_timestamp = (
            user_config.get("should_show_timestamp", False) if user_config else False
        )
        if should_show_timestamp and seg.start_seconds > 0:
            summary_text = _offset_timestamps(summary_text, seg.start_seconds)

        return SegmentResult(
            segment=seg,
            subtitles_array=None,
            ai_summary=summary_text,
        )
    except Exception as e:
        return SegmentResult(segment=seg, subtitles_array=None, ai_summary=None, error=str(e))


async def process_segments(
    segments_with_subs: List[dict],
    video_config: dict,
    user_config: Optional[dict],
    chapters: Optional[List[dict]] = None,
) -> List[SegmentResult]:
    """Process each segment through the subtitle + AI pipeline in parallel.

    Each item in segments_with_subs is a dict: {"segment": Segment, "subtitles_array": list}
    """
    task_id = video_config.get("task_id")
    total_segments = len(segments_with_subs)

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "process_segments", "running", progress=0.0, message=f"正在分析分段音视频... (0/{total_segments})")

    # Real-time progress tracking under parallel execution
    completed_count = 0
    failed_count = 0
    lock = asyncio.Lock()

    async def run_task_with_progress(item):
        nonlocal completed_count, failed_count
        res = await process_single_segment(item, video_config, user_config, chapters, total_segments)
        
        async with lock:
            if res.ai_summary is not None:
                completed_count += 1
            else:
                failed_count += 1
                
            total_done = completed_count + failed_count
            progress = (total_done / total_segments) * 100.0
            
            if task_id:
                from app.services.status_tracker import update_step
                msg = f"正在分析分段音视频... 已完成 ({total_done}/{total_segments})"
                if failed_count > 0:
                    msg += f" (已跳过 {failed_count} 部分出错)"
                
                status = "running"
                if total_done == total_segments:
                    status = "completed"
                    msg = f"所有 {total_segments} 个分段处理完成"
                    if failed_count > 0:
                        msg += f" ({completed_count} 成功, {failed_count} 失败)"
                update_step(task_id, "process_segments", status, progress=progress, message=msg)
                
        return res

    # Run all segment summarizations in parallel using asyncio.gather
    tasks = [
        run_task_with_progress(item)
        for item in segments_with_subs
    ]
    results = await asyncio.gather(*tasks)

    return list(results)


def _offset_timestamps(text: str, offset_seconds: float) -> str:
    """Add offset to numeric timestamps at start of bullet points.

    Looks for patterns like:
      - 12.3 - some text
      - 45 - some text
    """
    import re

    def repl(match):
        prefix = match.group(1)
        ts = float(match.group(2))
        new_ts = ts + offset_seconds
        return f"{prefix}{new_ts:.1f} -"

    # Match bullet start with a number (int or float)
    return re.sub(r"^(\s*[-*]?\s*)(\d+(?:\.\d+)?)\s+-", repl, text, flags=re.MULTILINE)
