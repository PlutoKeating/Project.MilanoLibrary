# Backend Quick Start Guide

This guide describes how to set up, run, configure, and troubleshoot the FastAPI backend service for MilanoLibrary.

---

## 1. Prerequisites

Before starting, ensure your host system has:
1. **Python 3.11+**: Check with `python --version`.
2. **FFmpeg**: Essential for parsing local uploads and slicing audio.
   - Run `ffmpeg -version` to verify it's globally available in your command line.
3. **Redis Server** (Optional, recommended): For result caching. If running via Docker, this is managed automatically.

---

## 2. Installation

1. Clone the repository and navigate to the backend folder:
   ```bash
   cd MilanoLibrary-v1/backend
   ```

2. Create and activate a clean Python virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Upgrade pip and install all Python requirements:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 3. Configuration

Duplicate the `.env.example` file and configure it:

```bash
cp .env.example .env
```

Open `.env` in your preferred editor. Here are the core keys:

| Environment Variable | Allowed Values | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `OPENAI_API_KEY` | `sk-...` | None | Official OpenAI API Key. Required if not using third-party compatible providers. |
| `OPENAI_COMPATIBLE_API_KEY` | `sk-...` | None | Alternative gateway key (e.g. DeepSeek, Groq, OpenRouter). |
| `OPENAI_COMPATIBLE_BASE_URL` | URL | `https://api.openai.com/v1` | Custon base URL for compatible API services. |
| `OPENAI_COMPATIBLE_MODEL` | model name | `gpt-4o-mini` | Fallback model to request if no client overrides are passed. |
| `LOCAL_WHISPER_MODEL` | `tiny`/`base`/`small`/`medium`/`large-v3` | `small` | Default model size downloaded automatically for offline local transcription. |
| `LOCAL_WHISPER_DEVICE` | `auto`, `cuda`, `cpu` | `auto` | Execution hardware. If CUDA compatible drivers are present, defaults to `cuda`. |
| `LOCAL_WHISPER_COMPUTE_TYPE`| `auto`, `float16`, `int8`, `float32` | `auto` | Quantization precision. CPU is highly optimized for `int8`. |
| `REDIS_URL` | Redis Connection URI | `redis://localhost:6379` | Local or Docker Redis URL to persist summary cache hashes. |
| `HF_TOKEN` | Hugging Face Access Token | None | Recommended. Increases download rate limits and speed when pulling Whisper weights. |

---

## 4. Running the Application

### Development (Hot-reloaded)
Run the server with Uvicorn. This monitors files for modifications and reloads automatically:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger Documentation**: Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.
- **Health Verification**: Check [http://localhost:8000/health](http://localhost:8000/health) - should return `{"status": "ok"}`.

### Production
For production deployment, run multiple workers without live-reloading:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 5. Local Whisper Model Management

When local media files (such as local-video or local-audio uploads) are submitted, the server will fall back to local `faster-whisper` transcription if online API transcribers are unavailable. 

MilanoLibrary provides specific endpoints to query and download these models on-demand:

1. **Check model status**:
   ```bash
   curl http://localhost:8000/api/models/local
   ```
2. **Trigger background download**:
   ```bash
   curl -X POST http://localhost:8000/api/models/local/small/download
   ```
3. **Query download progress**:
   ```bash
   curl http://localhost:8000/api/models/local/small/status
   ```
   *Response*: `{"status": "downloading", "progress": 42}` or `{"status": "installed", "progress": 100}`.

---

## 6. Troubleshooting

### Local model downloads are slow or timeout
Because models are downloaded from Hugging Face (`Systran/faster-whisper-*`), networks inside restricted regions might experience slow speeds.
- **Solution**: Set the Hugging Face mirror endpoint environment variable before running the server:
  - **Linux/macOS**: `export HF_ENDPOINT=https://hf-mirror.com`
  - **Windows (PowerShell)**: `$env:HF_ENDPOINT="https://hf-mirror.com"`

### `ffmpeg not found` Errors
- Ensure FFmpeg binaries are in your system's PATH.
- Test by running `ffmpeg -version` inside a *new* terminal window.

### GPU acceleration (`cuda`) fails or falls back to CPU
- Make sure you have installed compatible **NVIDIA GPU drivers** and **CUDA Toolkit**.
- Windows systems need `cublas64_12.dll` (or relevant version) and `cudnn_ops_infer64_8.dll` in their system search directories.
- If CUDA execution fails, `faster-whisper` automatically falls back to CPU execution with optimized `int8` quantization. This is a safe fallback and will not crash the pipeline.
