# MilanoLibrary 前端应用

基于 Next.js + React + TypeScript 构建的视频与本地媒体智能总结前端界面。遵循严格的复古未来主义极简美学设计（Retro-futurism Minimalism）。

---

## 核心特性

- **跨平台视频提取**：支持快速解析并提交 Bilibili 和 YouTube 视频 URL。
- **本地文件拖拽上传**：集成 Drag & Drop 上传本地视频/音频文件到后端。
- **配置持久化**：使用 `react-hook-form-persist` 将用户的所有表单首选项（输出语言、是否显示 Emoji、时间戳等）自动持久化在浏览器的 `localStorage` 中。
- **本地 Whisper 下载控制器**：支持实时连接后端 Model Manager API，切换 Online/Local，后台一键下载各级别 Whisper 模型权重并实时刷新进度。
- **流式响应渲染**：基于 `marked-react` 与 React Stream Reader 逐字渲染 LLM 的 Markdown 输出。
- **智能交互时间戳**：自动解析文本中的 `[MM:SS]` 时间戳，点击时间戳可直接拉取并定位到对应媒体位置（Sentence 级别的精准交互）。
- **完全客户端渲染**：绝不使用 Next.js API Routes，所有大模型调用、音视频分片与转录均通过暴露的 `NEXT_PUBLIC_API_URL` 直连 FastAPI 后端。

---

## 目录结构

```
frontend/
├── components/             # React UI 组件
│   ├── Header.tsx          # 头部像素风 H1
│   ├── Footer.tsx          # 底部信息栏
│   ├── SubmitButton.tsx    # 带 Loading 状态的提交按钮
│   ├── UserKeyInput.tsx    # API Key, Model Name, Backend Base URL 自定义输入抽屉
│   ├── PromptOptions.tsx   # 语言、时间戳、结构化输出等表单开关项
│   ├── ModelSelector.tsx   # 在线/本地 Whisper 模型切换与后台下载进度指示器
│   ├── SummaryResult.tsx   # 渲染 Markdown 总结
│   └── Sentence.tsx        # 精准时间戳定位渲染器
│
├── pages/                  # Next.js 页面结构 (Pages Router)
│   ├── _app.tsx            # 全局 App 配置，加载全局样式
│   ├── _document.tsx       # 自定义 HTML Document (加载 JetBrains Mono 字体)
│   ├── 404.tsx             # 极简 404 错误页
│   └── [[...slug]].tsx     # 捕获所有路径的主页，包含完整的状态调度与渲染逻辑
│
├── hooks/                  # 自定义状态 Hooks
│   ├── useSummarize.ts     # 核心总结与多媒体上传 Stream Reader 流式调度 Hook
│   ├── useModelManager.ts  # 在线 Whisper 模型状态拉取与下载管理 Hook
│   ├── useClearCache.ts    # 远程一键清空 API 缓存的 Hook
│   └── useLocalStorage.ts  # 本地浏览器 Storage 的响应式绑定 Hook
│
├── utils/                  # 纯计算辅助函数
│   ├── schemas/
│   │   └── video.ts        # 基于 Zod 的表单验证与 TS 类型导出 Schema
│   ├── constants/          # 语言字典等常量
│   ├── getVideoIdFromUrl.ts# 解析各种 Bilibili/YouTube URL
│   └── extractUrl.ts       # 媒体 ID 深度提取器
│
├── lib/                    # 全局公用定义
│   ├── api.ts              # API Base URL 解析规则
│   └── types.ts            # 公共 TypeScript Interface 定义
│
├── styles/                 # 样式系统
│   ├── globals.css         # 全局 Tailwind 基础配置、暗黑背景及绝对直角样式重置
│   └── markdown.css        # 为流式 Markdown 专门定制的复古青红版 CSS 排版
│
├── package.json            # NPM 包管理
└── tsconfig.json           # 严格模式 TypeScript 配置文件
```

---

## 本地开发调试

### 1. 配置环境变量

复制配置文件模板：

```bash
cp .env.example .env
```

打开并编辑 `.env`：

```env
# 连接的后端 FastAPI API 服务基础路径
NEXT_PUBLIC_API_URL=http://localhost:8000

# 本地前端开发服务器监听端口
FRONTEND_PORT=3000
```

### 2. 启动服务

```bash
# 安装依赖 (推荐 npm ci 确保锁版本一致性)
npm ci

# 启动 Next.js 本地开发热重载服务器
npm run dev
```

打开浏览器访问 http://localhost:3000。

### 3. 构建与生产部署

```bash
# 静态构建与体积分析
npm run build

# 启动 Next.js 生产环境服务器
npm run start
```
