# Backend System Architecture Spec

This document details the internal design, component relationships, processing pipelines, and module specifications of the MilanoLibrary FastAPI Backend.

---

## 1. Request Flow Overview

The backend is completely stateless and handles summarization requests through two primary endpoints:

```
                  [POST /api/summarize] (Remote URL)
                           │
                           ▼
                  [subtitles.py: Fetch]
                           │
                           ▼
                  [chapters.py: Chapters]
                           │
                           ▼
             [openai_client.py: LLM Stream]
                           │
                           ▼
                  [Cache Result (Redis)]
```

```
               [POST /api/video/upload] (Local File)
                           │
                           ▼
                [video_ingest.py: Save]
                           │
                           ▼
               [video_segment.py: Slicing]
                           │
                           ▼
             [segment_processor.py: Transcribe]
             (Online API / Local faster-whisper)
                           │
                           ▼
               [composer.py: Merge Summaries]
                           │
                           ▼
                  [Cache Result (Redis)]
```

---

## 2. Component Specifications

### 2.1 Router Controllers (`app/routers/`)
- **`summarize.py`**: Validates the input `VideoConfig` and `UserConfig`. Initiates the remote subtitle pipeline and triggers `generate_summary_stream()` to yield streamed Markdown chunks or structured completions back to the client.
- **`upload.py`**: Handles incoming multipart `form-data` uploads containing file binary, stringified configurations, and passes the media to the pipeline runner `_run_pipeline()`.
- **`models.py`**: Interacts with the local Whisper registry, allowing clients to query download statuses and fetch model weight packages in the background safely.
- **`cache.py`**: Clear-cache endpoint connected directly to the Redis database connection pool.

### 2.2 Shared Client Factory (`app/services/_client.py`)
Encapsulates API client lifecycle and configuration loading. Evaluates whether to use user-overridden keys (`user_config`) or fallback to server-side keys (`backend/.env`). Creates safe, asynchronous OpenAI client instances.

### 2.3 LLM Summarizer Service (`app/services/openai_client.py`)
Responsible for crafting structured LLM prompts based on user preferences (timestamps, languages, emojis) and sending chat completion requests. Supports **Structured Outputs** using `Pydantic` models to guarantee structured, predictable markdown outputs.

### 2.4 Multitasking Transcribing Engine (`app/services/segment_processor.py` & `local_whisper.py`)
- For long media files, sequential transcription is slow. The backend uses **audio segment chunking (ffmpeg-based)** to split long streams into distinct shorter wav chunks (e.g., 60-second segments or structural chapters).
- `segment_processor.py` orchestrates these chunks, firing off concurrent threads to transcribe them.
- If online OpenAI Whisper is selected but returns a failure, it falls back immediately to `local_whisper.py` using `faster-whisper` (CTranslate2 backend).
- `local_whisper.py` manages the thread-safe loading of models and features automatic hardware routing (`cuda` or `cpu`).

### 2.5 Chapters Detection Subsystem (`app/services/chapters.py`)
Attempts to break down the video into natural chapters:
- **YouTube**: Parses description text for timestamps.
- **Bilibili**: Maps multi-page (multi-P) structures to chapters.
- **Fallback / Local Upload**: If no structural data is present, the subtitle transcripts are passed to a lightweight LLM context to run syntactic boundary detection, returning structured chapter definitions (titles + timestamp intervals).

### 2.6 Composer Compiler (`app/services/composer.py`)
Merges segment transcriptions and their mini-summaries into a coherent global document. Groups segment points under their corresponding detected chapters, formats timestamps, and yields stream chunks for visual progression.

---

## 3. Data Processing Pipeline (Detailed)

When a local video file is uploaded to `POST /api/video/upload`:

1. **Ingest (`video_ingest.py`)**: File is saved to `storage/videos/` with a unique UUID. Native ffmpeg extractors fetch metadata (bitrate, channels, duration).
2. **Segment (`video_segment.py`)**: Audio is extracted using `ffmpeg -y -i <video> -vn -acodec pcm_s16le -ar 16000 -ac 1 <output.wav>`. Then, the audio is sliced into segment chunks under `storage/segments/` matching chapter durations or fixed steps.
3. **Transcribe (`segment_processor.py`)**: 
   - Uses `ThreadPoolExecutor` to run concurrent transcription workers.
   - Each worker converts a `.wav` file to text and records start/end timestamps.
4. **LLM Synthesis (`composer.py` & `openai_client.py`)**:
   - Compiles segment transcripts into highly formatted summary text.
   - Saves final result hashes into Redis using a composite key (`video_id + language + show_timestamp + show_emoji`).
5. **Garbage Collection**: Unused temporary files inside `storage/segments/` and `storage/videos/` are removed after composition or pipeline failure to prevent local storage bloat.
