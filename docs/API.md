# MilanoLibrary v2 API Specification Reference

This document provides a comprehensive and accurate reference for all REST API endpoints offered by the MilanoLibrary backend service.

---

## Service Configuration

- **Default Local Base URL**: `http://localhost:8000`
- **Default Production Base URL**: Defined by client-side or environment variables.
- **Content-Type**: All JSON requests must send `Content-Type: application/json`.
- **Streaming Content-Type**: Streaming endpoints return `text/plain; charset=utf-8` with `Cache-Control: no-cache`.

---

## 1. System & Utility Endpoints

### Health Check

Check if the backend server is running and responsive.

- **Method**: `GET`
- **Path**: `/health`
- **Authentication**: None

#### Request Example

```bash
curl http://localhost:8000/health
```

#### Response Example (200 OK)

```json
{
  "status": "ok"
}
```

---

## 2. Summarization Endpoints

### URL-based Video Summarization

Summarize online videos from YouTube or Bilibili by providing their URL metadata. Supports optional streaming mode.

- **Method**: `POST`
- **Path**: `/api/summarize`
- **Authentication**: Optional (Passed inside `user_config`)

#### Request Schema

The request body is a JSON object with two main fields: `video_config` and `user_config` (optional).

##### `video_config` Properties

| Field | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `video_id` | `string` | **Yes** | - | Bilibili video ID (BV/AV) or YouTube Video ID. |
| `service` | `string` | No | `"bilibili"` | Source service. Supported values: `"bilibili"`, `"youtube"`, `"podcast"`, `"meeting"`, `"local-video"`, `"local-audio"`. |
| `page_number` | `string` | No | `null` | Part number for multi-page Bilibili videos. |
| `enable_stream` | `boolean` | No | `true` | If true, streams the text completion word-by-word. Otherwise, returns a single JSON object when finished. |
| `model` | `string` | No | `null` | Specific LLM model to override backend defaults (e.g. `gpt-4o`). |
| `show_timestamp`| `boolean` | No | `false` | Include timestamp indicators `[MM:SS]` inside summary lines. |
| `show_emoji` | `boolean` | No | `true` | Prepend summarized bullets with descriptive emojis. |
| `output_language`| `string` | No | `"zh"` | Code of the target summary language (e.g. `"zh"`, `"en"`, `"ja"`). |
| `use_structured_output` | `boolean` | No | `true` | Instruct LLM to output summary inside strict JSON schema to prevent formatting anomalies. |
| `respect_chapters` | `boolean` | No | `true` | Attempt to auto-detect video chapters (via description or subtitles analysis) and frame the summary within chapters. |
| `model_type` | `string` | No | `"online"` | `"online"` for API key LLMs, or `"local"` for self-hosted instances. |
| `local_model` | `string` | No | `null` | Model name override when using local inference. |

##### `user_config` Properties (Optional)

| Field | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `user_key` | `string` | No | `null` | Client-supplied OpenAI / Custom compatible API key. Overrides backend `.env`. |
| `base_url` | `string` | No | `null` | Base endpoint URL override (e.g., third-party LLM gateways). |
| `model_name` | `string` | No | `null` | Custom Model override requested by the client. |
| `should_show_timestamp` | `boolean` | No | `false` | Client preference on whether to force include timestamps. |

#### Request Example

```json
{
  "video_config": {
    "video_id": "BV1fX4y1Q7Ux",
    "service": "bilibili",
    "enable_stream": false,
    "show_timestamp": true,
    "show_emoji": true,
    "output_language": "zh",
    "use_structured_output": true,
    "respect_chapters": true
  },
  "user_config": {
    "user_key": "sk-example-key-xxxxxxxxxx",
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4o-mini"
  }
}
```

#### Responses

##### Stream-based Response (`enable_stream: true`)
- **Status Code**: `200 OK`
- **Headers**: `Content-Type: text/plain; charset=utf-8`
- **Body**: Streams raw Markdown summary chunks.

##### Non-Stream Response (`enable_stream: false`)
- **Status Code**: `200 OK`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "result": "# 视频总结\n\n- 🌟 核心大纲要点..."
}
```

---

## 3. Local Media Upload Endpoints

### Local Media Upload & Summary

Upload local video or audio files directly to the server, transcribe using online Whisper API or local fallback `faster-whisper`, and generate a structured stream/batch summary.

- **Method**: `POST`
- **Path**: `/api/video/upload`
- **Content-Type**: `multipart/form-data`
- **Authentication**: Optional (Passed inside `user_config` parameter)

#### Form Fields

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | `Binary (File)` | **Yes** | Video or Audio file to upload (MP4, MKV, AVI, MP3, WAV, etc.) |
| `video_config` | `string (JSON String)` | **Yes** | Stringified JSON object matching the `video_config` schema in `/api/summarize`. |
| `user_config` | `string (JSON String)` | No | Stringified JSON object matching the `user_config` schema in `/api/summarize`. |

#### cURL Request Example

```bash
curl -X POST http://localhost:8000/api/video/upload \
  -F "file=@/path/to/my_speech.mp4" \
  -F "video_config={\"enable_stream\":false,\"output_language\":\"en\",\"model_type\":\"online\"}" \
  -F "user_config={\"user_key\":\"sk-xxxxxxxx\"}"
```

#### Responses

Matches the same responses as `/api/summarize` (either raw text streaming or `{"result": "..."}` JSON).

---

## 4. Local Whisper Models Management

Manage offline faster-whisper transcribing models stored in backend filesystem `/app/models/`.

### List Local Models

Returns all available Whisper models and whether they have been fully downloaded and installed locally on the backend.

- **Method**: `GET`
- **Path**: `/api/models/local`
- **Authentication**: None

#### Response Example (200 OK)

```json
{
  "models": [
    {
      "name": "tiny",
      "label": "Tiny",
      "size": "~39MB",
      "installed": true
    },
    {
      "name": "base",
      "label": "Base",
      "size": "~74MB",
      "installed": false
    },
    {
      "name": "small",
      "label": "Small",
      "size": "~466MB",
      "installed": true
    },
    {
      "name": "medium",
      "label": "Medium",
      "size": "~1.5GB",
      "installed": false
    },
    {
      "name": "large-v3",
      "label": "Large V3",
      "size": "~3GB",
      "installed": false
    }
  ]
}
```

---

### Download Local Model

Triggers a background download task for a specific Whisper model size weights.

- **Method**: `POST`
- **Path**: `/api/models/local/{model_name}/download`
- **Path Parameters**:
  - `model_name` (Required): Must be one of `tiny`, `base`, `small`, `medium`, `large-v3`.
- **Authentication**: None

#### Request Example

```bash
curl -X POST http://localhost:8000/api/models/local/small/download
```

#### Response Example (200 OK)

```json
{
  "status": "started",
  "message": "Download started for small"
}
```

---

### Query Model Download Status

Get the current download progress (percentage, state, errors) of a background downloading Whisper model.

- **Method**: `GET`
- **Path**: `/api/models/local/{model_name}/status`
- **Path Parameters**:
  - `model_name` (Required): Must be one of `tiny`, `base`, `small`, `medium`, `large-v3`.
- **Authentication**: None

#### Response Examples

##### Case A: Model already installed
```json
{
  "status": "installed",
  "progress": 100
}
```

##### Case B: Downloading in progress
```json
{
  "status": "downloading",
  "progress": 42,
  "error": null
}
```

##### Case C: Not installed / Not downloaded
```json
{
  "status": "not_installed",
  "progress": 0
}
```

---

## 5. Cache Management Endpoints

### Clear All Cache

Purge all cached summarization results saved inside the Redis/Upstash cache instance to force fresh regeneration.

- **Method**: `DELETE`
- **Path**: `/api/cache`
- **Authentication**: None

#### Request Example

```bash
curl -X DELETE http://localhost:8000/api/cache
```

#### Response Example (200 OK)

```json
{
  "success": true,
  "deleted": 8,
  "message": "Successfully cleared 8 cache keys.",
  "error": null
}
```
