# Backend Quick Start Guide

This guide walks you through setting up, configuring, running, and troubleshooting the FastAPI backend service for MilanoLibrary.

---

## 1. Prerequisites

Before starting, ensure your host system has:
1. **Python 3.11+**: Verify with `python --version`.
2. **FFmpeg**: Vital for extracting audio and probing formats. Confirm `ffmpeg -version` works in your terminal.
3. **Redis Server** (Optional, recommended): For caching results. Managed automatically if deploying via Docker Compose.

---

## 2. Installation

1. Navigate to the backend directory:
   ```bash
   cd backend
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

3. Upgrade pip and install requirements:
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

Open `.env` in an editor. Key environment variables include:

| Environment Variable | Allowed Values | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `OPENAI_API_KEY` | `sk-...` | None | Official OpenAI Key. Required if not using third-party compatible providers. |
| `OPENAI_COMPATIBLE_API_KEY` | `sk-...` | None | Alternative gateway key (e.g. DeepSeek, Groq, OpenRouter). |
| `OPENAI_COMPATIBLE_BASE_URL` | URL | `https://api.openai.com/v1` | Custom base URL for compatible API gateways. |
| `OPENAI_COMPATIBLE_MODEL` | model name | `gpt-4o-mini` | Fallback model name. |
| `LOCAL_WHISPER_MODEL` | `tiny`/`base`/`small`/`medium`/`large-v3` | `small` | Default size downloaded automatically for offline local transcription. |
| `LOCAL_WHISPER_DEVICE` | `auto`, `cuda`, `cpu` | `auto` | Execution hardware. If CUDA driver/dlls are present, defaults to GPU. |
| `LOCAL_WHISPER_COMPUTE_TYPE`| `auto`, `float16`, `int8`, `float32` | `auto` | Precision quantization. CPU is optimized for `int8`. |
| `REDIS_URL` | Redis Connection URI | `redis://localhost:6379` | Connection string for caching. |
| `HF_TOKEN` | Hugging Face Access Token | None | Speeds up Whisper model downloads from Hugging Face Hub. |

---

## 4. Running the Application

### Development (Hot-reloaded)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Swagger UI**: Access interactive endpoints at [http://localhost:8000/docs](http://localhost:8000/docs).
- **Health Check**: Verify running state at [http://localhost:8000/health](http://localhost:8000/health).

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 5. Local Whisper Model Management

When local media is uploaded, the backend falls back to local `faster-whisper` transcription if online Whisper APIs are unavailable. You can manage models via the following endpoints:

1. **Check local model status**:
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

### Local model downloads are extremely slow or fail
Because models are downloaded from Hugging Face Hub, connections in certain restricted regions can experience timeouts.
- **Solution**: Set the Hugging Face mirror endpoint environment variable before starting uvicorn:
  - **Linux/macOS**: `export HF_ENDPOINT=https://hf-mirror.com`
  - **Windows (PowerShell)**: `$env:HF_ENDPOINT="https://hf-mirror.com"`

### `ffmpeg not found` Errors
- Ensure FFmpeg binaries are in your system's PATH.
- Test by running `ffmpeg -version` inside a *new* terminal window.

### GPU acceleration (`cuda`) fails or falls back to CPU
- Ensure you have compatible **NVIDIA GPU drivers** and **CUDA Toolkit** installed.
- Windows environments require `cublas64_12.dll` (or related version) and `cudnn_ops_infer64_8.dll` in their search directories.
- If CUDA execution fails, `faster-whisper` automatically falls back to CPU execution with optimized `int8` quantization, ensuring the pipeline completes safely.
