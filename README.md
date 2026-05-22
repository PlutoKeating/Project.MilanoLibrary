# Project.MilanoLibrary

复古未来主义极简风格的 AI 视频与本地媒体总结工具。支持 Bilibili、YouTube 视频链接，以及本地视频/音频文件上传总结。内置本地 Whisper 语音转录引擎。

## 核心特性

- **多平台支持**：支持 Bilibili 视频、YouTube 视频、播客、本地视频（`local-video`）及本地音频（`local-audio`）的一键总结。
- **混合转录引擎**：支持在线 OpenAI Whisper API；同时内置本地 `faster-whisper` 离线转录引擎作为 Fallback 或纯离线运行。
- **本地模型管理**：提供本地 Whisper 模型（`tiny`, `base`, `small`, `medium`, `large-v3`）的在线一键下载与进度查询 API。
- **流式输出**：支持极速的 LLM 总结流式渲染，字字可见。
- **结构化总结**：基于 JSON Schema 结构化输出（Structured Outputs），确保大模型输出的稳定结构。
- **章节感知**：支持自动解析 YouTube 描述章节、Bilibili 多 P 结构，并支持通过 LLM 从字幕中智能检测视频章节大纲。
- **复古未来设计**：暗黑极简像素风、JetBrains Mono 字体、无圆角、无玻璃态、无冗余动画。

---

## 架构

```
┌─────────────┐      HTTP/API       ┌─────────────┐
│   前端      │ ◄─────────────────► │   后端      │
│  Next.js    │   /api/summarize    │   FastAPI   │
│  (React)    │   /api/video/upload │   (Python)  │
└─────────────┘                     └─────────────┘
                                           │
                                    ┌──────┴────────────────┐
                                    │ ├─ OpenAI / 兼容 API   │
                                    │ ├─ Bilibili/YouTube   │
                                    │ ├─ 本地 faster-whisper│
                                    │ └─ Redis (缓存)        │
                                    └───────────────────────┘
```

---

## 快速开始

### 1. 配置环境变量

```bash
# 前端环境变量
cp frontend/.env.example frontend/.env

# 后端环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，至少配置你的 OPENAI_API_KEY
```

### 2. 启动后端

```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# macOS/Linux:
# ./venv/bin/pip install -r requirements.txt
# ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端服务启动于 http://localhost:8000

### 3. 启动前端

```bash
cd frontend
npm ci
npm run dev
```

前端服务启动于 http://localhost:3000

---

## Docker 部署 (推荐)

使用 Docker Compose 可以一键部署完整的服务（包括 Redis 缓存）：

```bash
docker compose up -d --build
```

这会启动三个服务：

- `milanolibrary-frontend` — Next.js (默认映射端口 `3000`)
- `milanolibrary-backend` — FastAPI (默认映射端口 `8000`)
- `milanolibrary-redis` — Redis (默认映射端口 `6379`)

> 如需自定义暴露的端口或传入参数，编辑根目录 `.env` 或 `backend/.env` / `frontend/.env` 即可。

---

## 技术栈

### 前端技术栈

- **框架**：Next.js 16 (Pages Router) + React 18 + TypeScript (Strict 严格模式)
- **样式**：Tailwind CSS (复古未来主义定制设计)
- **表单与校验**：React Hook Form + Zod
- **Markdown 渲染**：marked-react

### 后端技术栈

- **框架**：FastAPI + Python 3.11+
- **转录引擎**：OpenAI Whisper API + 本地 `faster-whisper` (CTranslate2)
- **大模型驱动**：`openai` Python SDK (全面兼容任何第三方 OpenAI 格式的 API 接口)
- **音视频处理**：`ffmpeg` + `av` / `pydub` (支持分段分片智能总结)
- **缓存引擎**：Redis / Upstash (支持对高频视频总结进行即时结果复用)

---

## API 端点一览

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| **GET** | `/health` | 健康检查 |
| **POST** | `/api/summarize` | URL 视频总结 (Bilibili/YouTube，支持流式) |
| **POST** | `/api/video/upload` | 本地视频/音频上传，自动通过 Whisper 转录并流式总结 |
| **DELETE** | `/api/cache` | 彻底清空后端所有总结缓存 |
| **GET** | `/api/models/local` | 获取本地 Whisper 模型列表及各自的下载/安装状态 |
| **POST** | `/api/models/local/{name}/download` | 后台触发下载指定的本地 Whisper 模型 |
| **GET** | `/api/models/local/{name}/status` | 查询指定本地 Whisper 模型的下载进度 |

> 完整的 API 输入/输出定义与示例，请阅读 [docs/API.md](./docs/API.md)。

---

## 视觉与交互风格

**复古未来主义极简风 (Retro-futurism Minimalism):**

- **主色调**：背景色为深空黑 `#0a0a0f`，组件边框为暗蓝灰色 `#1e293b`
- **霓虹点缀**：高亮文字/主按钮采用霓虹青 `#00f0ff`，警告/异常/特殊点缀采用霓虹品红 `#ff00a0`
- **等宽字体**：全站强制使用 JetBrains Mono 字体
- **绝对直角**：禁止使用任何圆角 (no `rounded-*` corners) 与渐变/毛玻璃效果
- **瞬时反馈**：除必要的过渡动效外，消除一切冗余花哨的动画
