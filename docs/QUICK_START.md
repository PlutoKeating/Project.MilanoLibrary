# MilanoLibrary 快速启动与使用指南

> 复古等宽极简主义风格 | 无数据库文件化视频知识库 | 3 阶段 AI 重组编译器 | 多书聚合笔记 | 插件化平台适配器

---

## 目录

- [一、配置要求](#一、配置要求)
- [二、环境变量配置](#二、环境变量配置)
- [三、Docker Compose 一键部署 (推荐)](#三、docker-compose-一键部署-推荐)
- [四、宿主机手动运行 (开发调试)](#四、宿主机手动运行-开发调试)
- [五、核心模块功能与使用指南](#五、核心模块功能与使用指南)
  - [1. 挂载 Obsidian 书籍根目录](#1-挂载-obsidian-书籍根目录)
  - [2. 编译第一本米兰之书 (MilanoBook)](#2-编译第一本米兰之书-milanobook)
  - [3. 自定义适配器热插拔](#3-自定义适配器热插拔)
  - [4. 跨书聚合智能笔记 (Aggregator)](#4-跨书聚合智能笔记-aggregator)
  - [5. 本地 Whisper 离线转录与模型一键下载](#5-本地-whisper-离线转录与模型一键下载)
- [六、排产与故障排查](#六、排产与故障排查)

---

## 一、配置要求

| 运行模态 | 推荐版本 | 最低版本 | 说明 |
| :--- | :--- | :--- | :--- |
| **Docker** | 24.0.0+ | 20.10+ | 容器引擎 |
| **Docker Compose** | 2.22.0+ | 2.20+ | 编排工具 |
| **Python** | 3.11.x | 3.10 | 手动启动后端所需 |
| **Node.js** | 20.x | 18.x | 手动启动前端所需 |
| **FFmpeg** | 6.0+ | 4.4 | 用于音频属性分析与高精度转录格式化 |

---

## 二、环境变量配置

启动前，分别进入 `frontend` 和 `backend` 目录，将各自的 `.env.example` 复制为 `.env`。

### 1. 后端配置 `backend/.env`
```env
# OpenAI 官方 API 密钥 (可选)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxx

# 自定义 OpenAI 兼容中转配置 (推荐，如 DeepSeek、OpenRouter 等)
OPENAI_COMPATIBLE_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com/v1
OPENAI_COMPATIBLE_MODEL=gpt-4o-mini

# 本地 Whisper 模型下载预设 (支持 tiny, base, small, medium, large-v3)
LOCAL_WHISPER_MODEL=small
LOCAL_WHISPER_DEVICE=auto
LOCAL_WHISPER_COMPUTE_TYPE=auto

# 缓存与网络
REDIS_URL=redis://localhost:6379
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
```

### 2. 前端配置 `frontend/.env`
```env
# 连接的后端 FastAPI 根路径
NEXT_PUBLIC_API_URL=http://localhost:8000
FRONTEND_PORT=3000
```

---

## 三、Docker Compose 一键部署 (推荐)

在项目根目录下执行以下命令，一键编译并启动前端、后端、Redis 缓存服务：
```bash
docker compose up -d --build
```

### 服务运行地址：
- **前端控制台 UI**: [http://localhost:3000](http://localhost:3000)
- **后端 Swagger API 交互文档**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **后端健康检测**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 四、宿主机手动运行 (开发调试)

### 1. 启动后端 (FastAPI)
确保宿主机已经全局安装 `FFmpeg` 并在系统环境变量中 (可运行 `ffmpeg -version` 验证)。

```bash
cd backend
python -m venv venv

# Windows (PowerShell/CMD) 激活并安装运行：
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# macOS/Linux 激活并安装运行：
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 启动前端 (Next.js)
```bash
cd frontend
npm ci
npm run dev
```
打开浏览器访问 [http://localhost:3000](http://localhost:3000) 即可进行前端开发或应用体验。

---

## 五、核心模块功能与使用指南

### 1. 挂载 Obsidian 书籍根目录
1. 访问前端控制台，在顶部 **OBSIDIAN ROOT VAULT PATH** 配置框中，可以看到当前挂载的物理存储根目录。
2. 点击 **BROWSE...** 按钮，会调出极简定制的 **磁盘文件浏览器 (FileExplorer)**，支持跨盘符、跨级目录层层下探。
3. 选择你期望作为本地知识库或 Obsidian 库的目录，点击底部的选定路径，系统会自动保存配置、读取其中已有的米兰之书并刷新书架。

### 2. 编译第一本米兰之书 (MilanoBook)
1. 在书架点击 **[ NEW VAULT ] 创建新书籍**，会初始化并打开一个新书的编译调度终端。
2. 可以在面板中提交：
   - **在线 URL** (Bilibili/YouTube 视频链接)
   - **本地音视频文件** (拖拽或点击上传 `.mp4`, `.mp3`, `.wav` 等格式文件)
3. 点击 **EXECUTE SUMMARY** 启动流水线，右侧会显示实时追踪的后台编译进度条，完整流程包括：
   - 获取元数据 (`fetch_metadata` / `upload_file`)
   - 下载流媒体并标准化音频轨提取 (`download_video` / `extract_audio`)
   - 提取或 Whisper 转录高保真音轨文本 (`transcribe`)
   - **Phase 1: 全景大纲生成**：大模型智能切片，生成语义树状章节目录 (`detect_chapters`)
   - **Phase 2: 并行提炼**：规整内存分片，多线程高并发总结各叶子节点大纲内容 (`process_segments`)
   - **Phase 3: 深度优先合并**：将生成的叶子节点 Markdown 文档递归组装，写入 `complete.md` (`compose_summary`)。
4. 编译完成后，前端会即时渲染出左侧为带有跳转功能的**等宽树状大纲目录**、右侧为**高解析学术级 Markdown 渲染正文**的多功能阅读面板。

### 3. 自定义适配器热插拔
1. 在提交多媒体面板底部，点击 **[ADAPTERS]** 按钮，可查看当前后端内置和上传的平台视频抓取适配器。
2. 你可以编写自定义 Python 脚本（继承自 `backend/app/adapters/base.py` 的 `BaseAdapter`），并在页面中一键上传。系统会即时载入并将其注入可供选用的服务平台字典中。

### 4. 跨书聚合智能笔记 (Aggregator)
1. 切换至 **[AGGREGATOR // 多书整合]** 面板。
2. 在左侧列表中多选已经提炼完成的 MilanoBooks。
3. 在右侧输入框中编写你期望提炼的整合性综合指令 (例如：*“深度对比这三个视频在 Transformer 演化路径以及未来发展方向上的异同，并提炼关键公式与研究细节。”*)。
4. 点击启动聚合。大模型在后台会秒级抓取多本书的大纲和正文进行跨领域融合重组，生成极其详尽、学术级的系统化知识笔记，存储于书籍根目录下的 `.notes/` 文件夹。
5. 自动跳转至 **[STUDY NOTES // 智能笔记]** 目录，即可进行沉浸式 Markdown 阅读或一键复制 MD 正文。

### 5. 本地 Whisper 离线转录与模型一键下载
1. 对于本地上传的媒体或无自带字幕的在线视频，系统首选调用在线 Whisper API 转录。若未提供 Key 或转录出错，会自动回退至本地离线 `faster-whisper` 模型转录。
2. 前端切换 **Local** 推理，选择预期的模型尺寸 (`tiny`, `base`, `small`, `medium`, `large-v3`)，点击 **DOWNLOAD**，后端会自动开启多线程后台下载，并在配置卡上实时反馈下载百分比。

---

## 六、故障排查

### 1. 提示 “未安装 FFmpeg 依赖”
- 手动启动后端时，请务必保证执行命令行的终端下运行 `ffmpeg -version` 和 `ffprobe -version` 无报错。Windows 系统推荐安装后将其 bin 目录添加进系统高级环境变量 PATH，并**重启终端**以生效。

### 2. 磁盘文件浏览器 (Browse) 无法访问某些路径
- 容器化部署时，出于安全性考虑，系统默认只能浏览和挂载挂载卷挂载出的目录（如 Docker 的 `/host_home`）。如需访问整个宿主机，请确保在根目录 `.env` 或 `docker-compose.yml` 中正确配置了宿主机家路径到容器内部的映射。

### 3. 本地 Whisper 模型下载极慢或失败
- 默认需要从 Hugging Face 镜像拉取权重，国内网络可能存在延迟。
- **解决方式**：启动后端前，在系统命令行执行以下命令设置中转站加速：
  - **macOS/Linux**: `export HF_ENDPOINT=https://hf-mirror.com`
  - **Windows (PowerShell)**: `$env:HF_ENDPOINT="https://hf-mirror.com"`
- 在 Docker 容器中运行时，可通过在 `backend/.env` 中配置 `HF_TOKEN` 或传入中国境内的代理链接加速。
