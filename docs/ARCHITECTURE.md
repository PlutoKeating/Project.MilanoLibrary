# MilanoLibrary Architectural Design Document

This document outlines the modern high-level architecture, directory layout, core subsystems, database-less storage scheme, and technology stacks of MilanoLibrary.

---

## 1. System Overview

MilanoLibrary is designed as a **decoupled frontend-backend system** implementing a **Database-less Video Vault & Recomposition Compiler**. 

```
┌─────────────────────────────────┐      HTTP API / JSON      ┌─────────────────────────────────┐
│           Frontend              │ ◄───────────────────────► │            Backend              │
│   Next.js React (Pages HMR)     │   /api/books              │            FastAPI              │
│   No API Routes (Client-Only)   │   /api/notes              │         (Async Python)         │
└─────────────────────────────────┘   /api/status/{id}        └─────────────────────────────────┘
                                                                               │
                                                               ┌───────────────┴───────────────┐
                                                               │         Services Layer        │
                                                               └───────────────┬───────────────┘
                                                                               ├─ OpenAI/LLM Provider
                                                                               ├─ local faster-whisper
                                                                               ├─ Redis (High-speed cache)
                                                                               └─ Filesystem Storage Root
                                                                                  (Obsidian-Compatible Vault)
```

---

## 2. Directory Layout

```
Project.MilanoLibrary/
├── frontend/                     # Next.js Frontend Application (Monospace Monochromatic Style)
│   ├── pages/                    # Catch-all page router entry point [[...slug]].tsx
│   ├── components/               # Pure UI modules (FileExplorer, PipelineProcessor, TimelineProgress, etc.)
│   ├── hooks/                    # Reactive hooks logic (useSummarize, useModelManager, useClearCache)
│   ├── lib/                      # Base configurations & global typescript interfaces
│   ├── utils/                    # Video ID extraction regex, parser, and Zod configuration schemas
│   └── styles/                   # Dark global CSS & Markdown typographic setup
│
├── backend/                      # FastAPI Python Backend
│   ├── app/
│   │   ├── main.py               # REST API entry point, middlewares, and router mappings
│   │   ├── config.py             # Settings configurations parser using Pydantic BaseSettings
│   │   ├── models.py             # Pydantic Schemas validating request & response payloads
│   │   ├── routers/              # Controller endpoints (summarize, upload, books, notes, models, cache)
│   │   └── services/             # Dynamic core services
│   │       ├── db_manager.py     # Database-less filesystem manager, handling directories dynamically
│   │       ├── book_persistence.py# MilanoBook serializer (book.json, index.json, complete.md, segments/)
│   │       ├── subtitles.py      # Subtitles extractor (Bilibili & YouTube subtitle URL fetchers)
│   │       ├── local_whisper.py  # Local faster-whisper (CTranslate2) engine & downloader status poller
│   │       ├── status_tracker.py # Global state-machine tracking task step percent & logs
│   │       ├── openai_client.py  # Robust LLM gateway supporting strict schema calling
│   │       ├── adapter_manager.py# Custom Python scrapers manager supporting runtime uploads
│   │       ├── video_ingest.py   # Temporary storage of uploads & media probe properties
│   │       ├── video_segment.py  # In-memory Segment metadata structures
│   │       ├── chapters.py       # Description parsing or LLM-based chapter detector
│   │       ├── cache.py          # Redis connection pool and invalidation
│   │       ├── prompts.py        # System and user prompts for outline and leaf levels
│   │       └── output_schema.py  # Hardcoded structured JSON schemas for outline parsing
│   │
│   ├── models/                   # Local Whisper models weight storage path
│   ├── storage/                  # System configurations (settings.json) and cache
│   └── requirements.txt          # Python dependencies
│
└── docs/                         # Specifications documentation folder
```

---

## 3. Database-less Architecture (Obsidian-Compatible)

Unlike traditional platforms relying on SQL servers (Postgres/MySQL) or MongoDB, MilanoLibrary adopts a **pure file-system database-less model** stored directly in a user-selected **Active Root Vault Directory**.

### Directory Hierarchy on Host Machine
```
[Active Root Directory]/
├── book_20260524_152345_a1b2c3d4/   # A single MilanoBook
│   ├── book.json                    # Lightweight book metadata (Title, Author, Source URL, Duration)
│   ├── index.json                   # Structured chapter outline tree with leaf UUID mappings
│   ├── raw.json                     # Complete subtitle/transcription sentences with timestamps
│   ├── complete.md                  # Beautifully assembled complete markdown book (LaTeX & Code included)
│   ├── source_video.mp4             # Saved physical media stream (if uploaded locally)
│   └── segments/                    # Individual chapter summary segments
│       ├── seg_4b9a1122.md
│       ├── seg_7d2f3344.md
│       └── ...
└── .notes/                          # Study Notes Aggregator outputs
    ├── note_20260524_163311_f1g2h3.json # High-fidelity synthesized cross-book study guide
    └── ...
```

This design guarantees absolute data ownership and portability, allowing users to directly open their Active Root Directory in **Obsidian** or any Markdown text editor.

---

## 4. The Unified 3-Phase Compilation Pipeline

The backend unifies remote URL summarization (`POST /api/summarize`) and local media upload (`POST /api/video/upload`) inside a single, state-tracked, highly parallelized pipeline:

```
[Trigger Request] 
       │
       ▼ (Step: fetch_metadata / upload_file)
[Resolve metadata from Platform Adapter or Ingest uploaded media]
       │
       ▼ (Step: download_video [online only])
[Download stream bytes into local path]
       │
       ▼ (Step: extract_audio / transcribe)
[Fetch subtitles online, OR fall back to transcribing via OpenAI Whisper API / local faster-whisper]
       │
       ▼ (Step: detect_chapters)
[Phase 1: Robust LLM Call with JSON schema to compile nested Chapter Outline tree & overall summary]
       │
       ▼ (Step: segment_video)
[Plan Logical Segment division in-memory (No physical FFmpeg slicing needed!)]
       │
       ▼ (Step: process_segments)
[Phase 2: Concurrent/Parallelized Leaf Node Summaries using LLM in knowledge-lecture prose style]
       │
       ▼ (Step: compose_summary)
[Phase 3: Recursive compilation of segments & persistence as a structural MilanoBook under Vault]
```

### Detailed Pipeline Stages

1. **Subtitles Fetching & ASR fallback**: Attempts to pull official subtitles. If missing (or local media file), transcribes the audio. If online OpenAI Whisper API fails (or no key provided), automatically falls back to the thread-safe offline `faster-whisper` model.
2. **Phase 1 (Outline Generation)**: Passes the entire timestamped transcript to a strong LLM. Uses strict JSON Schema (`OUTLINE_JSON_SCHEMA`) to structure a deep hierarchical chapter outline tree, guaranteeing no overlapping, semantic continuity, and strict raw title text (no pre-pended numbers).
3. **Phase 2 (Parallel Leaf Summaries)**: Flattens the outline tree to harvest "Leaf Nodes" (chapters without subchapters). Slices subtitle arrays logically in-memory matching leaf timestamp ranges `[start_seconds, end_seconds]`. Synthesizes individual leaf node summaries in parallel using a multi-threaded asyncio pool. Emojis, math LaTeX formulas, and raw code snippets are preserved.
4. **Phase 3 (DFS Compilation & Book Saving)**: Performs a Recursive DFS walk on the Outline tree to stitch leaf summary documents with hierarchically formatted heading prefixes (e.g., "一、" for level-1, "1.1." for level-2, etc.). Outputs `complete.md` and updates metadata in `book.json`.

---

## 5. Study Notes Aggregator

To compile knowledge across domains, the **Aggregator** allows selecting multiple MilanoBooks:
1. Gathers metadata, transcript paragraph snapshots, and structural elements of chosen books.
2. Formulates a comprehensive context and calls a robust LLM with user-supplied prompts.
3. Generates systematic study notes containing:
   - Core Knowledge Synthesis
   - Key Technical Concept Glossaries
   - Step-by-step Structural Breakdowns
   - Concrete Practice Guides
4. Saves compiled results under the `.notes/` sub-folder.

---

## 6. Development & Quality Constraints

- **Decoupled API Routing**: The frontend operates strictly as an SPA client, reading from `/api/books/settings/root` to display directory structures via a custom custom-built `FileExplorer`.
- **Prettier & TypeScript**: Strictly enforced types on both ends to avoid runtime desynchronization.
- **Resilient Fallback**: Local faster-whisper uses hardware auto-detection (`cuda` with FP16, or thread-safe multithreaded `cpu` with optimized INT8 quantization).
