from typing import List, Optional, AsyncGenerator
from app.config import settings
from app.services import prompts
from app.services._client import select_api_key, create_client
from app.services.segment_processor import SegmentResult
from app.services.output_schema import (
    SUMMARY_JSON_SCHEMA,
    parse_llm_json_output,
    parse_markdown_to_structure,
)


def _build_composer_system_prompt(language: str, use_chapters: bool = False, metadata: Optional[dict] = None) -> str:
    en_language = prompts.PROMPT_LANGUAGE_MAP.get(language, language)

    chapter_instruction = ""
    if use_chapters:
        chapter_instruction = (
            "The input contains detailed knowledge extractions from different chapters/sections of the same video. "
            "You MUST preserve the chapter structure in your output. Each chapter should remain "
            "a separate entry in the 'chapters' array. Do NOT merge chapters together. "
        )
    else:
        chapter_instruction = (
            "The input contains detailed knowledge extractions from consecutive segments of the same video. "
        )

    metadata_instruction = ""
    if metadata:
        uploader = metadata.get("uploader", "")
        description = metadata.get("description", "")
        title = metadata.get("title", "")
        metadata_parts = []
        if title:
            metadata_parts.append(f"Video Title: {title}")
        if uploader:
            metadata_parts.append(f"Uploader/博主昵称: {uploader}")
        if description:
            metadata_parts.append(f"Video Description/平台简介: {description}")
        if metadata_parts:
            metadata_instruction = (
                f"\n\nVideo Metadata context:\n"
                + "\n".join(metadata_parts) + "\n\n"
            )

    return (
        f"You are a meticulous content editor. {chapter_instruction}"
        f"{metadata_instruction}"
        f"Your task is to seamlessly combine these adjacent notes into a single, cohesive structure in {en_language}. "
        f"Retain ALL original details, including deeply nested bullet points and specific facts. "
        f"You may smooth out transitions and remove edge duplicates between segments, but you MUST NOT summarize, "
        f"abbreviate, or reduce the length of the extracted knowledge. Every specific detail from the input must be preserved in the final output. "
        f"Output MUST be valid JSON conforming to the provided schema."
    )


def _build_composer_user_prompt(title: str, segment_summaries: List[str], video_config: dict, chapters: Optional[List[dict]] = None) -> str:
    language = video_config.get("output_language", "zh")
    language_name = prompts.LANGUAGE_CODE_TO_ENGLISH_NAME.get(language, language)
    show_emoji = video_config.get("show_emoji", True)

    # Build segments text with chapter context if available
    segments_text_parts = []
    for i, s in enumerate(segment_summaries):
        if not s:
            continue
        header = f"### Segment {i + 1}"
        if chapters and i < len(chapters):
            ch_title = chapters[i].get("title", "")
            if ch_title:
                header = f"### Chapter: {ch_title}"
        segments_text_parts.append(f"{header}\n{s}")

    segments_text = "\n\n".join(segments_text_parts)

    chapter_instruction = ""
    if chapters and len(chapters) > 0:
        chapter_instruction = (
            "IMPORTANT: The input is organized by chapters. Your output MUST also be organized by chapters. "
            "Output each chapter as a separate entry in the 'chapters' array.\n\n"
        )

    prompt = (
        f"1. Provide a one-sentence overall_summary of the entire video based on the segment summaries.\n"
        f"2. Organize the merged knowledge into chapters/sections.\n"
        f"3. Each chapter should have a chapter_title.\n"
        f"4. Each bullet point should have:\n"
        f"   - text: the highly detailed extracted knowledge point\n"
        f"   - emoji: {'an appropriate emoji' if show_emoji else 'null'}\n"
        f"   - children: nested bullet points if sub-concepts exist\n"
        f"5. {chapter_instruction}"
        f"Your task is to merge the following segment notes into a single coherent structure. "
        f"Ensure every specific detail, example, or definition mentioned is fully preserved. "
        f"Do NOT summarize or omit any information from the segments. "
        f"Reply in {language_name} Language.\n"
        f"Output MUST be valid JSON only, conforming to the schema."
    )

    return f'Title: "{title}"\n\nSegment Summaries:\n{segments_text}\n\nInstructions: {prompt}'


async def compose_summary(
    title: str,
    segment_results: List[SegmentResult],
    video_config: dict,
    user_config: Optional[dict],
    chapters: Optional[List[dict]] = None,
) -> str:
    """Merge all segment summaries into a final Markdown document via AI."""
    user_key = user_config.get("user_key") if user_config else None
    base_url = user_config.get("base_url") if user_config else None
    model_name = user_config.get("model_name") if user_config else None

    api_key = select_api_key(user_key)
    if not api_key:
        return "Error: Missing API key for OpenAI-compatible provider"

    summaries = [r.ai_summary for r in segment_results if r.ai_summary]
    if not summaries:
        errors = [r.error for r in segment_results if r.error]
        if errors:
            unique_errors = list(dict.fromkeys(errors))
            first_error = unique_errors[0]
            if first_error.startswith("501::"):
                first_error = first_error[5:]
            return f"Error: 501::{first_error}"
        return "Error: No content generated from any segment"

    if len(summaries) == 1:
        return summaries[0]

    system_prompt = _build_composer_system_prompt(
        language=video_config.get("output_language", "zh"),
        use_chapters=bool(chapters),
        metadata=video_config.get("metadata"),
    )
    user_prompt = _build_composer_user_prompt(title, summaries, video_config, chapters)

    final_model = model_name or video_config.get("model") or settings.openai_compatible_model
    max_tokens = 8192

    client = create_client(base_url)
    client.api_key = api_key

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await client.chat.completions.create(
            model=final_model,
            messages=messages,
            max_tokens=max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "video_summary",
                    "schema": SUMMARY_JSON_SCHEMA,
                    "strict": True,
                },
            },
        )
        text = response.choices[0].message.content or ""
        parsed = parse_llm_json_output(text)
        if parsed:
            should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False
            return parsed.to_markdown(
                show_timestamp=should_show_timestamp,
                show_emoji=video_config.get("show_emoji", True),
            )
        else:
            raise Exception("Failed to parse LLM structured composer output as valid video summary JSON")
    except Exception as e:
        return f"Error: {str(e)}"


async def compose_summary_stream(
    title: str,
    segment_results: List[SegmentResult],
    video_config: dict,
    user_config: Optional[dict],
    chapters: Optional[List[dict]] = None,
) -> AsyncGenerator[str, None]:
    """Stream the final composed Markdown document."""
    user_key = user_config.get("user_key") if user_config else None
    base_url = user_config.get("base_url") if user_config else None
    model_name = user_config.get("model_name") if user_config else None

    api_key = select_api_key(user_key)
    if not api_key:
        yield "Error: Missing API key for OpenAI-compatible provider"
        return

    summaries = [r.ai_summary for r in segment_results if r.ai_summary]
    if not summaries:
        errors = [r.error for r in segment_results if r.error]
        if errors:
            unique_errors = list(dict.fromkeys(errors))
            first_error = unique_errors[0]
            if first_error.startswith("501::"):
                first_error = first_error[5:]
            yield f"Error: 501::{first_error}"
        else:
            yield "Error: No content generated from any segment"
        return

    if len(summaries) == 1:
        yield summaries[0]
        return

    system_prompt = _build_composer_system_prompt(
        language=video_config.get("output_language", "zh"),
        use_chapters=bool(chapters),
        metadata=video_config.get("metadata"),
    )
    user_prompt = _build_composer_user_prompt(title, summaries, video_config, chapters)

    final_model = model_name or video_config.get("model") or settings.openai_compatible_model
    max_tokens = 8192

    client = create_client(base_url)
    client.api_key = api_key

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await client.chat.completions.create(
            model=final_model,
            messages=messages,
            max_tokens=max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "video_summary",
                    "schema": SUMMARY_JSON_SCHEMA,
                    "strict": True,
                },
            },
        )
        text = response.choices[0].message.content or ""
        parsed = parse_llm_json_output(text)
        if parsed:
            should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False
            markdown = parsed.to_markdown(
                show_timestamp=should_show_timestamp,
                show_emoji=video_config.get("show_emoji", True),
            )
            yield markdown
        else:
            raise Exception("Failed to parse LLM structured composer output as valid video summary JSON")
    except Exception as e:
        yield f"Error: {str(e)}"

