# MilanoLibrary Backend Service

FastAPI Python service for video transcription and summarization. It processes remote video URLs, supports local video/audio uploads, hosts an automatic local `faster-whisper` transcription workflow, and caches results to Redis.

---

## Technical Stack

- **REST Framework**: FastAPI + Uvicorn + Pydantic v2
- **ASR (Speech-to-Text)**: Online OpenAI Whisper API + Local `faster-whisper` (CTranslate2) Fallback
- **Media Slicing**: FFmpeg, PyAV, Pydub
- **Caches & Databases**: Redis, Upstash Rest Client
- **Large Language Model Integrations**: `openai` Python SDK (fully compatible with any custom base URL gateways)

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py               # FastAPI router mounting, middleware & initialization
│   ├── config.py             # Configuration properties definition (Pydantic BaseSettings)
│   ├── models.py             # Pydantic Schemas for requests/responses validation
│   ├── routers/              # Controller routers handling incoming API endpoints
│   │   ├── cache.py          # DELETE /api/cache
│   │   ├── models.py         # GET/POST /api/models/local
│   │   ├── summarize.py      # POST /api/summarize
│   │   └── upload.py         # POST /api/video/upload
│   └── services/             # Core business service logic implementations
│       ├── _client.py        # Shared helper to generate authentic OpenAI client connections
│       ├── openai_client.py  # Primary LLM summary and text completion engines (batch & stream)
│       ├── subtitles.py      # Downloader/scrapers for YouTube, Bilibili and savesubs
│       ├── local_whisper.py  # Local faster-whisper engine, cuda/cpu driver check, and model manager
│       ├── video_ingest.py   # Temporary storage of uploaded files & metadata generation
│       ├── video_segment.py  # Smart FFmpeg chunks slicer based on chapters or fixed steps
│       ├── segment_processor.py# Multithreading / Concurrent segment transcription supervisor
│       ├── composer.py       # Segment text merge & final markdown styling composer
│       ├── chapters.py       # Chapter analysis from video description or LLM subtitle scans
│       ├── cache.py          # Redis caching utilities
│       ├── prompts.py        # System prompt templates map for various output configurations
│       └── output_schema.py  # Hardcoded JSON structures for structured schemas outputs
│
├── models/                   # Docker mounted volume holding downloaded offline Whisper model weights
├── storage/                  # Ingested video files and temporary audio chunk partitions
├── docs/                     # Backend-specific architectural specifications
├── requirements.txt          # Python packages requirements
└── Dockerfile                # Production-grade multi-stage container build file
```

---

## Prerequisites & Installation

### FFmpeg Installation
The backend relies on the `ffmpeg` and `ffprobe` binaries to handle audio extraction and chunk slicing.
- **Ubuntu/Debian**: `sudo apt update && sudo apt install -y ffmpeg`
- **macOS (Homebrew)**: `brew install ffmpeg`
- **Windows**: Install via scoop/chocolatey or download the builds from the official website and add them to your user `PATH`.

### Local Virtual Environment Setup
1. Enter the `backend` directory and create a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   ```
2. Activate the virtual environment:
   - **Windows**: `.\venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Server

### Development Mode (with Live Reloading)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
You can now access the interactive OpenAPI/Swagger Documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Environmental Configuration

Create `backend/.env` from `backend/.env.example` and populate your API settings:

```env
# Primary OpenAI Config
OPENAI_API_KEY=sk-xxxxxx

# Custom API Gateway (Optional)
OPENAI_COMPATIBLE_API_KEY=sk-compatible-key
OPENAI_COMPATIBLE_BASE_URL=https://api.yourprovider.com/v1
OPENAI_COMPATIBLE_MODEL=gpt-4o-mini

# Offline local-Whisper settings
LOCAL_WHISPER_MODEL=small
LOCAL_WHISPER_DEVICE=auto
LOCAL_WHISPER_COMPUTE_TYPE=auto

# Cache settings
REDIS_URL=redis://localhost:6379

# Server and CORS
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
```
