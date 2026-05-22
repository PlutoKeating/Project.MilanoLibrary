# Project.MilanoLibrary 快速启动与使用指南

> 前后端分离架构 | Docker 一键部署 | 本地 Whisper 语音转录与模型一键下载 | 复古未来主义极简风

---

## 目录

- [功能概览](#功能概览)
- [环境要求](#环境要求)
- [目录结构](#目录结构)
- [配置环境变量](#配置环境变量)
- [Docker 部署](#docker-部署)
  - [一键启动](#一键启动)
  - [服务地址](#服务地址)
  - [查看状态与日志](#查看状态与日志)
  - [重启与更新](#重启与更新)
  - [完全清理与重置](#完全清理与重置)
- [本地开发独立启动](#本地开发独立启动)
  - [后端独立启动](#后端独立启动)
  - [前端独立启动](#前端独立启动)
- [使用指南](#使用指南)
  - [URL 视频总结](#url-视频总结)
  - [本地视频/音频上传总结](#本地视频音频上传总结)
  - [本地 Whisper 离线转录与模型下载](#本地-whisper-离线转录与模型下载)
  - [清除缓存](#清除缓存)
- [API 常用端点参考](#api-常用端点参考)
- [故障排查](#故障排查)

---

## 功能概览

MilanoLibrary 支持多种源头的视频/音频媒体总结：

| 方式 | 输入源 | 字幕/语音文本来源 | 运行要求 |
| :--- | :--- | :--- | :--- |
| **Bilibili 视频** | 视频/多 P 链接 | 提取官方或 Bilibili 自动生成的字幕 | 需要配置 AI 总结模型与 Key |
| **YouTube 视频** | 视频 URL | 提取官方字幕 / 通过 savesubs 抓取 | 需要配置 AI 总结模型与 Key |
| **本地媒体上传** | 本地视频/音频文件 | **在线 Whisper API** 或 **本地 faster-whisper** 离线转录 | 需要配置 AI 总结模型与 Key |

---

## 环境要求

| 工具 | 推荐版本 | 最低版本 | 说明 |
| :--- | :--- | :--- | :--- |
| **Docker** | 24.0.0+ | 20.10+ | 容器运行时引擎 |
| **Docker Compose** | 2.22.0+ | 2.20+ | 多容器编排工具 |
| **Python** | 3.11.x | 3.10 | 仅在非 Docker 独立运行后端时需要 |
| **Node.js** | 20.x | 18.x | 仅在非 Docker 独立运行前端时需要 |

---

## 目录结构

```
Project.MilanoLibrary/
├── frontend/                   # Next.js 前端应用
│   ├── pages/                  # Pages Router 路由入口 (包含 catch-all [[...slug]].tsx)
│   ├── components/             # 复古极简 UI 组件 (ModelSelector, SummaryResult, UserKeyInput 等)
│   ├── hooks/                  # 自定义 Hook 逻辑 (useSummarize, useModelManager, useClearCache)
│   ├── lib/                    # 公共 TypeScript 类型与 API 配置
│   ├── utils/                  # 纯辅助函数与 Zod 校验 Schema
│   └── styles/                 # Tailwind CSS 样式文件与 Markdown 专有排版
│
├── backend/                    # FastAPI 后端应用
│   ├── app/
│   │   ├── main.py             # 接口路由整合与 CORS 注册入口
│   │   ├── config.py           # 基于 Pydantic Settings 的环境变量读取
│   │   ├── models.py           # 输入输出 API 字段校验 (VideoConfig, UserConfig 等)
│   │   ├── routers/            # 分组路由层 (summarize, upload, cache, models)
│   │   └── services/           # 核心业务服务层
│   │       ├── subtitles.py    # 字幕获取与分发逻辑
│   │       ├── local_whisper.py# 本地 faster-whisper 转录器与后台模型管理
│   │       ├── openai_client.py# 官方与兼容 API LLM 调用和流式生成
│   │       ├── video_ingest.py # 视频/音频上传文件预处理、格式检测与保存
│   │       ├── video_segment.py# 基于 FFmpeg 的智能/等长音频分段
│   │       ├── segment_processor.py# 针对音频段落进行转录与初步提炼
│   │       └── composer.py     # 合并段落总结并格式化输出最终 Markdown
│   │
│   ├── models/                 # 本地下载的 faster-whisper 权重存放目录
│   ├── storage/                # 上传视频、临时音频分片的运行时存储
│   └── requirements.txt        # 依赖库列表
│
├── docker-compose.yml          # Docker 一键编排文件 (整合 include 功能)
└── README.md                   # 全局说明文档
```

---

## 配置环境变量

### 1. 复制模板

```bash
# 前端环境变量
cp frontend/.env.example frontend/.env

# 后端环境变量
cp backend/.env.example backend/.env
```

### 2. 配置说明

#### `backend/.env`
- **`OPENAI_API_KEY`**：你的官方 OpenAI API Key，可用于大模型总结和在线 Whisper 转录。
- **`OPENAI_COMPATIBLE_API_KEY`**：第三方/自定义 OpenAI 兼容平台的 Key。
- **`OPENAI_COMPATIBLE_BASE_URL`**：第三方平台的基础 URL（默认 `https://api.openai.com/v1`）。
- **`OPENAI_COMPATIBLE_MODEL`**：默认使用的总结模型名称（默认 `gpt-4o-mini`）。
- **`LOCAL_WHISPER_MODEL`**：默认使用的本地 Whisper 模型名称（可选 `tiny`, `base`, `small`, `medium`, `large-v3`，默认 `small`）。
- **`LOCAL_WHISPER_DEVICE`**：运行设备（支持 `auto`, `cuda`, `cpu`）。
- **`LOCAL_WHISPER_COMPUTE_TYPE`**：推理精度（支持 `auto`, `float16`, `int8`, `float32`）。
- **`HF_TOKEN`**：可选。你的 Hugging Face Token，设置后可极大加快本地 Whisper 模型文件的下载速度并避免速率限制。

---

## Docker 部署

### 一键启动

在根目录下执行：

```bash
docker compose up -d --build
```

该命令将自动拉取基础镜像，并在后端容器中挂载本地 `./backend/models` 用于存储下载的 Whisper 权重，在前端容器中运行 Next.js 生产环境，同时启动一个 Redis 服务用于结果缓存。

### 服务地址

| 服务 | 访问地址 | 说明 |
| :--- | :--- | :--- |
| **前端主页** | [http://localhost:3000](http://localhost:3000) | 用于提交视频链接、上传文件并查看总结结果 |
| **后端 API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI，可直接测试各个接口 |
| **后端 Health** | [http://localhost:8000/health](http://localhost:8000/health) | 返回 `{"status": "ok"}` 证明后端健康运行中 |

### 查看状态与日志

```bash
# 查看所有服务的运行状态
docker compose ps

# 实时追踪所有服务的控制台日志
docker compose logs -f

# 仅看后端/前端日志
docker compose logs -f backend
docker compose logs -f frontend
```

### 重启与更新

```bash
# 重启所有容器
docker compose restart

# 如果你修改了后端 Python 代码，仅重启或重新构建后端：
docker compose up -d --build backend

# 如果你修改了前端 React 代码，重新构建并部署前端：
docker compose up -d --build frontend
```

### 完全清理与重置

```bash
# 停止容器并删除临时容器网络
docker compose down

# 彻底清理：停止容器、删除网络、删除缓存 Redis 挂载卷
docker compose down -v
```

---

## 本地开发独立启动

如果你不想使用 Docker 部署，也可以在物理机上分别独立启动：

### 后端独立启动

1. 安装 `FFmpeg`，并确保 `ffmpeg` 命令在系统 PATH 路径中。
2. 进入 backend 文件夹：
   ```bash
   cd backend
   python -m venv venv
   ```
3. 激活虚拟环境：
   - **Windows (CMD/PowerShell)**: `.\venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`
4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
5. 运行：
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 前端独立启动

1. 进入 frontend 文件夹：
   ```bash
   cd frontend
   ```
2. 安装 NPM 依赖：
   ```bash
   npm ci
   ```
3. 运行本地开发服务器：
   ```bash
   npm run dev
   ```
4. 访问 `http://localhost:3000` 开始开发。

---

## 使用指南

### URL 视频总结

1. 浏览器打开 `http://localhost:3000`。
2. 支持输入以下链接格式：
   - **Bilibili 视频**：`https://www.bilibili.com/video/BV1xx411c7mD`
   - **YouTube 视频**：`https://www.youtube.com/watch?v=xxxxx`
3. 配置右下角的 Prompt 选项（如输出语言、是否显示 Emoji、是否利用 Structured Output 结构化输出等）。
4. 点击 **EXECUTE SUMMARY**。
5. 结果区域会实时接收流式 Markdown，展示最终包含时间戳定位和精彩总结的卡片。

### 本地视频/音频上传总结

1. 点击输入框下方的 **"上传本地视频文件"** 区域，或拖拽视频/音频文件（如 `.mp4`, `.mp3`, `.mkv`, `.wav` 等）。
2. 配置你期望总结的 AI 参数。
3. 点击 **EXECUTE SUMMARY**。
4. 后端接收文件后，将会进行音视频流分离，并开始分片转录与流式处理。

### 本地 Whisper 离线转录与模型下载

上传本地文件后，系统对语音转录的判定流程如下：
1. **在线优先**：若用户提供了有效的 OpenAI API Key 且平台支持音频转录接口，优先调用在线 OpenAI Whisper API 接口，速度最快。
2. **本地回退**：若在线不可用，系统会自动使用 **本地 faster-whisper** 引擎进行离线高精度转录。

#### 本地模型下载
在前端页面的配置区域中：
- 你可以在 **Online / Local** 切换按钮中选择 **Local**，并选择你想要使用的模型（如 `tiny`, `base`, `small`, `medium`, `large-v3`）。
- 点击 **DOWNLOAD** 按钮，后端将会发起后台多线程模型下载，前端可以实时查看到下载百分比进度。下载的模型会存放在 `./backend/models/` 下。

### 清除缓存

- MilanoLibrary 使用 Redis 缓存已总结成功的卡片内容，防止对同一段长视频进行重复的大模型计费。
- 如果想要强制重新总结，可以点击页面上的 **CLEAR CACHE** 按钮，它会向后端发送 `DELETE /api/cache` 请求，清空所有的缓存哈希记录。

---

## API 常用端点参考

详细的请求体与返回体格式请直接访问 [docs/API.md](./docs/API.md) 或 Swagger 页面。

- `POST /api/summarize` — 总结传入的 URL 视频
- `POST /api/video/upload` — 上传本地视频/音频并总结
- `DELETE /api/cache` — 清空全部后端缓存
- `GET /api/models/local` — 查询本地 Whisper 模型列表及状态
- `POST /api/models/local/{model_name}/download` — 触发特定模型后台下载
- `GET /api/models/local/{model_name}/status` — 进度查询

---

## 故障排查

### 1. 本地视频上传报错 `501` "该视频没有字幕，或视频太短"
- **检查**：视频中是否有清晰的人声？如果是纯音乐或背景杂音，转录结果为空时会触发该异常。
- **FFmpeg 依赖**：后端必须有 FFmpeg。如果是在物理机运行非 Docker 后端，请务必在命令行输入 `ffmpeg -version` 确认 FFmpeg 已被正确安装并添加到 PATH 变量。

### 2. 网页显示 `❌ 请求出错: Connection Refused`
- **检查**：后端服务（`8000` 端口）是否已经启动。
- **检查**：如果在前端手动配置了 `Backend Base URL`，确保拼写正确且无多余斜杠（如 `http://localhost:8000`）。
- **检查**：如果是 Docker 运行，前端容器内部默认会去连接环境变量中配置的 `NEXT_PUBLIC_API_URL`。可以在前端 `.env` 文件里修正它并重新构建。

### 3. 本地 Whisper 首次下载模型很慢
- **检查**：由于模型托管在 Hugging Face，国内网络可能存在延迟。
- **解决方式**：建议在 `backend/.env` 配置文件中增加 `HF_TOKEN` 环境变量。此外，如果使用物理机运行，可以在启动前执行 `export HF_ENDPOINT=https://hf-mirror.com` 或在 Docker 环境中添加代理，以加速 huggingface 下载。
