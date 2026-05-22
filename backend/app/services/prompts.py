from typing import Optional

LANGUAGE_CODE_TO_ENGLISH_NAME = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
    "ar": "Arabic",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
    "tr": "Turkish",
    "pl": "Polish",
    "sv": "Swedish",
    "id": "Indonesian",
    "hi": "Hindi",
    "vi": "Vietnamese",
    "th": "Thai",
}

PROMPT_LANGUAGE_MAP = {
    "中文": "Chinese",
    "English": "English",
    "日语": "Japanese",
    "韩语": "Korean",
    "Français": "French",
    "Deutsch": "German",
    "Español": "Spanish",
    "Русский": "Russian",
    "العربية": "Arabic",
    "Português": "Portuguese",
    "Italiano": "Italian",
    "Nederlands": "Dutch",
    "Türkçe": "Turkish",
    "Polski": "Polish",
    "Svenska": "Swedish",
    "Bahasa Indonesia": "Indonesian",
    "हिन्दी": "Hindi",
    "Tiếng Việt": "Vietnamese",
    "泰语": "Thai",
}

DEFAULT_LANGUAGE = "zh"


def get_system_prompt(
    language: str = "Chinese",
    should_show_timestamp: bool = False,
    use_chapters: bool = False,
    metadata: Optional[dict] = None,
) -> str:
    en_language = PROMPT_LANGUAGE_MAP.get(language, language)

    chapter_instruction = ""
    if use_chapters:
        chapter_instruction = (
            "The video is organized into chapters/sections. "
            "You MUST preserve the chapter structure in your output. Each chapter should have its own "
            "section with relevant bullet points. "
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
                "\n\nHere is some context/metadata about this video. Use this to enrich and improve "
                "the transcription summary quality (e.g. knowing uploader context, subject terminology):\n"
                + "\n".join(metadata_parts) + "\n\n"
            )

    base = (
        f"You are a meticulous Knowledge Extractor and Transcript Structurer. Your task is to extract "
        f"ALL specific factual details, concepts, and knowledge points from the video content in {en_language}. "
        f"{chapter_instruction}"
        f"{metadata_instruction}"
        f"DO NOT summarize, abbreviate, or omit any specific information. The length and depth of your output "
        f"must strictly reflect the actual density of the content. If the text is long and dense, output a highly "
        f"detailed, extensive document. Correct any obvious typos in the transcript, but preserve the speaker's original meaning."
    )

    return base


def get_user_subtitle_prompt(
    title: str,
    transcript: str,
    video_config: dict,
    chapters: Optional[list] = None,
) -> str:
    video_title = " ".join(title.split())
    video_transcript = " ".join(transcript.split())
    language = video_config.get("output_language", DEFAULT_LANGUAGE)
    language_name = LANGUAGE_CODE_TO_ENGLISH_NAME.get(language, language)
    show_emoji = video_config.get("show_emoji", True)

    emoji_template_text = "[Emoji] " if show_emoji else ""
    emoji_description_text = "Choose an appropriate emoji for each bullet point. " if show_emoji else ""

    # Build chapter context if available
    chapter_context = ""
    if chapters and len(chapters) > 0:
        chapter_context = "\n\nThe video has the following chapters/sections:\n"
        for ch in chapters:
            title_ch = ch.get("title", "Untitled")
            chapter_context += f"  - {title_ch}\n"
        chapter_context += (
            "\nIMPORTANT: You MUST organize your output by these chapters. "
            "Each chapter should be a separate section with its own bullet points. "
            "Do NOT merge chapters together.\n"
        )

    prompt = (
        f"Your output should use the following template:\n## Summary\n## Highlights\n"
        f"### Chapter Title (if chapters exist)\n"
        f"- {emoji_template_text}Bulletpoint\n"
        f"    - Child points (if applicable)\n\n"
        f"Process the transcript thoroughly. Follow the original structure and logic of the speaker. "
        f"Convert all scattered spoken knowledge points into well-structured, highly detailed bullet points with nested children if sub-concepts exist. "
        f"Ensure every specific detail, example, or definition mentioned is fully preserved. "
        f"{emoji_description_text}"
        f"Use the text above: {{Title}} {{Transcript}}.\n\n"
        f"Reply in {language_name} Language."
    )

    return (
        f'Title: "{video_title}"\n'
        f'Transcript: "{video_transcript}"\n'
        f'{chapter_context}\n'
        f'Instructions: {prompt}'
    )


def get_user_subtitle_with_timestamp_prompt(
    title: str,
    transcript: str,
    video_config: dict,
    chapters: Optional[list] = None,
) -> str:
    video_title = " ".join(title.split())
    video_transcript = " ".join(transcript.split())
    language = video_config.get("output_language", DEFAULT_LANGUAGE)
    language_name = LANGUAGE_CODE_TO_ENGLISH_NAME.get(language, language)
    show_emoji = video_config.get("show_emoji", True)

    emoji_template_text = "[Emoji] " if show_emoji else ""

    # Build chapter context if available
    chapter_context = ""
    if chapters and len(chapters) > 0:
        chapter_context = "\n\nThe video has the following chapters/sections:\n"
        for ch in chapters:
            title_ch = ch.get("title", "Untitled")
            chapter_context += f"  - {title_ch}\n"
        chapter_context += (
            "\nIMPORTANT: You MUST organize your output by these chapters. "
            "Each chapter should be a separate section with its own bullet points. "
            "Do NOT merge chapters together.\n"
        )

    prompt_with_timestamp = (
        f"Act as a meticulous Knowledge Extractor and provide highly detailed bullet points for the text transcript "
        f"given in the format [seconds] - [text]{chapter_context}\n"
        f"Make sure that:\n"
        f"    - Please start by summarizing the whole video in one short sentence as an introduction.\n"
        f"    - Then, extract all specific factual details, concepts, and knowledge points without summarizing or omitting information.\n"
        f"    - each bullet_point should have the start timestamp, use this template: "
        f"- seconds - {emoji_template_text}[bullet_point]\n"
        f"    - there may be typos in the subtitles, please correct them\n"
        f"    - If chapters are provided, group bullet points under each chapter heading (### Chapter Title)\n"
        f"    - Reply all in {language_name} Language."
    )

    return f"Title: {video_title}\nTranscript: {video_transcript}\n\nInstructions: {prompt_with_timestamp}"


def get_structured_output_system_prompt(
    language: str = "Chinese",
    use_chapters: bool = False,
) -> str:
    """System prompt when using JSON structured output mode."""
    en_language = PROMPT_LANGUAGE_MAP.get(language, language)

    chapter_instruction = ""
    if use_chapters:
        chapter_instruction = (
            "The video is organized into chapters. You MUST output each chapter as a separate entry "
            "in the 'chapters' array, preserving the original chapter titles and order. "
        )

    return (
        f"You are a meticulous Knowledge Extractor and Transcript Structurer. {chapter_instruction}"
        f"Your task is to extract ALL specific factual details, concepts, and knowledge points from the video content in {en_language}. "
        f"DO NOT summarize, abbreviate, or omit any specific information. The length and depth of your output "
        f"must strictly reflect the actual density of the content. Correct any obvious typos in the transcript, "
        f"but preserve the speaker's original meaning. "
        f"Output MUST be valid JSON conforming to the provided schema."
    )


def get_structured_output_user_prompt(
    title: str,
    transcript: str,
    video_config: dict,
    chapters: Optional[list] = None,
) -> str:
    """User prompt for structured JSON output mode."""
    video_title = " ".join(title.split())
    video_transcript = " ".join(transcript.split())
    language = video_config.get("output_language", DEFAULT_LANGUAGE)
    language_name = LANGUAGE_CODE_TO_ENGLISH_NAME.get(language, language)
    show_emoji = video_config.get("show_emoji", True)

    chapter_context = ""
    if chapters and len(chapters) > 0:
        chapter_context = "\n\nThe video has the following chapters/sections:\n"
        for ch in chapters:
            title_ch = ch.get("title", "Untitled")
            chapter_context += f"  - {title_ch}\n"

    return (
        f'Title: "{video_title}"\n'
        f'Transcript: "{video_transcript}"\n'
        f'{chapter_context}\n'
        f'Instructions:\n'
        f'1. Provide a one-sentence overall_summary of the entire video.\n'
        f'2. Organize the extracted knowledge into chapters (use the provided chapters if available).\n'
        f'3. Each chapter should have a chapter_title.\n'
        f'4. Each bullet point should have:\n'
        f'   - text: the highly detailed extracted knowledge point\n'
        f'   - emoji: {"an appropriate emoji" if show_emoji else "null"}\n'
        f'   - children: nested bullet points if sub-concepts exist\n'
        f'5. Process the transcript thoroughly. Convert all scattered spoken knowledge points into well-structured, highly detailed bullet points. Ensure every specific detail, example, or definition mentioned is fully preserved.\n'
        f'6. Reply in {language_name} Language.\n'
        f'7. Output MUST be valid JSON only, no markdown, no extra text.'
    )
