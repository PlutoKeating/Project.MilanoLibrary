# Backend System Architecture Specifications

This document details the internal design, component relationships, data persistence models, and processing pipelines of the MilanoLibrary FastAPI Backend.

---

## 1. Request Flow Overview

The backend acts as a **Database-less Video Vault & Recomposition Compiler**. Rather than managing database connections, it maps requests directly to physical folder structures.

Both online URL submissions (`POST /api/summarize`) and local media file uploads (`POST /api/video/upload`) route into a single unified 3-phase compilation pipeline:

```
[POST /api/summarize] (Online URL)                [POST /api/video/upload] (Local File)
           │                                                    │
           ▼ (fetch_metadata)                                   ▼ (upload_file)
[Resolve metadata from Platform Adapter]              [Probes media file metadata]
           │                                                    │
           ▼ (download_video)                                   │
[Download video/audio stream locally]                           │
           │                                                    │
           └─────────────────────────┬──────────────────────────┘
                                     │
                                     ▼ (extract_audio / transcribe)
                    [Fetch Subtitles / Transcribe Audio]
                 (Online Subtitles OR Local faster-whisper)
                                     │
                                     ▼ (detect_chapters)
                    [Phase 1: Nested Chapter Outlining]
               (Calls robust LLM with strict JSON Schema)
                                     │
                                     ▼ (segment_video)
                    [Logical Segment planning in-memory]
                                     │
                                     ▼ (process_segments)
                    [Phase 2: Concurrently Summarize Leaves]
                    (Multi-threaded Asyncio LLM Summarizer)
                                     │
                                     ▼ (compose_summary)
                    [Phase 3: Recursive DFS Book Assembly]
               (Saves book.json, index.json, complete.md under Vault)
```

---

## 2. Component Specifications

### 2.1 Router Controllers (`app/routers/`)
- **`summarize.py`**: Intercepts online URLs. Maps request IDs to custom adapters to fetch platform metadata and stream downloads, launching the background compilation process.
- **`upload.py`**: Interacts with multipart `form-data` uploads. Saves files to a temporary location, extracts properties, and fires off the background compiler.
- **`books.py`**: Exposes directory setting, directory browsing, and book metadata updates. Connects the frontend `FileExplorer` directly to physical storage.
- **`notes.py`**: Exposes the Multi-book Study Notes Aggregator. Aggregates multiple book summaries and prompts LLM to generate custom systematic study notes.
- **`models.py`**: Orchestrates offline Whisper model downloads and queries percent progress.
- **`cache.py`**: Handles cache invalidation queries on the Redis client.

### 2.2 Dynamic Platform Adapters (`app/adapters/` & `app/services/adapter_manager.py`)
Provides runtime extensibility for platform scraping:
- Built-in adapters are configured for YouTube (`youtube.py`) and Bilibili (`bilibili.py`).
- **`adapter_manager.py`** scans the adapters folder and loads custom python adapters uploaded by users at runtime, resolving scrapers without server restarts.

### 2.3 Database-less Vault Manager (`app/services/db_manager.py` & `book_persistence.py`)
- **`db_manager.py`** resolves the active host directory path dynamically. Reads/writes path strings from/to `storage/settings.json`. Maps files and directory listings seamlessly for the SPA file explorer.
- **`book_persistence.py`** defines saving behaviors for compiled MilanoBooks. Writes basic metadata in `book.json` and structural indices in `index.json`. Creates a `segments/` folder for individual leaf markdown chunks and compiles the unified `complete.md`.

### 2.4 Status Tracker (`app/services/status_tracker.py`)
A thread-safe in-memory state tracker:
- Maps task IDs to progress percentages and logs.
- Exposes structured pipelines steps: `fetch_metadata`/`upload_file`, `download_video`, `extract_audio`, `transcribe`, `detect_chapters`, `segment_video`, `process_segments`, `compose_summary`.
- Queried periodically via `GET /api/status/{task_id}`.

### 2.5 ASR Subsystem (`app/services/subtitles.py` & `local_whisper.py`)
- **`subtitles.py`**: Fetches online transcripts from platforms or scrapes via savesubs.
- **`local_whisper.py`**: Manages the local `faster-whisper` process. Safely shares loaded models across threads. Features hardware auto-routing (FP16 CUDA GPU or INT8 CPU execution).

---

## 3. The 3-Phase Compilation Pipeline (Detailed)

1. **Phase 1: Outline Tree Generation**:
   - The entire transcript is passed to a robust LLM.
   - Pydantic outlines (`OUTLINE_JSON_SCHEMA`) enforce strict JSON responses.
   - The LLM creates a nested chapter outline tree where each leaf node maps to a continuous, non-overlapping timestamp range `[start_seconds, end_seconds]` spanning the entire video.
   - No pre-pended serial numbers or hierarchical headers (e.g., "1.1") are permitted inside LLM-generated titles (titles are kept clean; indexes are formatted dynamically during compilation).
2. **Phase 2: In-Memory Logical Slicing & Parallel Summaries**:
   - Slices the subtitle paragraph list in-memory matching leaf nodes' timestamp bounds.
   - Launches concurrent async LLM tasks to summarize leaf segments.
   - Instructs LLMs to write detailed prose summaries, capturing all LaTeX formulas, code snippets, and specific data points.
3. **Phase 3: DFS Recursive Assembly**:
   - Performs a recursive DFS walk on the `outline` tree structure.
   - Resolves level depths and appends numbered heading prefixes (e.g. "一、" for Level 1, "1.1." for Level 2, "1.1.1." for Level 3, etc.).
   - Pulls individual leaf node markdown summaries from `segments/` and concatenates them into the master `complete.md` book file.
