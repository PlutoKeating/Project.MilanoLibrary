# MilanoLibrary 前端应用 (Next.js)

基于 Next.js + React + TypeScript 严格模式构建的 **无数据库视频知识库与重组编译器** 客户端界面。
遵循极致等宽、绝对直角的复古未来主义极简美学设计 (Retro-futurism Minimalism)。

---

## 核心特性

- **动态磁盘书籍挂载**：集成 `FileExplorer` 与后端 API 联动，支持直观地层层下探、选定磁盘上任何路径作为书籍根目录（Obsidian 库），即时加载/载入知识库中的所有 MilanoBooks。
- **3阶段编译流可视化**：内置 `PipelineProcessor` 和 `TimelineProgress` 组件，可实时、全自动跟踪后台流媒体获取、音频分离、高精度转录、大纲生成、并行叶节点提炼和递归拼装合并的实时百分比与详细日志日志。
- **跨领域多书整合 (Aggregator)**：提供专属的整合提炼控制台，支持跨书籍多选，输入自定义综合指令进行高深度知识编排重组，一键生成跨领域智能笔记。
- **自定义平台适配器后台管理**：支持在线上传自定义 Python 视频抓取适配器脚本并实时注入。
- **高解析科学公式/代码渲染**：使用 `ReactMarkdown` + `remark-gfm` + `remark-math` + `rehype-katex` + `katex` 渲染引擎。完美呈现大语言模型总结中包含的数学 LaTeX 公式与标准语法高亮代码块。
- **双向交互等宽树状大纲目录**：自动解析 MilanoBook 中的大纲树并生成侧边导航。点击标题、点击正文中的 `[MM:SS]` 精准时间戳可对视频播放器（或外部流定位）执行跳转播放与页面内滚动，实现高解析度的多媒体阅读互动。
- **全客户端渲染架构 (Client-Only)**：绝对不使用 Next.js API Routes。所有大语言模型调用、流式处理、模型管理全部通过直连暴露的 `NEXT_PUBLIC_API_URL` 远程 FastAPI 后端处理，保证轻量高效。
- **首选项自动持久化**：使用 `react-hook-form-persist` 将用户的所有表单首选项、自定义 API 密钥、自定义 Endpoint 及所选模型无感持久化存储于浏览器的 `localStorage` 中。

---

## 目录结构

```
frontend/
├── components/             # React UI 组件
│   ├── Header.tsx          # 头部极简像素风大标题
│   ├── Footer.tsx          # 底部免责与版权栏
│   ├── FileExplorer.tsx    # 磁盘文件目录浏览器 (用于动态挂载 Root Vault)
│   ├── PipelineProcessor.tsx# 核心多媒体提交、上传、编译控制面板
│   ├── TimelineProgress.tsx# 后台流水线百分比进度条与多步骤日志追踪器
│   ├── SubmitButton.tsx    # 带像素风状态切换的提交按钮
│   ├── UserKeyInput.tsx    # API Key, Model Name, Backend Base URL 配置抽屉
│   ├── PromptOptions.tsx   # 总结语言、Emoji、结构化开关等表单配置项
│   ├── ModelSelector.tsx   # 在线/本地 Whisper 切换及离线权重包后台下载器
│   ├── SummaryResult.tsx   # 渲染 Markdown 总结
│   └── Sentence.tsx        # 交互式时间戳高亮组件
│
├── pages/                  # Next.js Pages 目录
│   ├── _app.tsx            # 全局 App 配置 (导入全局样式)
│   ├── _document.tsx       # 自定义 HTML 模板 (预加载 JetBrains Mono 字体)
│   ├── 404.tsx             # 像素风 404 页
│   └── [[...slug]].tsx     # 捕获所有路径的主页，包含完整的状态调度与三主栏视图切换
│
├── hooks/                  # 自定义状态 Hooks
│   ├── useSummarize.ts     # 总结流式 Stream 调度及 abort 信号控制 Hook
│   ├── useModelManager.ts  # 在线 Whisper 模型包下载与进度拉取 Hook
│   ├── useClearCache.ts    # 远程一键清空 API 缓存的 Hook
│   └── useLocalStorage.ts  # 响应式绑定 LocalStorage 键值的 Hook
│
├── utils/                  # 纯计算辅助函数
│   ├── schemas/
│   │   └── video.ts        # 基于 Zod 编写的前后端配置验证 Schema
│   ├── constants/          # 语种映射字典
│   ├── getVideoIdFromUrl.ts# 解析在线 Bilibili/YouTube 视频标识码
│   └── extractUrl.ts       # 在线 URL 提取与分 P 参数映射器
│
├── lib/                    # 公共层
│   ├── api.ts              # API Base URL 动态解析
│   └── types.ts            # 全局 TypeScript 接口定义
│
└── styles/                 # 样式系统
    ├── globals.css         # 全局 Tailwind 配置、纯直角及像素化视觉重置
    └── markdown.css        # LaTeX 公式、代码块、引用段落专用 Markdown 排版
```

---

## 本地开发调试

### 1. 配置本地环境
复制配置文件：
```bash
cp .env.example .env
```
编辑 `.env` 文件，输入对应参数：
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
FRONTEND_PORT=3000
```

### 2. 启动开发服务器
```bash
# 严格锁定包版本安装依赖
npm ci

# 启动开发服务器（支持 HMR 热重载）
npm run dev
```
打开浏览器访问 [http://localhost:3000](http://localhost:3000)。

### 3. 构建静态生产文件
```bash
npm run build
npm run start
```
