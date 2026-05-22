import uuid
import shutil
import re
import subprocess
from typing import Optional
from pathlib import Path
from pydantic import BaseModel

import imageio_ffmpeg


STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
VIDEO_DIR = STORAGE_DIR / "videos"

# Ensure storage dirs exist
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


def _probe_media_duration(path: str) -> Optional[float]:
    """Get media duration in seconds using ffmpeg."""
    result = subprocess.run(
        [FFMPEG_EXE, "-i", path],
        capture_output=True, text=True,
    )
    m = re.search(r"Duration:\s+(\d+):(\d+):([\d.]+)", result.stderr)
    if m:
        h, mi, s = m.groups()
        return int(h) * 3600 + int(mi) * 60 + float(s)
    return None


class MetaVideo(BaseModel):
    video_id: str
    source_type: str  # "link" | "upload"
    original_url: Optional[str] = None
    local_path: str
    title: Optional[str] = None
    duration_seconds: Optional[float] = None
    format: str


async def ingest_from_upload(file_path: str, original_filename: str) -> MetaVideo:
    """Move an uploaded file into local storage and return MetaVideo."""
    video_id = uuid.uuid4().hex[:16]
    out_dir = VIDEO_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(original_filename).suffix.lstrip(".") or "mp4"
    local_path = str(out_dir / f"original.{ext}")
    shutil.move(file_path, local_path)

    duration = _probe_media_duration(local_path)

    return MetaVideo(
        video_id=video_id,
        source_type="upload",
        original_url=None,
        local_path=local_path,
        title=Path(original_filename).stem,
        duration_seconds=duration,
        format=ext,
    )
