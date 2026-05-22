# Milano Library - 视频内容结构化管理系统

> 全功能视频资源切片器与结构化知识管理平台

---

## 项目简介

Milano Library 是一个基于Flask的全栈Web应用，用于将视频资源转换为结构化的知识库。系统支持从B站视频URL提取视频信息，通过多模态切片技术将视频内容进行语义化分割，并利用大语言模型进行智能重组，最终生成结构化的学习笔记。

### 核心特性

- **视频内容结构化**：将视频转换为MilanoBook格式，包含段落切片和结构化知识单元
- **智能语义分割**：基于语音识别和语义分析，将视频按主题切分为多个段落
- **多模态数据支持**：支持视频、音频、文本等多种模态数据的存储和管理
- **AI驱动的内容重组**：利用大语言模型分析视频内容，自动生成Timeline、StuffList、RelationGraph等结构化知识单元
- **智能笔记生成**：基于多个视频内容，自动生成结构化的学习笔记
- **完整的Web管理界面**：提供直观的用户界面，支持视频库和笔记库的管理
- **RESTful API**：提供完整的API接口，支持程序化调用

---

## 系统架构

### 技术栈

- **后端框架**：Flask
- **视频处理**：yt-dlp（视频下载）、ffmpeg（音频提取）、whisper（语音识别）
- **AI服务**：ModelScope OpenAI兼容接口（Qwen3-32B模型）
- **前端**：HTML + Bootstrap 5 + JavaScript
- **数据存储**：本地JSON文件存储

### 核心组件

#### 1. MilanoBook 数据模型

MilanoBook是视频内容的结构化容器，包含以下核心组件：

- **Paragraph（段落）**：视频切片的基本单元
  - 时间范围（start_time, end_time）
  - 文本内容（text_content）
  - 多模态数据（multi_modal_data）

- **Item（结构化知识单元）**：基类，支持多种类型
  - **StuffList**：扁平化内容列表
  - **Timeline**：按时间顺序排列的内容
  - **RelationGraph**：内容之间的逻辑关系图

#### 2. VideoProcessor（视频处理服务）

负责视频的完整处理流程：

1. **视频下载**：使用yt-dlp从B站下载视频
2. **音频提取**：使用ffmpeg从视频中提取音频
3. **语音识别**：使用whisper将音频转换为带时间戳的文字
4. **语义分割**：基于语义将转录文本分割成段落
5. **结构化重组**：利用大模型分析内容，生成结构化的MilanoBook

#### 3. GenerateService（笔记生成服务）

使用ModelScope的OpenAI兼容接口生成笔记：

- **批量笔记生成**：支持从多个MilanoBook生成笔记
- **流式输出**：支持实时返回生成结果
- **结构分析**：分析视频内容的逻辑结构
- **自定义提示词**：支持用户输入生成偏好

#### 4. MilanoBookStorage（存储管理器）

负责MilanoBook对象的持久化存储：

- **文件存储**：每个MilanoBook存储为独立的文件夹
- **JSON序列化**：支持对象与JSON的双向转换
- **批量管理**：支持列表、删除等操作

#### 5. Flask Web应用

提供完整的Web界面和API服务：

- **页面路由**：首页、视频库、笔记管理、笔记详情
- **API路由**：视频处理、笔记生成、数据管理等
- **模板渲染**：使用Jinja2模板引擎

---

## 目录结构

```
Project.MilanoLibrary/
├── release/                           # 开发代码目录
│   ├── app/                        # Flask应用主目录
│   │   ├── __init__.py            # 应用工厂函数
│   │   ├── routes/                 # 路由模块
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # 页面路由
│   │   │   └── api.py             # API路由
│   │   ├── services/              # 业务逻辑层
│   │   │   ├── video_processor.py  # 视频处理服务
│   │   │   └── generate_service.py # 笔记生成服务
│   │   ├── models/                # 数据模型
│   │   │   └── MilanoBook/       # MilanoBook相关模型
│   │   │       ├── __init__.py     # MilanoBook和Paragraph类
│   │   │       ├── storage.py      # 存储管理器
│   │   │       └── Item/          # Item子类
│   │   │           ├── __init__.py # Item基类
│   │   │           ├── StuffList.py # 扁平化列表
│   │   │           ├── Timeline.py   # 时间线
│   │   │           └── RelationGraph.py # 关系图
│   │   ├── static/                # 静态资源
│   │   │   └── css/
│   │   │       └── style.css
│   │   ├── templates/             # HTML模板
│   │   │   ├── index.html         # 首页
│   │   │   ├── result.html        # 处理结果页
│   │   │   ├── books.html         # 视频库管理
│   │   │   ├── notes_list.html    # 笔记管理
│   │   │   └── notes.html         # 笔记详情
│   │   └── utils.py              # 工具函数
│   ├── milano_books/              # MilanoBook存储目录
│   ├── notes/                    # 笔记存储目录
│   └── run.py                   # 应用入口
├── docs/                         # 文档目录
│   ├── 48h 题目（全栈版）.pdf    # 原始项目要求
│   └── bilibili-API-collect-master/ # B站API文档
├── config.ini                    # 配置文件
├── DEVLOG.md                    # 开发日志
└── README.md                    # 项目说明文档
```

---

## 安装和运行

### 环境要求

- Python 3.7+
- pip（Python包管理器）
- ffmpeg（音频处理工具）

### 依赖项

主要Python依赖：

```
flask
yt-dlp
openai
whisper
```

### 安装步骤

1. **克隆项目到本地**
   ```bash
   git clone <repository-url>
   cd Project.MilanoLibrary
   ```

2. **安装Python依赖**
   ```bash
   pip install flask yt-dlp openai whisper
   ```

3. **安装ffmpeg**
   
   **Windows:**
   ```bash
   # 使用chocolatey安装
   choco install ffmpeg
   
   # 或下载预编译版本并添加到PATH
   ```
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Linux:**
   ```bash
   sudo apt-get install ffmpeg
   ```

4. **配置API密钥**
   
   编辑 `config.ini` 文件，填入ModelScope API密钥和模型名称：
   ```ini
   [modelscope]
   api_key = your_api_key_here
   model_name = Qwen/Qwen3-32B
   ```

5. **运行应用**
   ```bash
   cd dev
   python run.py
   ```

6. **访问Web界面**
   
   在浏览器中打开：`http://127.0.0.1:5001`

---

## 使用说明

### Web界面使用

#### 1. 首页 - 添加视频

1. 访问 `http://127.0.0.1:5001`
2. 在输入框中输入B站视频URL（例如：https://www.bilibili.com/video/BV1xx411c7m9）
3. 点击"处理视频"按钮
4. 等待处理完成，查看结果页面

#### 2. 视频库管理

1. 点击导航栏的"视频库"
2. 查看所有已处理的视频
3. 可以搜索视频标题
4. 选中一个或多个视频：
   - 生成笔记：点击"生成笔记"按钮，输入偏好设置
   - 删除视频：点击"删除选中视频"按钮

#### 3. 笔记管理

1. 点击导航栏的"笔记管理"
2. 查看所有生成的笔记
3. 可以搜索笔记内容
4. 选中一个或多个笔记进行删除
5. 点击笔记卡片查看详情

#### 4. 笔记详情

1. 查看生成的笔记内容
2. 支持Markdown格式渲染
3. 点击"返回笔记管理"返回列表

### API调用

#### 处理视频

**请求：**
```http
POST /api/process
Content-Type: application/json

{
  "video_url": "https://www.bilibili.com/video/BV1xx411c7m9"
}
```

**响应：**
```json
{
  "book_id": "book_20260103_034616_1234567890",
  "title": "视频标题",
  "author": "作者名称",
  "source_url": "https://www.bilibili.com/video/BV1xx411c7m9",
  "paragraphs": [
    {
      "start_time": 0.0,
      "end_time": 10.0,
      "text_content": "切片文本内容",
      "multi_modal_data": {
        "type": "semantic_slice",
        "video_url": "https://www.bilibili.com/video/BV1xx411c7m9",
        "slice_index": 0,
        "total_slices": 10
      }
    }
  ],
  "items": [
    {
      "type": "StuffList",
      "name": "视频内容列表",
      "description": "按顺序排列的视频内容切片",
      "content_count": 10
    },
    {
      "type": "Timeline",
      "name": "视频时间线",
      "description": "按时间顺序排列的视频内容",
      "content_count": 10
    },
    {
      "type": "RelationGraph",
      "name": "内容关系图",
      "description": "视频内容之间的逻辑关系",
      "content_count": 0
    }
  ]
}
```

#### 列出所有视频

**请求：**
```http
GET /api/books
```

**响应：**
```json
{
  "books": [
    {
      "book_id": "book_20260103_034616_1234567890",
      "title": "视频标题",
      "author": "作者名称",
      "created_at": "2026-01-03T03:46:16"
    }
  ]
}
```

#### 获取指定视频

**请求：**
```http
GET /api/books/{book_id}
```

**响应：**
```json
{
  "book_id": "book_20260103_034616_1234567890",
  "title": "视频标题",
  "author": "作者名称",
  "source_url": "https://www.bilibili.com/video/BV1xx411c7m9",
  "paragraphs": [...],
  "items": [...]
}
```

#### 删除视频

**请求：**
```http
DELETE /api/books/{book_id}
```

**响应：**
```json
{
  "message": "书籍 book_20260103_034616_1234567890 已删除"
}
```

#### 生成笔记

**请求：**
```http
POST /api/generate-notes
Content-Type: application/json

{
  "book_ids": ["book_20260103_034616_1234567890"],
  "user_prompt": "重点关注技术细节"
}
```

**响应：**
```json
{
  "success": true,
  "notes_id": "9b154c79-90d7-40b6-ac1b-1d6147c2abc3",
  "message": "笔记生成成功"
}
```

#### 流式生成笔记

**请求：**
```http
POST /api/generate-notes-stream
Content-Type: application/json

{
  "book_ids": ["book_20260103_034616_1234567890"],
  "user_prompt": ""
}
```

**响应：**
```
data: {"type": "content", "content": "生成的笔记片段1"}

data: {"type": "content", "content": "生成的笔记片段2"}

data: {"type": "done", "notes_id": "9b154c79-90d7-40b6-ac1b-1d6147c2abc3"}
```

#### 列出所有笔记

**请求：**
```http
GET /api/notes
```

**响应：**
```json
{
  "success": true,
  "notes": [
    {
      "notes_id": "9b154c79-90d7-40b6-ac1b-1d6147c2abc3",
      "book_ids": ["book_20260103_034616_1234567890"],
      "content": "笔记内容...",
      "user_prompt": "",
      "created_at": "2026-01-03T04:30:00"
    }
  ]
}
```

#### 获取指定笔记

**请求：**
```http
GET /api/notes/{notes_id}
```

**响应：**
```json
{
  "success": true,
  "notes": {
    "notes_id": "9b154c79-90d7-40b6-ac1b-1d6147c2abc3",
    "book_ids": ["book_20260103_034616_1234567890"],
    "content": "笔记内容...",
    "user_prompt": "",
    "created_at": "2026-01-03T04:30:00"
  }
}
```

#### 删除笔记

**请求：**
```http
DELETE /api/notes/{notes_id}
```

**响应：**
```json
{
  "success": true,
  "message": "笔记 9b154c79-90d7-40b6-ac1b-1d6147c2abc3 已删除"
}
```

---

## 核心功能详解

### 1. 视频信息提取

使用yt-dlp从B站URL提取视频信息：

- 视频标题
- 作者名称
- 视频时长
- 播放量、点赞数
- 标签和分类
- 上传时间

支持BV号和AV号两种视频ID格式。

### 2. 视频内容切片（Tokenization）

将视频按语义切分为多个段落：

1. **音频提取**：使用ffmpeg从视频中提取音频
2. **语音识别**：使用whisper将音频转换为带时间戳的文字
3. **语义分割**：基于以下规则进行分割：
   - 时间间隔超过3秒
   - 句子结束标记（。！？）
   - 主题转换关键词（首先、接下来、然后、最后等）
   - 段落长度控制（最多30秒）

每个段落包含：
- 时间范围（start_time, end_time）
- 文本内容（text_content）
- 多模态数据（multi_modal_data）

### 3. 结构化重组（Recomposition）

利用大语言模型分析视频内容，生成结构化的知识单元：

- **Timeline（时间线）**：按时间顺序排列的关键内容
- **StuffList（内容列表）**：按逻辑顺序排列的重要内容
- **RelationGraph（关系图）**：内容之间的逻辑关系

系统会自动分析视频内容，选择最合适的重组方式。

### 4. 智能笔记生成

基于多个MilanoBook生成结构化的学习笔记：

- 核心知识点总结
- 关键概念解释
- 学习要点梳理
- 实践建议
- 相关资源链接

支持：
- 批量生成：一次处理多个视频
- 流式输出：实时显示生成进度
- 自定义提示词：指定生成偏好

### 5. 本地存储管理

使用文件系统进行数据持久化：

- **MilanoBook存储**：每个视频存储为独立文件夹
- **笔记存储**：每个笔记存储为JSON文件
- **JSON序列化**：支持对象与JSON的双向转换

---

## 开发说明

### 扩展新的Item类型

1. 在 `dev/app/models/MilanoBook/Item/` 目录下创建新的Python文件
2. 继承自 `Item` 基类
3. 实现自定义的属性和方法
4. 在 `dev/app/models/MilanoBook/storage.py` 中添加序列化和反序列化逻辑
5. 在 `dev/app/services/video_processor.py` 中添加相应的重组逻辑

### 扩展新的模态处理

1. 修改 `dev/app/services/video_processor.py` 中的 `tokenization` 方法
2. 添加新的模态数据提取逻辑
3. 在 `Paragraph` 类中添加相应的属性支持

### 添加新的API接口

1. 在 `dev/app/routes/api.py` 中添加新的路由
2. 实现业务逻辑
3. 返回JSON格式的响应

### 添加新的页面

1. 在 `dev/app/templates/` 目录下创建新的HTML模板
2. 在 `dev/app/routes/main.py` 中添加页面路由
3. 在导航栏中添加链接

---

## 配置说明

### config.ini 配置文件

```ini
[modelscope]
api_key = your_api_key_here
model_name = Qwen/Qwen3-32B
```

**参数说明：**

- `api_key`：ModelScope API密钥，用于调用大模型
- `model_name`：使用的模型名称，默认为Qwen/Qwen3-32B

### 环境变量

- `MODELSCOPE_BASE_URL`：ModelScope API基础URL，默认为https://api-inference.modelscope.cn/v1

---

## 常见问题

### 1. whisper安装失败

**问题**：安装whisper时出现错误

**解决方案**：
```bash
pip install openai-whisper
```

### 2. ffmpeg未找到

**问题**：运行时提示ffmpeg未找到

**解决方案**：确保ffmpeg已安装并添加到系统PATH中

### 3. 视频下载失败

**问题**：从B站下载视频失败

**解决方案**：
- 检查网络连接
- 确认视频URL格式正确
- 更新yt-dlp到最新版本：`pip install --upgrade yt-dlp`

### 4. 笔记生成失败

**问题**：调用ModelScope API失败

**解决方案**：
- 检查API密钥是否正确
- 确认网络连接
- 查看控制台错误日志

---

## 后续改进方向

- [ ] 支持更多视频平台（YouTube、抖音等）
- [ ] 实现真实的视频帧提取和图像识别
- [ ] 添加更智能的内容切片算法
- [ ] 支持更多类型的结构化知识单元
- [ ] 实现数据库存储（SQLite/PostgreSQL）
- [ ] 添加用户认证和权限管理
- [ ] 实现知识图谱可视化
- [ ] 添加全文搜索功能
- [ ] 支持导出为多种格式（PDF、Word等）
- [ ] 实现笔记分享功能

---

## 许可证

MIT License

---

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交Pull Request

---

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue
- 发送邮件

---

## 致谢

感谢以下开源项目的支持：

- [Flask](https://flask.palletsprojects.com/) - Web框架
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载工具
- [whisper](https://github.com/openai/whisper) - 语音识别
- [ModelScope](https://modelscope.cn/) - 大语言模型服务
- [Bootstrap](https://getbootstrap.com/) - 前端UI框架

---

## 原始项目要求

详细的项目要求请参考：`docs/48h 题目（全栈版）.pdf`

---

**© 2026 Milano Library. All rights reserved.**
