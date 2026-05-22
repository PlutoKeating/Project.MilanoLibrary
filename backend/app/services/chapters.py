"""Chapter detection from video metadata and subtitles."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Chapter:
    title: str
    start_seconds: float
    end_seconds: Optional[float] = None


# ============== YouTube chapters ==============

def _parse_youtube_chapters_from_description(description: str, duration_seconds: float) -> List[Chapter]:
    """Extract chapter markers from YouTube video description.

    YouTube chapters are typically in format:
      0:00 Intro
      1:23 Main Topic
      5:45 Conclusion
    """
    chapters: List[Chapter] = []
    # Match patterns like "0:00 Title", "01:23:45 Title", "1:23 Title"
    pattern = re.compile(
        r'^(?:\s*[-*•]?\s*)?(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$',
        re.MULTILINE,
    )
    matches = pattern.findall(description)

    for i, (ts, title) in enumerate(matches):
        start = _timestamp_to_seconds(ts)
        if start is None:
            continue
        # End is start of next chapter or video end
        end = None
        if i + 1 < len(matches):
            next_start = _timestamp_to_seconds(matches[i + 1][0])
            if next_start is not None:
                end = next_start
        elif duration_seconds and duration_seconds > start:
            end = duration_seconds
        chapters.append(Chapter(title=title.strip(), start_seconds=start, end_seconds=end))

    return chapters


# ============== Bilibili chapters ==============

def _parse_bilibili_chapters(pages: List[Dict[str, Any]], duration_seconds: float) -> List[Chapter]:
    """Extract chapters from Bilibili multi-part video pages.

    Each page has: part (title), page (number), duration (seconds)
    """
    chapters: List[Chapter] = []
    current_start = 0.0
    for page in pages:
        title = page.get("part", f"P{page.get('page', len(chapters)+1)}")
        page_duration = page.get("duration", 0)
        end = current_start + page_duration if page_duration else None
        chapters.append(Chapter(title=title.strip(), start_seconds=current_start, end_seconds=end))
        current_start = end if end else current_start + 60
    return chapters


# ============== Generic: chapters from subtitles via LLM ==============

CHAPTER_DETECTION_PROMPT = """You are a video content analyzer. Analyze the following video transcript and identify natural chapter/section boundaries.

The video title is: {title}

Transcript (with timestamps):
{transcript}

Instructions:
1. Identify the major thematic sections/chapters of this video.
2. Each chapter should represent a distinct topic or segment.
3. Use the provided timestamps to determine chapter start times.
4. Return ONLY a valid JSON array in this exact format:
[
  {{"title": "Chapter Title", "start_seconds": 0}},
  {{"title": "Next Chapter", "start_seconds": 120}}
]

Rules:
- The first chapter MUST start at 0 seconds.
- Chapter titles should be concise (2-8 words).
- Do NOT include any text outside the JSON array.
- Do NOT use markdown code blocks.
- Reply in {language} Language for chapter titles.
"""


async def detect_chapters_from_subtitles(
    title: str,
    subtitles: List[Dict[str, Any]],
    language: str = "Chinese",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> List[Chapter]:
    """Use LLM to detect chapters from subtitle content.

    Falls back to time-based segmentation if LLM fails.
    """
    from app.services._client import create_client
    from app.config import settings
    import json

    # Build transcript with timestamps for LLM context
    transcript_lines = []
    for item in subtitles[:200]:  # Limit context to avoid token overflow
        s = item.get("s", item.get("start", 0))
        text = item.get("text", "")
        # Strip existing timestamp prefix if present
        text = re.sub(r'^\d+(?:\.\d+)?\s*-\s*', '', text)
        transcript_lines.append(f"[{s}s] {text}")

    transcript = "\n".join(transcript_lines)

    prompt = CHAPTER_DETECTION_PROMPT.format(
        title=title,
        transcript=transcript[:8000],  # Limit length
        language=language,
    )

    client = create_client(base_url)
    client.api_key = api_key or settings.openai_api_key or settings.openai_compatible_api_key or ""
    final_model = model or settings.openai_compatible_model

    chapters_data = None
    max_chapter_attempts = 10
    
    for attempt in range(1, max_chapter_attempts + 1):
        try:
            print(f"Subtitles chapter detection attempt {attempt}/{max_chapter_attempts}...")
            response = await client.chat.completions.create(
                model=final_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.2,
            )
            text = response.choices[0].message.content or ""
            # Strip markdown code blocks if present
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```\s*$', '', text)
            data = json.loads(text)
            
            if isinstance(data, list) and len(data) > 0:
                chapters_data = data
                print(f"Successfully detected chapters JSON on attempt {attempt}.")
                break
            else:
                raise ValueError("Parsed data is not a non-empty list.")
        except Exception as e:
            print(f"Warning: Chapter detection attempt {attempt} failed: {str(e)}.")
            if attempt < max_chapter_attempts:
                await asyncio.sleep(1.0)
                
    if chapters_data is not None:
        chapters: List[Chapter] = []
        for i, item in enumerate(chapters_data):
            start = float(item.get("start_seconds", 0))
            end = None
            if i + 1 < len(chapters_data):
                end = float(chapters_data[i + 1].get("start_seconds", start))
            chapters.append(Chapter(
                title=str(item.get("title", f"Section {i+1}")),
                start_seconds=start,
                end_seconds=end,
            ))
        return chapters
    else:
        # Fallback: divide into ~5 equal parts
        if not subtitles:
            return []
        total_duration = subtitles[-1].get("s", subtitles[-1].get("end", 0))
        if not total_duration or total_duration <= 0:
            return []
        num_chapters = max(3, min(8, int(total_duration / 300)))
        step = total_duration / num_chapters
        return [
            Chapter(
                title=f"Part {i+1}",
                start_seconds=i * step,
                end_seconds=(i + 1) * step if i < num_chapters - 1 else None,
            )
            for i in range(num_chapters)
        ]


# ============== Utilities ==============

def _timestamp_to_seconds(ts: str) -> Optional[float]:
    """Convert 'MM:SS' or 'HH:MM:SS' to seconds."""
    parts = ts.strip().split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    return None


def assign_subtitles_to_chapters(
    subtitles: List[Dict[str, Any]],
    chapters: List[Chapter],
) -> Dict[int, List[Dict[str, Any]]]:
    """Assign each subtitle item to its corresponding chapter.

    Returns: {chapter_index: [subtitle_items]}
    """
    result: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(len(chapters))}
    for item in subtitles:
        s = item.get("s", item.get("start", 0))
        # Find which chapter this subtitle belongs to
        chapter_idx = 0
        for i, ch in enumerate(chapters):
            if s >= ch.start_seconds:
                chapter_idx = i
            else:
                break
        result[chapter_idx].append(item)
    return result
