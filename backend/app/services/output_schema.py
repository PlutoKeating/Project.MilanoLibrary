"""Structured output schemas and validation for LLM summaries."""

import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class BulletPoint:
    emoji: Optional[str]
    text: str
    timestamp_seconds: Optional[float] = None
    children: Optional[List["BulletPoint"]] = None


@dataclass
class ChapterSummary:
    chapter_title: str
    chapter_start_seconds: float
    bullets: List[BulletPoint]


@dataclass
class VideoSummary:
    overall_summary: str
    chapters: List[ChapterSummary]

    def to_markdown(
        self,
        show_timestamp: bool = False,
        show_emoji: bool = True,
    ) -> str:
        """Convert structured summary to Markdown string."""
        lines: List[str] = []

        # Overall summary
        if self.overall_summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(self.overall_summary)
            lines.append("")

        # Highlights / Chapters
        lines.append("## Highlights")
        lines.append("")

        for ch in self.chapters:
            # Chapter heading
            ts_prefix = ""
            if show_timestamp and ch.chapter_start_seconds is not None:
                ts_str = _format_timestamp(ch.chapter_start_seconds)
                ts_prefix = f"[{ts_str}] "
            lines.append(f"### {ts_prefix}{ch.chapter_title}")
            lines.append("")

            for bp in ch.bullets:
                lines.extend(_bullet_to_markdown_lines(bp, 0, show_timestamp, show_emoji))

            lines.append("")

        return "\n".join(lines).strip()


def _bullet_to_markdown_lines(
    bp: BulletPoint,
    depth: int,
    show_timestamp: bool,
    show_emoji: bool,
) -> List[str]:
    indent = "    " * depth
    parts: List[str] = [indent, "- "]

    if show_timestamp and bp.timestamp_seconds is not None:
        parts.append(f"{bp.timestamp_seconds:.1f} - ")

    if show_emoji and bp.emoji:
        parts.append(f"{bp.emoji} ")

    parts.append(bp.text)
    lines = ["".join(parts)]

    if bp.children:
        for child in bp.children:
            lines.extend(_bullet_to_markdown_lines(child, depth + 1, show_timestamp, show_emoji))

    return lines


def _format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


# ============== JSON Schema for LLM structured output ==============

SUMMARY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_summary": {
            "type": "string",
            "description": "A one-sentence summary of the entire video",
        },
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chapter_title": {
                        "type": "string",
                        "description": "Title of this chapter/section",
                    },
                    "bullets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "emoji": {
                                    "type": ["string", "null"],
                                    "description": "An appropriate emoji for this point, or null",
                                },
                                "text": {
                                    "type": "string",
                                    "description": "The bullet point text content",
                                },
                                "children": {
                                    "type": ["array", "null"],
                                    "items": {"$ref": "#/$defs/bullet"},
                                    "description": "Nested child bullet points, or null",
                                },
                            },
                            "required": ["text"],
                        },
                    },
                },
                "required": ["chapter_title", "bullets"],
            },
        },
    },
    "required": ["overall_summary", "chapters"],
    "$defs": {
        "bullet": {
            "type": "object",
            "properties": {
                "emoji": {"type": ["string", "null"]},
                "text": {"type": "string"},
                "children": {
                    "type": ["array", "null"],
                    "items": {"$ref": "#/$defs/bullet"},
                },
            },
            "required": ["text"],
        }
    },
}


def parse_llm_json_output(text: str) -> Optional[VideoSummary]:
    """Parse and validate LLM JSON output into VideoSummary.

    Handles various LLM output formats including markdown code blocks.
    """
    # Strip markdown code blocks
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        else:
            return None

    return _dict_to_video_summary(data)


def _dict_to_video_summary(data: Dict[str, Any]) -> Optional[VideoSummary]:
    """Convert parsed dict to VideoSummary dataclass."""
    try:
        chapters: List[ChapterSummary] = []
        for ch in data.get("chapters", []):
            bullets: List[BulletPoint] = []
            for bp in ch.get("bullets", []):
                bullets.append(_dict_to_bullet(bp))
            chapters.append(ChapterSummary(
                chapter_title=ch.get("chapter_title", "Untitled"),
                chapter_start_seconds=float(ch.get("chapter_start_seconds", 0)),
                bullets=bullets,
            ))

        return VideoSummary(
            overall_summary=data.get("overall_summary", ""),
            chapters=chapters,
        )
    except Exception:
        return None


def _dict_to_bullet(data: Dict[str, Any]) -> BulletPoint:
    children = None
    if data.get("children"):
        children = [_dict_to_bullet(c) for c in data["children"]]
    return BulletPoint(
        emoji=data.get("emoji") or None,
        text=data.get("text", ""),
        timestamp_seconds=data.get("timestamp_seconds"),
        children=children or None,
    )


# ============== Fallback: parse free-text Markdown to structured ==============

def parse_markdown_to_structure(text: str) -> VideoSummary:
    """Best-effort parse legacy/free-text Markdown output into VideoSummary.

    Used as fallback when structured JSON output fails.
    """
    lines = text.strip().split("\n")
    overall_summary = ""
    chapters: List[ChapterSummary] = []
    current_chapter: Optional[ChapterSummary] = None
    current_bullets: List[BulletPoint] = []
    bullet_stack: List[tuple] = []  # (depth, BulletPoint)

    in_summary = False
    in_highlights = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            continue

        # Detect sections
        if line.startswith("## Summary"):
            in_summary = True
            in_highlights = False
            continue
        if line.startswith("## Highlights"):
            in_summary = False
            in_highlights = True
            if current_chapter and current_bullets:
                current_chapter.bullets = current_bullets
                chapters.append(current_chapter)
            current_chapter = None
            current_bullets = []
            bullet_stack = []
            continue

        # Chapter heading (### or ##)
        if line.startswith("### ") or (line.startswith("## ") and in_highlights):
            if current_chapter and current_bullets:
                current_chapter.bullets = current_bullets
                chapters.append(current_chapter)
            title = line.lstrip("# ").strip()
            # Try extract timestamp from [MM:SS] or [HH:MM:SS]
            ts_match = re.search(r'^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)', title)
            start_seconds = 0.0
            if ts_match:
                start_seconds = _parse_timestamp_str(ts_match.group(1)) or 0.0
                title = ts_match.group(2)
            current_chapter = ChapterSummary(
                chapter_title=title,
                chapter_start_seconds=start_seconds,
                bullets=[],
            )
            current_bullets = []
            bullet_stack = []
            continue

        # Overall summary text
        if in_summary and not line.startswith("#"):
            overall_summary = (overall_summary + " " + line).strip() if overall_summary else line
            continue

        # Bullet points
        if in_highlights:
            bullet = _parse_bullet_line(line)
            if bullet:
                depth = _get_indent_depth(raw_line)
                if depth == 0:
                    current_bullets.append(bullet)
                    bullet_stack = [(0, bullet)]
                else:
                    # Find parent
                    parent = None
                    for d, b in reversed(bullet_stack):
                        if d < depth:
                            parent = b
                            break
                    if parent:
                        if parent.children is None:
                            parent.children = []
                        parent.children.append(bullet)
                    else:
                        current_bullets.append(bullet)
                    bullet_stack.append((depth, bullet))

    # Finalize last chapter
    if current_chapter and current_bullets:
        current_chapter.bullets = current_bullets
        chapters.append(current_chapter)

    # If no chapters detected, create a single default chapter
    if not chapters and current_bullets:
        chapters.append(ChapterSummary(
            chapter_title="Highlights",
            chapter_start_seconds=0.0,
            bullets=current_bullets,
        ))

    return VideoSummary(overall_summary=overall_summary, chapters=chapters)


def _parse_bullet_line(line: str) -> Optional[BulletPoint]:
    """Parse a single bullet line like '- 12.3 - 🎬 Some text'."""
    # Strip leading bullet markers and whitespace
    cleaned = re.sub(r'^[\s]*[-*•\d]+[.\)]?\s*', '', line).strip()
    if not cleaned:
        return None

    # Extract timestamp: "12.3 - " or "12:30 - "
    ts_match = re.match(r'^(\d+(?:\.\d+)?)\s*-\s*(.*)$', cleaned)
    timestamp = None
    if ts_match:
        try:
            timestamp = float(ts_match.group(1))
            cleaned = ts_match.group(2).strip()
        except ValueError:
            pass

    # Extract emoji
    emoji = None
    emoji_match = re.match(
        r'^([\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF])\s+(.+)$',
        cleaned,
    )
    if emoji_match:
        emoji = emoji_match.group(1)
        cleaned = emoji_match.group(2)

    return BulletPoint(emoji=emoji, text=cleaned, timestamp_seconds=timestamp)


def _get_indent_depth(line: str) -> int:
    """Calculate indentation depth (4 spaces = 1 level)."""
    leading = len(line) - len(line.lstrip())
    return leading // 4


def _parse_timestamp_str(ts: str) -> Optional[float]:
    parts = ts.split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return None


# ============== Phase 1: Video Outline Schema ==============

OUTLINE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Overall video title"
        },
        "overall_summary": {
            "type": "string",
            "description": "A concise, high-level paragraph summary of the entire video content"
        },
        "outline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique ID of this node, e.g., 'node_1'"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of this outline item"
                    },
                    "has_subchapters": {
                        "type": "boolean",
                        "description": "True if this node contains nested subchapters, False if it is a terminal leaf node"
                    },
                    "children": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "has_subchapters": {"type": "boolean"},
                                "start_seconds": {"type": "number"},
                                "end_seconds": {"type": "number"}
                            },
                            "required": ["id", "title", "has_subchapters"]
                        },
                        "description": "List of subchapters, present if has_subchapters is True"
                    },
                    "start_seconds": {
                        "type": "number",
                        "description": "Start timestamp in seconds, present if has_subchapters is False"
                    },
                    "end_seconds": {
                        "type": "number",
                        "description": "End timestamp in seconds, present if has_subchapters is False"
                    }
                },
                "required": ["id", "title", "has_subchapters"]
            }
        }
    },
    "required": ["title", "overall_summary", "outline"]
}


def parse_outline_json_output(text: str) -> Optional[dict]:
    """Parse and validate LLM output into Phase 1 structured outline dictionary."""
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)

    try:
        data = json.loads(text)
        if "outline" in data and "title" in data:
            return data
    except Exception:
        # Try to extract JSON from text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if "outline" in data and "title" in data:
                    return data
            except Exception:
                pass
    return None
