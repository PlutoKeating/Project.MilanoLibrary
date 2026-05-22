from typing import Optional, AsyncGenerator
import asyncio
import random
from app.config import settings
from app.services import prompts
from app.services._client import select_api_key, create_client
from app.services.cache import get_cache_id, get_cached_result, set_cached_result
from app.services.output_schema import (
    SUMMARY_JSON_SCHEMA,
    parse_llm_json_output,
    parse_markdown_to_structure,
    VideoSummary,
)


async def robust_llm_call(
    messages: list,
    api_key: str,
    base_url: Optional[str],
    model: str,
    response_format: Optional[dict] = None,
    max_retries: int = 5,
    initial_delay: float = 1.0,
) -> str:
    """Execute an LLM call with exponential backoff and randomized jitter."""
    client = create_client(base_url)
    client.api_key = api_key
    
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": 4096 if response_format else 8192,
                "stream": False,
            }
            if response_format:
                kwargs["response_format"] = response_format
                
            response = await client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            last_exception = e
            # Exponential backoff with jitter (delay * (1.5 + [0, 1]))
            sleep_time = delay * (1.5 + random.random())
            print(f"Warning: LLM call failed (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {sleep_time:.2f}s...")
            await asyncio.sleep(sleep_time)
            delay *= 2  # Double the base delay for exponential backoff
            
    # Raise exception if all retries failed
    raise Exception(f"LLM call failed after {max_retries} attempts. Final error: {str(last_exception)}")


def build_user_prompt(title: str, transcript: str, video_config: dict, should_show_timestamp: bool, chapters: Optional[list] = None) -> str:
    if should_show_timestamp:
        return prompts.get_user_subtitle_with_timestamp_prompt(title, transcript, video_config, chapters)
    return prompts.get_user_subtitle_prompt(title, transcript, video_config, chapters)


def get_small_size_transcripts(new_text_data: list, old_text_data: list) -> str:
    seen = set()
    merged = []
    for item in new_text_data + old_text_data:
        text = item.get("text", "")
        if text not in seen:
            seen.add(text)
            merged.append(item)
    merged.sort(key=lambda x: x.get("index", 0))
    return " ".join(item.get("text", "") for item in merged)


async def generate_summary_stream(
    video_config: dict,
    user_config: Optional[dict],
    chapters: Optional[list] = None,
    use_structured_output: bool = True,
) -> AsyncGenerator[str, None]:
    user_key = user_config.get("user_key") if user_config else None
    base_url = user_config.get("base_url") if user_config else None
    model_name = user_config.get("model_name") if user_config else None
    should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False

    api_key = select_api_key(user_key)
    if not api_key:
        yield "Error: Missing API key for OpenAI-compatible provider"
        return

    task_id = video_config.get("task_id")
    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "fetch_subtitles", "running", message="正在提取/获取视频字幕...")

    # Fetch subtitle
    from app.services.subtitles import fetch_subtitle
    subtitle_video_config = {
        **video_config,
        "whisper_api_key": api_key,
        "whisper_base_url": base_url,
    }
    subtitle_result = await fetch_subtitle(subtitle_video_config, should_show_timestamp)
    title = subtitle_result.get("title", "")
    subtitles_array = subtitle_result.get("subtitles_array")
    description_text = subtitle_result.get("description_text")

    if subtitle_result.get("error"):
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "fetch_subtitles", "failed", message=subtitle_result["error"])
        yield f"Error: 501::{subtitle_result['error']}"
        return

    if not subtitles_array and not description_text:
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "fetch_subtitles", "failed", message="视频中没有找到字幕")
        yield "Error: 501::No subtitle in the video"
        return

    input_text = get_small_size_transcripts(subtitles_array, subtitles_array) if subtitles_array else description_text

    user_prompt = build_user_prompt(title, input_text, video_config, should_show_timestamp, chapters)

    final_model = model_name or video_config.get("model") or settings.openai_compatible_model
    max_tokens = 8192

    # Check cache
    cache_id = get_cache_id(video_config)
    cached = await get_cached_result(cache_id)
    if cached:
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "fetch_subtitles", "completed", message="字幕提取成功")
            update_step(task_id, "generate_summary", "completed", message="AI 总结生成成功 (已命中缓存)")
        yield cached
        return

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "fetch_subtitles", "completed", message="字幕提取成功")
        update_step(task_id, "generate_summary", "running", message="正在请求 AI 模型生成总结...")

    client = create_client(base_url)
    client.api_key = api_key

    system_prompt = prompts.get_system_prompt(
        language=video_config.get("output_language", "zh"),
        should_show_timestamp=should_show_timestamp,
        use_chapters=bool(chapters),
        metadata=video_config.get("metadata"),
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Try structured output first if enabled
    if use_structured_output:
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
                markdown = parsed.to_markdown(
                    show_timestamp=should_show_timestamp,
                    show_emoji=video_config.get("show_emoji", True),
                )
                yield markdown
                if markdown:
                    await set_cached_result(cache_id, markdown)
                if task_id:
                    from app.services.status_tracker import update_step
                    update_step(task_id, "generate_summary", "completed", message="AI 总结生成成功")
                return
        except Exception:
            # Fallback to streaming text
            pass

    # Standard streaming fallback
    try:
        stream = await client.chat.completions.create(
            model=final_model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True,
        )

        full_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                full_text += delta
                yield delta

        # Post-process: try to parse and re-format for consistency
        if full_text:
            parsed = parse_markdown_to_structure(full_text)
            if parsed and len(parsed.chapters) > 0:
                formatted = parsed.to_markdown(
                    show_timestamp=should_show_timestamp,
                    show_emoji=video_config.get("show_emoji", True),
                )
                # Only replace if we got meaningful structure
                if formatted and len(formatted) > len(full_text) * 0.5:
                    full_text = formatted
            await set_cached_result(cache_id, full_text)
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "generate_summary", "completed", message="AI 总结生成成功")

    except Exception as e:
        # Fallback to non-streaming
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

            # Try structured parse
            parsed = parse_llm_json_output(text)
            if parsed:
                text = parsed.to_markdown(
                    show_timestamp=should_show_timestamp,
                    show_emoji=video_config.get("show_emoji", True),
                )
            else:
                parsed_md = parse_markdown_to_structure(text)
                if parsed_md and len(parsed_md.chapters) > 0:
                    formatted = parsed_md.to_markdown(
                        show_timestamp=should_show_timestamp,
                        show_emoji=video_config.get("show_emoji", True),
                    )
                    if formatted and len(formatted) > len(text) * 0.5:
                        text = formatted

            yield text
            if text:
                await set_cached_result(cache_id, text)
            if task_id:
                from app.services.status_tracker import update_step
                update_step(task_id, "generate_summary", "completed", message="AI 总结生成成功")
        except Exception as fallback_e:
            yield f"Error: {str(fallback_e)}"


async def generate_summary(
    video_config: dict,
    user_config: Optional[dict],
    chapters: Optional[list] = None,
    use_structured_output: bool = True,
) -> str:
    user_key = user_config.get("user_key") if user_config else None
    base_url = user_config.get("base_url") if user_config else None
    model_name = user_config.get("model_name") if user_config else None
    should_show_timestamp = user_config.get("should_show_timestamp", False) if user_config else False

    api_key = select_api_key(user_key)
    if not api_key:
        return "Error: Missing API key for OpenAI-compatible provider"

    task_id = video_config.get("task_id")
    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "fetch_subtitles", "running", message="正在提取/获取视频字幕...")

    from app.services.subtitles import fetch_subtitle
    subtitle_video_config = {
        **video_config,
        "whisper_api_key": api_key,
        "whisper_base_url": base_url,
    }
    subtitle_result = await fetch_subtitle(subtitle_video_config, should_show_timestamp)
    title = subtitle_result.get("title", "")
    subtitles_array = subtitle_result.get("subtitles_array")
    description_text = subtitle_result.get("description_text")

    if subtitle_result.get("error"):
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "fetch_subtitles", "failed", message=subtitle_result["error"])
        return f"Error: 501::{subtitle_result['error']}"

    if not subtitles_array and not description_text:
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "fetch_subtitles", "failed", message="视频中没有找到字幕")
        return "Error: 501::No subtitle in the video"

    input_text = get_small_size_transcripts(subtitles_array, subtitles_array) if subtitles_array else description_text
    user_prompt = build_user_prompt(title, input_text, video_config, should_show_timestamp, chapters)

    final_model = model_name or video_config.get("model") or settings.openai_compatible_model
    max_tokens = 8192

    cache_id = get_cache_id(video_config)
    cached = await get_cached_result(cache_id)
    if cached:
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "fetch_subtitles", "completed", message="字幕提取成功")
            update_step(task_id, "generate_summary", "completed", message="AI 总结生成成功 (已命中缓存)")
        return cached

    if task_id:
        from app.services.status_tracker import update_step
        update_step(task_id, "fetch_subtitles", "completed", message="字幕提取成功")
        update_step(task_id, "generate_summary", "running", message="正在请求 AI 模型生成总结...")

    client = create_client(base_url)
    client.api_key = api_key

    system_prompt = prompts.get_system_prompt(
        language=video_config.get("output_language", "zh"),
        should_show_timestamp=should_show_timestamp,
        use_chapters=bool(chapters),
        metadata=video_config.get("metadata"),
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Try structured output first
    if use_structured_output:
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
                markdown = parsed.to_markdown(
                    show_timestamp=should_show_timestamp,
                    show_emoji=video_config.get("show_emoji", True),
                )
                if markdown:
                    await set_cached_result(cache_id, markdown)
                if task_id:
                    from app.services.status_tracker import update_step
                    update_step(task_id, "generate_summary", "completed", message="AI 总结生成成功")
                return markdown
        except Exception:
            pass

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

        # Try to parse as JSON first
        parsed = parse_llm_json_output(text)
        if parsed:
            text = parsed.to_markdown(
                show_timestamp=should_show_timestamp,
                show_emoji=video_config.get("show_emoji", True),
            )
        else:
            # Try to parse markdown and re-format
            parsed_md = parse_markdown_to_structure(text)
            if parsed_md and len(parsed_md.chapters) > 0:
                formatted = parsed_md.to_markdown(
                    show_timestamp=should_show_timestamp,
                    show_emoji=video_config.get("show_emoji", True),
                )
                if formatted and len(formatted) > len(text) * 0.5:
                    text = formatted

        if text:
            await set_cached_result(cache_id, text)
        if task_id:
            from app.services.status_tracker import update_step
            update_step(task_id, "generate_summary", "completed", message="AI 总结生成成功")
        return text
    except Exception as e:
        return f"Error: {str(e)}"
