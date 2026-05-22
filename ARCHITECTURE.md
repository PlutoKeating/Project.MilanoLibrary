# MilanoLibrary Architectural Design Document

This document outlines the high-level architecture, directory layout, core subsystems, data flow, and technology stacks of MilanoLibrary v2.

---

## 1. System Overview

MilanoLibrary v2 is structured as a **frontend-backend separated (decoupled)** system designed for high-performance video and local media summarization.

```
                  ┌────────────────────────┐
                  │      Web Browser       │
                  └───────────┬────────────┘
                              │ HTTP / WebSocket (Stream)
                              ▼
                  ┌────────────────────────┐
                  │   Frontend (Next.js)   │
                  └───────────┬────────────┘
                              │ Rest API Call (JSON/FormData)
                              ▼
                  ┌────────────────────────┐
                  │   Backend (FastAPI)    │
                  └─────┬────────────┬─────┘
                        │            │
      ┌─────────────────┴─┐        ┌─┴──────────────────┐
      │ External Services │        │   Local Services   │
      └─────────────────┬─┘        └─┬──────────────────┘
                        │            │
        ├─ Bilibili API │            ├─ FFmpeg (Slicer)
        ├─ YouTube API  │            ├─ faster-whisper (ML)
        ├─ OpenAI API   │            └─ Redis (Cache DB)
        └─ savesubs API │
```

---

## 2. Directory Layout

```
Project.MilanoLibrary/
├── frontend/                     # Next.js SPA Frontend
│   ├── pages/                    # File-system router & Catch-all entry point
│   ├── components/               # UI components styled with retro-futuristic vibes
│   ├── hooks/                    # Reactive state hooks (summarize, models, cache)
│   ├── lib/                      # Client-side API helpers & shared typescript interfaces
│   ├── utils/                    # URL extractors, parser utils, and Zod configuration schemas
│   └── styles/                   # Dark theme CSS setup
│
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── main.py               # Main application entry point & CORS configuration
│   │   ├── config.py             # Server settings parsing (Pydantic BaseSettings)
│   │   ├── models.py             # Pydantic Schemas for requests/responses
│   │   ├── routers/              # Controller routers (summarize, upload, cache, models)
│   │   └── services/             # Core business service components
│   │       ├── subtitles.py      # Multi-platform subtitles resolver
│   │       ├── local_whisper.py  # Local faster-whisper engine and downloader
│   │       ├── openai_client.py  # LLM text completion & streaming agent
│   │       ├── video_ingest.py   # Temporary media ingestion & metadata analysis
│   │       ├── video_segment.py  # ffmpeg-based video/audio chunk segmenter
│   │       ├── segment_processor.py# Multithreading chunk transcribing supervisor
│   │       ├── composer.py       # Summaries merge & final formatting composer
│   │       ├── chapters.py       # Chapter timestamps detector (Metadata / LLM)
│   │       └── cache.py          # Redis connection client & key-value cache manager
│   │
│   ├── models/                   # Local Whisper models weight storage volume
│   ├── storage/                  # Ingested temporary media files and chunk segments
│   ├── requirements.txt          # Python requirements list
│   └── Dockerfile                # Backend container script
│
├── docs/                         # Project-wide specifications
│   └── API.md                    # Structured endpoint reference
├── docker-compose.yml            # Multi-container orchestrator
└── README.md                     # Welcome README
```

---

## 3. Technology Stack

| Architecture Layer | Component | Selected Technology | Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | UI Core | Next.js 16 (Pages Router) + React 18 | High speed, flexible client-side SPA routing, catch-all routing support |
| **Styling Engine** | Visual Aesthetic | Tailwind CSS | Fast implementation of the custom Retro-Futurism Design System |
| **Backend Core** | REST Server | FastAPI + Python 3.11+ | High performance, fully asynchronous async-await loop, built-in Swagger/OpenAPI docs |
| **ML Inference** | Local ASR | faster-whisper (CTranslate2) | 4x faster execution speed and 2x lower memory consumption than standard openai-whisper |
| **Data Chunk Slicing** | Media Slicer | FFmpeg + PyAV | Robust format conversion, fast chunk split, zero-copy audio stream extraction |
| **Caching Layer** | Results Store | Redis / Upstash Redis | Key-value records store, instantaneous retrieval of cached video summaries |

---

## 4. Key Pipelines & Data Flow

### Pipeline A: Remote Video URL Summarization (`POST /api/summarize`)

```
[Browser Submit URL] ──► [FastAPI Router]
                              │
                              ▼
                  [subtitles.py: Fetch Subs]
                    ├─► YouTube / Bilibili API (Official Subs)
                    └─► savesubs (Third-party Subs)
                              │
                              ▼ (Extract Chapters)
                  [chapters.py: Parse Chapters]
                    ├─► YouTube Video Description Metadata
                    ├─► Bilibili Pages Multi-parts Structure
                    └─► LLM-based Smart Chapter Slicing (if no structural data)
                              │
                              ▼ (AI Stream Summarizer)
                  [openai_client.py: generate_summary_stream]
                    ├─► Read subtitles content
                    ├─► Request ChatCompletion API with System Prompts
                    └─► Yield stream tokens back to Next.js
                              │
                              ▼
                  [marked-react] ──► Render beautiful summary layout on UI
```

### Pipeline B: Local Video/Audio File Upload (`POST /api/video/upload`)

```
[Browser Upload File] ──► [FastAPI Upload Router]
                                │
                                ▼
                    [video_ingest.py: Save File]
                      ├─► Create unique video UUID
                      └─► Extract Metadata (duration, size)
                                │
                                ▼
                    [video_segment.py: Slicing]
                      ├─► Check for structural Chapters
                      └─► Segment audio into chunks using FFmpeg (default 60s per chunk)
                                │
                                ▼
                    [segment_processor.py: Batch Process]
                      ├─► Multi-threading / Asynchronous Transcribing
                      ├─► Try Online OpenAI Whisper API (First Priority)
                      └─► Fallback to Local faster-whisper model (Second Priority)
                                │
                                ▼
                    [composer.py: Merge & Summarize]
                      ├─► Group all transcribed text chunks
                      ├─► LLM Segment-by-Segment Summarization
                      └─► Synthesize chapters and final Markdown
                                │
                                ▼
                    [Stream Response] ──► Render progressive Markdown text block
```

---

## 5. Local Whisper Auto-Fallback Mechanism

MilanoLibrary has a resilient local-ASR architecture. When a user uploads a media file, the backend attempts to transcribe audio via the online Whisper API. If that fails (e.g., API key has no Whisper permission, custom proxy returns 404, or the user didn't specify a key), the server initiates the **Local Fallback Workflow**:

1. **Model Loader Check**: Verify if the target model directory (e.g., `/app/models/faster-whisper-small/model.bin`) exists.
2. **On-demand Downloader**: If missing, FastAPI starts a multi-threaded downloader downloading files from Hugging Face into `/app/models/`.
3. **Execution Device Picker**: Selects CUDA GPU automatically if compatible drivers and dll/so dependencies are present; otherwise, seamlessly defaults to high-speed multithreaded CPU execution using quantizations (`int8`).
4. **CTranslate2 Whisper Runner**: transcribes audio files chunk-by-chunk and returns timestamp-annotated transcript segments back to the summarization pipeline.

---

## 6. Architectural Constraints & Style Guides

- **No Next.js API Routes**: Next.js is strictly used as a pure single page rendering app. All business logic, caching, API calls, and ML inference are isolated inside the FastAPI backend.
- **Stateless Server with Storage mounts**: While the FastAPI backend stores video chunks and local Whisper models, all configurations are passed statelessly in request bodies or environment variables. Models and media uploads are cached using Docker volume bindings to `./backend/models` and `./backend/storage`.
- **Zod Schema Synchronization**: Zod rules in `frontend/utils/schemas/video.ts` must align with Python Pydantic structures in `backend/app/models.py`.
