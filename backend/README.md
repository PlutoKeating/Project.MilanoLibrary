# MilanoLibrary Backend Service

FastAPI Python asynchronous service responsible for compiling remote video URLs and local file uploads into highly structured, Obsidian-compatible Markdown books (MilanoBook). It orchestrates a database-less filesystem storage scheme, supports custom platform adapters, and manages offline `faster-whisper` speech-to-text inference.

---

## Technical Stack

- **REST Web Server**: FastAPI + Uvicorn + Pydantic v2
- **Unified 3-Phase Pipeline**:
  - **Phase 1**: Outlining via robust JSON Schema OpenAI/Compatible model calls
  - **Phase 2**: In-memory Logical Subtitles Slicing & Parallel Leaf Node Summaries (via multi-threaded asyncio)
  - **Phase 3**: DFS Assembly compiling leaf Markdown files into a comprehensive `complete.md` book
- **Automatic Speech Recognition**: Online OpenAI Whisper API + Local `faster-whisper` (CTranslate2) Fallback
- **Media Decoding & Ingesting**: FFmpeg (metadata probing and audio track extraction)
- **High-speed Caching**: Redis / Upstash Rest API Client (skips LLM invocation for duplicate media files)
- **Extensibility**: Hot-swappable Custom Python scraping Adapters

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py               # REST server initialization, CORS setup, and router mounts
│   ├── config.py             # Global environmental configurations parser (Pydantic BaseSettings)
│   ├── models.py             # Pydantic Schemas validating request / response fields
│   ├── routers/              # Controller routers handling API endpoints
│   │   ├── cache.py          # DELETE /api/cache
│   │   ├── models.py         # GET/POST /api/models/local (Whisper model downloader)
│   │   ├── summarize.py      # POST /api/summarize (Online URL compiler pipeline)
│   │   ├── upload.py         # POST /api/video/upload (Local uploads compiler pipeline)
│   │   ├── books.py          # GET/POST/PUT/DELETE /api/books (Database-less vault manager)
│   │   └── notes.py          # GET/POST/DELETE /api/notes (Multi-book Study Guide Aggregator)
│   │
│   ├── app/adapters/         # Media platform adapters layer
│   │   ├── base.py           # Abstract BaseAdapter blueprint
│   │   ├── youtube.py        # Default YouTube scraping adapter
│   │   └── bilibili.py       # Default Bilibili scraping adapter
│   │
│   └── services/             # Dynamic core services
│       ├── _client.py        # Asynchronous OpenAI API Client factory
│       ├── db_manager.py     # Database-less filesystem manager, handling settings.json and vault paths
│       ├── book_persistence.py# Serializes and compiles books into book.json, index.json, complete.md
│       ├── adapter_manager.py# Scans and registers custom uploaded python adapters at runtime
│       ├── status_tracker.py # Tracks real-time compilation progress percentages and logs
│       ├── subtitles.py      # Fetches/scrapes subtitles from official sources or savesubs
│       ├── local_whisper.py  # Thread-safe faster-whisper ASR runner with auto GPU/CPU routing
│       ├── video_ingest.py   # Probes uploaded media files and extracts raw audio
│       ├── video_segment.py  # Memory structures for logical segment boundaries
│       ├── chapters.py       # Parses video descriptions or calls lightweight LLM for syntactic outlines
│       ├── cache.py          # Handles Redis connection and keys invalidation
│       ├── prompts.py        # Centralized system prompts for different pipelines and languages
│       └── output_schema.py  # Structured JSON schemas for outline trees
│
├── models/                   # Docker volume holding downloaded local Whisper model weights
├── storage/                  # Backing store holding settings.json and temporary cache files
├── requirements.txt          # Python package requirements
└── Dockerfile                # Multi-stage production Docker container builder
```

---

## Prerequisites & Installation

### 1. Install FFmpeg
The backend requires `ffmpeg` and `ffprobe` binaries to extract audio and probe files.
- **macOS (Homebrew)**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt update && sudo apt install -y ffmpeg`
- **Windows**: Download official builds and add the `/bin` folder to your system `PATH`.

### 2. Configure Virtual Environment
1. Create and activate a clean Python virtual environment:
   ```bash
   cd backend
   python -m venv venv
   ```
2. Activate the environment:
   - **Windows (PowerShell)**: `.\venv\Scripts\Activate.ps1`
   - **macOS/Linux**: `source venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## Running the Server

### Development Mode (with Live Reloading)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger Documentation is now accessible at [http://localhost:8000/docs](http://localhost:8000/docs).

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```
