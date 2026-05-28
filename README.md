<div align="center">
  <h1>Project.MilanoLibrary</h1>
  <strong>Database-less Video Vault & Recomposition Compiler</strong><br />
  一个复古未来主义极简风格的、无数据库、本地优先视频知识重组编译器与 Obsidian 原生知识库。
</div>

<div align="center">
  <a href="#-paradigm-shift"><strong>设计范式</strong></a> ·
  <a href="#-core-features"><strong>核心特性</strong></a> ·
  <a href="#-compilation-pipeline"><strong>工作原理</strong></a> ·
  <a href="#-quick-start"><strong>快速开始</strong></a> ·
  <a href="./docs/API.md"><strong>API 规范</strong></a> ·
  <a href="./docs/ARCHITECTURE.md"><strong>架构 spec</strong></a>
</div>

---

## 💡 Paradigm Shift (设计范式)

现有的视频总结工具大多止步于“总结生成”：将大模型的平铺段落输出到关系型数据库中，难以二次沉淀。**MilanoLibrary** 带来了全新的设计范式：

*   **Database-less (无数据库化)**
    摆脱传统数据库束缚，完全基于物理文件系统。所有提炼数据均以符合规范的 `book.json`、`index.json`、`complete.md` 和单独段落 `.md` 文件夹形式存储。数据资产 100% 归属用户。
*   **Obsidian-Native (Obsidian 原生适配)**
    你的书籍根目录即是一个标准的 Obsidian 库 (Vault)。生成的 MilanoBook 与 `.notes` 智能笔记原生完美融入你的双链知识网，支持无缝检索、编辑与链接引用。
*   **Logical Slicing & Recomposition (逻辑分片与重组)**
    摒弃传统的 FFmpeg 物理切割。在内存中通过高精度时间戳范围对字幕进行无损逻辑切片，在保留音视频原有上下文完整性的前提下，实现多线程、超高并发的叶子章节学术级提炼与深度优先重组。

---

## ✨ Core Features (核心特性)

| 特性 | 机制 | 业务优势 |
| :--- | :--- | :--- |
| **多源多平台接入** | 内置 YouTube/Bilibili 适配器 + 拖拽视音频上传 | 无论是公开讲演、技术分享还是本地录音，一网打尽 |
| **自定义适配器** | 插件化 `.py` 热插拔架构，支持前端实时上传/删除 | 开发者可秒级编写并注入任意新音视频平台的视频源抓取服务 |
| **三阶段智能编译** | 大纲建模（Phase 1）→ 并行提炼（Phase 2）→ 递归拼装（Phase 3） | 彻底消除废话与低智重叠，生成包含 LaTeX 公式、标准代码块的学术级书籍 |
| **跨书交叉整合** | 一键多选 MilanoBooks + 综合提示词指示 | 大模型深度重构多视频，提炼异同点与技术路线图，自动编译为系统化笔记 |
| **双向交互阅读器** | 等宽树状目录、精准 Sentence 跳转、嵌入式 HTML5 播放器 | 正文 `[MM:SS]` 精准时间戳可一键点击定位媒体播放，实现深度互动阅读 |
| **本地 STT 引擎** | 在线 Whisper 接口 + 本地 `faster-whisper` (CTranslate2) 自动回退 | 无网、无 key 状态下自动启动本地硬件推理加速转录，提供模型一键式下载 |

---

## 🛠️ Compilation Pipeline (工作原理)

MilanoLibrary 将视频的“存”与“重组”抽象为一条高度自动化的后台编译流水线：

```
                    [ 1. Ingest & Analyze ]
            从在线 URL 或本地上传中提取高精度音轨与元数据
                               │
                               ▼
                   [ 2. Resolve Transcript ]
             获取在线字幕 ──► (若无) ──► Whisper 在线 / 本地 STT
                               │
                               ▼
               [ 3. Phase 1: Outline Generation ]
        大模型严格 JSON 约束 ──► 全景嵌套章节大纲树 (outline.json)
                               │
                               ▼
                [ 4. Phase 2: In-Memory Slicing ]
         内存逻辑切片（覆盖全片） ──► 并发多线程 asyncio 提炼
                               │
                               ▼
               [ 5. Phase 3: DFS Assembly Walk ]
      递归深度优先遍历章节树 ──► 拼装生成 100% 格式化 complete.md 书籍
```

---

## 🚀 Quick Start (快速开始)

> [!IMPORTANT]  
> 运行物理机部署前，请确保系统已安装 **FFmpeg** 并将其添加至环境变量。

### 1. 启动 Docker 镜像 (推荐前后端分离部署)

项目已完美分离容器化，可分别进入前端和后端目录，通过 Docker Compose 启动各自服务：

#### 后端与缓存 (FastAPI + Redis)
```bash
cd backend
docker compose up -d --build
```
这会拉起以下两个服务：
*   **后端 API Swagger 文档** — `http://localhost:8000/docs` (FastAPI)
*   **Redis 高频缓存** — `http://localhost:6379` (自动缓存 duplicate 任务，防止重复计费)

#### 前端控制台 (Next.js)
```bash
cd frontend
docker compose up -d --build
```
这会拉起以下服务：
*   **前端控制台 UI** — `http://localhost:3000` (Next.js SPA)

### 2. 物理机手动启动 (本地开发)

#### 后端 (FastAPI)

```bash
cd backend
python -m venv venv

# 激活虚拟环境 (Windows)
.\venv\Scripts\Activate.ps1
# 激活虚拟环境 (macOS/Linux)
source venv/bin/activate

# 安装依赖并运行
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 前端 (Next.js)

```bash
cd frontend
npm ci
npm run dev
```

---

## ⚙️ Configuration (配置规范)

后端通过 `backend/.env` 配置文件进行统一装配。

> [!TIP]
> 如果你想极速下载本地 `faster-whisper` 的推理权重，建议在 `.env` 中添加 `HF_TOKEN`，或在运行前执行中转站映射：
> - **PowerShell**: `$env:HF_ENDPOINT="https://hf-mirror.com"`
> - **Bash**: `export HF_ENDPOINT=https://hf-mirror.com`

```env
# 基础大模型配置
OPENAI_API_KEY=sk-xxxxxx
OPENAI_COMPATIBLE_API_KEY=sk-xxxxxx
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com/v1
OPENAI_COMPATIBLE_MODEL=gpt-4o-mini

# 本地 Whisper 转录引擎预设
LOCAL_WHISPER_MODEL=small
LOCAL_WHISPER_DEVICE=auto
LOCAL_WHISPER_COMPUTE_TYPE=auto

# 端口与挂载
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
REDIS_URL=redis://localhost:6379
```

---

## 📐 Technology Stack (技术架构)

*   **Frontend**: Next.js 16 (Pages Router) · React 18 · TypeScript (Strict) · Tailwind CSS · `react-hook-form-persist` · `ReactMarkdown` (GFM + Math + KaTeX)
*   **Backend**: FastAPI (Async) · Pydantic v2 · CTranslate2 (`faster-whisper`) · FFmpeg / PyAV · Redis / Upstash Redis
