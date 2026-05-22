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
            "a separate section. Do NOT merge chapters together. "
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
        f"Your task is to seamlessly combine these adjacent notes into a single, cohesive Markdown document in {en_language}. "
        f"Retain ALL original markdown details, including deeply nested bullet points and specific facts. "
        f"You may smooth out transitions and remove edge duplicates between segments, but you MUST NOT summarize, "
        f"abbreviate, or reduce the length of the extracted knowledge. Every specific detail from the input must be preserved in the final output."
    )


def _build_composer_user_prompt(title: str, segment_summaries: List[str], video_config: dict, chapters: Optional[List[dict]] = None) -> str:
    language = video_config.get("output_language", "zh")
    language_name = prompts.LANGUAGE_CODE_TO_ENGLISH_NAME.get(language, language)
    show_emoji = video_config.get("show_emoji", True)

    emoji_template_text = "[Emoji] " if show_emoji else ""

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
            "Use ### Chapter Title for each chapter section. Do NOT flatten into a single list.\n\n"
        )

    prompt = (
        f"Your output should use the following template:\n## Summary\n## Highlights\n"
        f"### Chapter Title (if applicable)\n"
        f"- {emoji_template_text}Bulletpoint\n"
        f"    - Child points (if applicable)\n\n"
        f"{chapter_instruction}"
        f"Your task is to merge the following segment notes into a single coherent document. "
        f"Ensure every specific detail, example, or definition mentioned is fully preserved. "
        f"Do NOT summarize or omit any information from the segments. "
        f"Use the text above: {{Title}}.\n\nReply in {language_name} Language."
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

    # Try structured output first
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
    except Exception:
        pass

    # Fallback to text mode
    try:
        response = await client.chat.completions.create(
            model=final_model,
            messages=messages,
            max_tokens=max_tokens,
            stream=False,
        )
        text = response.choices[0].message.content or ""
        if text.startswith("\n\n"):
            text = text[2:]

        # Try to parse and re-format
        parsed = parse_llm_json_output(text)
        if parsed:
            should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False
            text = parsed.to_markdown(
                show_timestamp=should_show_timestamp,
                show_emoji=video_config.get("show_emoji", True),
            )
        else:
            parsed_md = parse_markdown_to_structure(text)
            if parsed_md and len(parsed_md.chapters) > 0:
                should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False
                formatted = parsed_md.to_markdown(
                    show_timestamp=should_show_timestamp,
                    show_emoji=video_config.get("show_emoji", True),
                )
                if formatted and len(formatted) > len(text) * 0.5:
                    text = formatted

        return text
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
        stream = await client.chat.completions.create(
            model=final_model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    except Exception as e:
        try:
            response = await client.chat.completions.create(
                model=final_model,
                messages=messages,
                max_tokens=max_tokens,
                stream=False,
            )
            text = response.choices[0].message.content or ""
            if text.startswith("\n\n"):
                text = text[2:]

            # Try to parse and re-format
            parsed = parse_llm_json_output(text)
            if parsed:
                should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False
                text = parsed.to_markdown(
                    show_timestamp=should_show_timestamp,
                    show_emoji=video_config.get("show_emoji", True),
                )
            else:
                parsed_md = parse_markdown_to_structure(text)
                if parsed_md and len(parsed_md.chapters) > 0:
                    should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False
                    formatted = parsed_md.to_markdown(
                        show_timestamp=should_show_timestamp,
                        show_emoji=video_config.get("show_emoji", True),
                    )
                    if formatted and len(formatted) > len(text) * 0.5:
                        text = formatted

            yield text
        except Exception as fallback_e:
            yield f"Error: {str(fallback_e)}"
