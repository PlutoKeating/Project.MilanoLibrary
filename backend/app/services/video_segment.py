import os
import subprocess
import asyncio
from typing import List
from pathlib import Path
from pydantic import BaseModel

import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
SEGMENT_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "segments"


class Segment(BaseModel):
    index: int
    local_path: str
    start_seconds: float
    duration_seconds: float
    chapter_title: str = ""  # Optional chapter name for context


async def segment_video(
    video_path: str,
    video_id: str,
    step_seconds: float = 60.0,
    chapters: List[dict] = None,
) -> List[Segment]:
    """Split video into segments.

    Priority:
    1. If chapters are provided, segment by chapter boundaries.
    2. Otherwise, use fixed-duration segmentation (default 60s).
    3. Videos shorter than step_seconds are NOT split.
    """
    out_dir = SEGMENT_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Probe duration
    import asyncio
    process = await asyncio.create_subprocess_exec(
        FFMPEG_EXE, "-i", video_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    import re
    m = re.search(r"Duration:\s+(\d+):(\d+):([\d.]+)", stderr.decode())
    if not m:
        return [Segment(
            index=0,
            local_path=video_path,
            start_seconds=0.0,
            duration_seconds=0.0,
        )]

    h, mi, s = m.groups()
    total_duration = int(h) * 3600 + int(mi) * 60 + float(s)

    # If chapters provided, segment by chapter boundaries
    if chapters and len(chapters) > 0:
        return await _segment_by_chapters(video_path, video_id, out_dir, chapters, total_duration)

    # Fixed-duration segmentation
    if total_duration <= step_seconds:
        return [Segment(
            index=0,
            local_path=video_path,
            start_seconds=0.0,
            duration_seconds=total_duration,
        )]

    segments: List[Segment] = []
    index = 0
    start = 0.0

    while start < total_duration:
        duration = min(step_seconds, total_duration - start)
        seg_path = str(out_dir / f"segment_{index:03d}.mp4")

        cmd = [
            FFMPEG_EXE,
            "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", video_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            seg_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        if process.returncode != 0:
            raise Exception("FFmpeg segment extraction failed")

        segments.append(Segment(
            index=index,
            local_path=seg_path,
            start_seconds=start,
            duration_seconds=duration,
        ))

        start += step_seconds
        index += 1

    return segments


async def _segment_by_chapters(
    video_path: str,
    video_id: str,
    out_dir: Path,
    chapters: List[dict],
    total_duration: float,
) -> List[Segment]:
    """Segment video by chapter boundaries."""
    segments: List[Segment] = []

    for i, ch in enumerate(chapters):
        start = float(ch.get("start_seconds", 0))
        # End is start of next chapter or video end
        if i + 1 < len(chapters):
            end = float(chapters[i + 1].get("start_seconds", total_duration))
        else:
            end = total_duration

        duration = max(0, end - start)
        if duration <= 0:
            continue

        seg_path = str(out_dir / f"segment_{i:03d}.mp4")

        cmd = [
            FFMPEG_EXE,
            "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", video_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            seg_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        if process.returncode != 0:
            raise Exception("FFmpeg segment extraction failed")

        segments.append(Segment(
            index=i,
            local_path=seg_path,
            start_seconds=start,
            duration_seconds=duration,
            chapter_title=ch.get("title", f"Section {i+1}"),
        ))

    return segments
