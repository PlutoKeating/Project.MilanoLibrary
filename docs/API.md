# MilanoLibrary API Specification Reference

This document provides a comprehensive, accurate reference for all REST API endpoints offered by the MilanoLibrary backend service.

---

## Service Configuration

- **Default Base URL**: `http://localhost:8000`
- **Content-Type**: Standard JSON requests must send `Content-Type: application/json`.
- **Multipart Content-Type**: File upload endpoint requires `multipart/form-data`.

---

## 1. System & Settings Endpoints

### Health Check
Check if the backend server is running and responsive.
- **Method**: `GET`
- **Path**: `/health`

#### Response (200 OK)
```json
{
  "status": "ok"
}
```

---

### Get Active Book Directory
Gets the currently active directory path where MilanoBooks are stored on the host.
- **Method**: `GET`
- **Path**: `/api/books/settings/root`

#### Response (200 OK)
```json
{
  "root_dir": "C:/Users/WilliamHVollita/MilanoVault"
}
```

---

### Update Active Book Directory
Changes the active root book vault folder dynamically.
- **Method**: `POST`
- **Path**: `/api/books/settings/root`
- **Request Body**:
```json
{
  "path": "C:/Users/WilliamHVollita/NewMilanoVault"
}
```

#### Response (200 OK)
```json
{
  "root_dir": "C:/Users/WilliamHVollita/NewMilanoVault"
}
```

---

### Browse Directories
File-system explorer utility to browse directories under the active or specific directory.
- **Method**: `GET`
- **Path**: `/api/books/settings/browse`
- **Query Parameters**:
  - `path` (Optional): Directory path to browse. Defaults to user's home directory.

#### Response (200 OK)
```json
{
  "current_path": "C:/Users/WilliamHVollita",
  "parent_path": "C:/Users",
  "subdirs": [
    "Documents",
    "Downloads",
    "Desktop",
    "MilanoVault"
  ]
}
```

---

## 2. Platform Adapter Endpoints

### List Adapters
Lists all platform adapters currently registered in the system (e.g., youtube, bilibili).
- **Method**: `GET`
- **Path**: `/api/adapters`

#### Response (200 OK)
```json
[
  {
    "service_id": "youtube",
    "label": "YouTube Scraper",
    "is_builtin": true
  },
  {
    "service_id": "bilibili",
    "label": "Bilibili Scraper",
    "is_builtin": true
  }
]
```

---

### Upload Custom Adapter
Uploads a custom Python scrapers file (`.py`) inheriting from `BaseAdapter`.
- **Method**: `POST`
- **Path**: `/api/adapters/upload`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Python file binary.

#### Response (200 OK)
```json
{
  "success": true,
  "service_id": "my_custom_platform"
}
```

---

### Delete Custom Adapter
Deletes an uploaded platform adapter script.
- **Method**: `DELETE`
- **Path**: `/api/adapters/{service_id}`

#### Response (200 OK)
```json
{
  "success": true
}
```

---

## 3. Summarization & Status Pipelines

### Submit Online URL Pipeline
Submits an online video link (BV/AV Bilibili URL, YouTube URL, etc.) to start a background compiler task.
- **Method**: `POST`
- **Path**: `/api/summarize`
- **Request Body Schema**:
```json
{
  "video_config": {
    "video_id": "BV1fX4y1Q7Ux",
    "service": "bilibili",
    "page_number": "1",
    "task_id": "task_12345678",
    "book_id": "book_20260524_152211"
  },
  "user_config": {
    "user_key": "sk-your-openai-compatible-key",
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4o-mini"
  }
}
```

#### Response (200 OK)
```json
{
  "task_id": "task_12345678",
  "book_id": "book_20260524_152211",
  "message": "Pipeline started in background"
}
```

---

### Upload Local Media Pipeline
Uploads local audio/video file and initiates the background compiler task.
- **Method**: `POST`
- **Path**: `/api/video/upload`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Media binary file (MP4, MP3, WAV, MKV).
  - `video_config` (Stringified JSON): Matching `video_config` structure in `/api/summarize`.
  - `user_config` (Stringified JSON, Optional): Matching `user_config` structure in `/api/summarize`.

#### Response (200 OK)
```json
{
  "task_id": "task_87654321",
  "book_id": "book_20260524_153300",
  "message": "Pipeline started in background"
}
```

---

### Query Pipeline Task Progress
Queries the real-time status, execution steps percentage, and log messages of a background compiler task.
- **Method**: `GET`
- **Path**: `/api/status/{task_id}`

#### Response (200 OK)
```json
{
  "task_id": "task_12345678",
  "media_type": "url",
  "book_id": "book_20260524_152211",
  "steps": [
    { "step": "fetch_metadata", "status": "completed", "progress": 100, "message": "已成功获取平台元数据: Transformer原理详解" },
    { "step": "download_video", "status": "completed", "progress": 100, "message": "视频流数据下载完成，即将进行音频提取" },
    { "step": "extract_audio", "status": "completed", "progress": 100, "message": "视频语音/字幕获取完成" },
    { "step": "transcribe", "status": "completed", "progress": 100, "message": "视频语音转文字提取完成" },
    { "step": "detect_chapters", "status": "completed", "progress": 100, "message": "已成功生成视频全景语义大纲树" },
    { "step": "segment_video", "status": "completed", "progress": 100, "message": "已成功完成内存逻辑分片，共规划 3 个叶子端点" },
    { "step": "process_segments", "status": "running", "progress": 66.6, "message": "正在分析分段音视频... 已完成 (2/3)" },
    { "step": "compose_summary", "status": "pending", "progress": 0, "message": "等待分段提炼完成..." }
  ]
}
```

---

## 4. MilanoBook Storage Endpoints

### List Books
Lists all books present inside the active vault directory.
- **Method**: `GET`
- **Path**: `/api/books`

#### Response (200 OK)
```json
{
  "books": [
    {
      "id": "book_20260524_152211",
      "title": "Transformer原理详解",
      "author": "未知作者",
      "description": "关于Transformer多头注意力机制的详细解剖总结...",
      "source_url": "https://www.bilibili.com/video/BV...",
      "media_type": "link",
      "media_path": null,
      "audio_path": null,
      "duration_seconds": 600.0,
      "created_at": "2026-05-24T15:22:11.123456",
      "updated_at": "2026-05-24T15:23:45.654321"
    }
  ]
}
```

---

### Create Placeholder Book
Creates an empty book placeholder with custom details.
- **Method**: `POST`
- **Path**: `/api/books`
- **Request Body**:
```json
{
  "title": "My Empty Notebook",
  "author": "Anonymous",
  "description": "An optional description"
}
```

#### Response (201 Created)
```json
{
  "id": "book_20260524_154500_4abc8f",
  "title": "My Empty Notebook",
  "author": "Anonymous",
  "description": "An optional description",
  "source_url": null,
  "media_type": "local",
  "media_path": null,
  "audio_path": null,
  "duration_seconds": 0.0,
  "created_at": "2026-05-24T15:45:00.123456",
  "updated_at": "2026-05-24T15:45:00.123456"
}
```

---

### Get Book Metadata
- **Method**: `GET`
- **Path**: `/api/books/{book_id}`

#### Response (200 OK)
Returns the lightweight book dictionary matching list items.

---

### Update Book Metadata
- **Method**: `PUT`
- **Path**: `/api/books/{book_id}`
- **Request Body**:
```json
{
  "title": "New Title",
  "author": "New Author",
  "description": "New description text"
}
```

#### Response (200 OK)
Returns the updated book dictionary.

---

### Delete Book
Permanently deletes the entire folder of a book under the active root directory.
- **Method**: `DELETE`
- **Path**: `/api/books/{book_id}`

#### Response (200 OK)
```json
{
  "success": true
}
```

---

### Read Book Complete Markdown
Reads the pre-assembled complete markdown document (`complete.md`) file of the book.
- **Method**: `GET`
- **Path**: `/api/books/{book_id}/content`

#### Response (200 OK)
```json
{
  "content": "# Summary\n\n关于Transformer多头注意力机制的详细解剖总结...\n\n# 一、 注意力计算公式\n\n$Attention(Q, K, V) = softmax(\\frac{QK^T}{\\sqrt{d_k}})V$\n..."
}
```

---

### Read Book Outline Tree Index
Reads the book index JSON structures (`index.json`).
- **Method**: `GET`
- **Path**: `/api/books/{book_id}/index`

#### Response (200 OK)
```json
{
  "title": "Transformer原理详解",
  "overall_summary": "关于Transformer多头注意力机制的详细解剖总结...",
  "outline": [
    {
      "id": "seg_f1g2h3",
      "uuid": "seg_f1g2h3",
      "title": "什么是注意力机制",
      "has_subchapters": false,
      "start_seconds": 0.0,
      "end_seconds": 120.0
    },
    {
      "id": "node_8ff",
      "title": "多头注意力机制",
      "has_subchapters": true,
      "children": [
        {
          "id": "seg_z9x8c7",
          "uuid": "seg_z9x8c7",
          "title": "公式拆解与QKV映射",
          "has_subchapters": false,
          "start_seconds": 120.0,
          "end_seconds": 360.0
        }
      ]
    }
  ]
}
```

---

### Recompile Book Complete Markdown
Force-triggers the DFS assembly to stitch leaf node Markdown summaries into `complete.md`.
- **Method**: `POST`
- **Path**: `/api/books/{book_id}/compile`

#### Response (200 OK)
```json
{
  "success": true
}
```

---

## 5. Study Notes Aggregator Endpoints

### Create Integrated Study Note
Compiles/synthesizes summaries and technical concepts across multiple chosen books.
- **Method**: `POST`
- **Path**: `/api/notes`
- **Request Body**:
```json
{
  "book_ids": [
    "book_20260524_152211",
    "book_20260524_154500"
  ],
  "user_prompt": "分析这两个视频中涉及的大语言模型多卡训练、并行的异同之处。"
}
```

#### Response (200 OK)
```json
{
  "id": "note_20260524_163311_f1g2h3",
  "book_ids": ["book_20260524_152211", "book_20260524_154500"],
  "content": "# 整合学习笔记\n\n## 1. 核心知识点总结\n...",
  "user_prompt": "分析这两个视频中涉及的大语言模型多卡训练、并行的异同之处。",
  "created_at": "2026-05-24T16:33:11.123456"
}
```

---

### List Notes
Lists all generated study notes under the `.notes/` subfolder.
- **Method**: `GET`
- **Path**: `/api/notes`

#### Response (200 OK)
```json
{
  "notes": [
    {
      "id": "note_20260524_163311_f1g2h3",
      "book_ids": ["book_20260524_152211", "book_20260524_154500"],
      "content": "...",
      "user_prompt": "...",
      "created_at": "2026-05-24T16:33:11.123456"
    }
  ]
}
```

---

### Delete Note
- **Method**: `DELETE`
- **Path**: `/api/notes/{note_id}`

#### Response (200 OK)
```json
{
  "success": true
}
```

---

## 6. Local Whisper Model Endpoints

### List Local Models
Lists installation statuses of all faster-whisper models weights.
- **Method**: `GET`
- **Path**: `/api/models/local`

#### Response (200 OK)
```json
{
  "models": [
    { "name": "tiny", "label": "Tiny", "size": "~39MB", "installed": true },
    { "name": "small", "label": "Small", "size": "~466MB", "installed": false }
  ]
}
```

---

### Trigger Model Download
Triggers background downloading of specific model weight packages.
- **Method**: `POST`
- **Path**: `/api/models/local/{model_name}/download`

#### Response (200 OK)
```json
{
  "status": "started",
  "message": "Download started for small"
}
```

---

### Query Model Download Status
- **Method**: `GET`
- **Path**: `/api/models/local/{model_name}/status`

#### Response (200 OK)
```json
{
  "status": "downloading",
  "progress": 42.5
}
```

---

## 7. Cache Management Endpoints

### Clear All Cache
Clears Redis caching results.
- **Method**: `DELETE`
- **Path**: `/api/cache`

#### Response (200 OK)
```json
{
  "success": true,
  "deleted": 12,
  "message": "Successfully cleared 12 cache keys.",
  "error": null
}
```
