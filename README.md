# Project.MilanoLibrary

> Full functional video resource tokenizer & structural knowledge manager

---

## 项目简介

MilanoLibrary 是一个视频内容结构化管理系统，用于将视频资源转换为结构化的知识库。系统支持从B站视频URL提取视频信息，将视频内容切分为多模态切片，并重组为结构化的知识单元，方便后续的检索和利用。

## 系统架构

### 核心组件

1. **MilanoBook** - 视频内容的结构化容器
   - Paragraph：存储视频切片的基本单元，包含时间范围、文本内容和多模态数据
   - Item：结构化知识单元的基类
     - StuffList：扁平化内容列表
     - Timeline：按时间顺序排列的内容
     - RelationGraph：内容之间的逻辑关系图

2. **VideoProcessor** - 视频处理服务
   - 从B站URL提取视频信息
   - Tokenization：将视频切分为多模态切片
   - Recomposition：将切片重组为结构化的MilanoBook

3. **Flask UI** - Web界面和API服务
   - 提供Web界面用于输入视频URL和查看处理结果
   - 提供RESTful API用于程序化调用

## 目录结构

```
Project.MilanoLibrary/
├── dev/                      # 开发代码目录
│   ├── MilanoBook/           # 核心类定义
│   │   ├── __init__.py       # MilanoBook和Paragraph类
│   │   └── Item/             # 结构化项目类
│   │       ├── __init__.py   # Item基类
│   │       ├── StuffList.py  # 扁平化列表
│   │       ├── Timeline.py   # 时间线
│   │       └── RelationGraph.py  # 关系图
│   ├── video_processor.py    # 视频处理服务
│   └── app.py                # Flask Web应用
├── docs/                     # 文档目录
│   ├── 48h 题目（全栈版）.pdf     # 原始项目要求
│   └── bilibili-API-collect-master/  # B站API文档
├── release/                  # 发布目录
├── DEVLOG.md                 # 开发日志
└── README.md                 # 项目说明文档
```

## 安装和运行

### 依赖项

- Python 3.7+
- Flask
- requests

### 安装步骤

1. 克隆项目到本地
   ```bash
   git clone <repository-url>
   cd Project.MilanoLibrary
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

   注：如果没有requirements.txt文件，请手动安装依赖
   ```bash
   pip install flask requests
   ```

3. 运行Web应用
   ```bash
   cd dev
   python app.py
   ```

4. 访问Web界面
   在浏览器中输入 `http://localhost:5000`

## 使用说明

### Web界面使用

1. 在浏览器中打开 `http://localhost:5000`
2. 在输入框中输入B站视频URL（例如：https://www.bilibili.com/video/BV1xx411c7m9）
3. 点击"处理视频"按钮
4. 等待处理完成，查看结果

### API调用

#### 处理视频API

- URL: `/api/process`
- Method: POST
- Content-Type: application/json
- Request Body:
  ```json
  {
    "video_url": "https://www.bilibili.com/video/BV1xx411c7m9"
  }
  ```

- Response:
  ```json
  {
    "title": "视频标题",
    "author": "作者名称",
    "source_url": "视频URL",
    "paragraphs": [
      {
        "start_time": 0.0,
        "end_time": 10.0,
        "text_content": "切片文本内容",
        "multi_modal_data": {
          "image": "frame_1.jpg",
          "audio": "audio_1.wav"
        }
      }
    ],
    "items": [
      {
        "type": "StuffList",
        "name": "视频内容列表",
        "description": "按顺序排列的视频内容切片",
        "content_count": 10
      }
    ]
  }
  ```

## 核心功能

### 1. 视频信息提取
- 从B站URL自动提取视频标题、作者、时长等信息
- 支持BV号和AV号两种视频ID格式

### 2. 视频内容切片（Tokenization）
- 将视频按时间切分为多个段落
- 每个段落包含时间范围、文本内容和多模态数据
- 支持多种模态数据：图像、音频等

### 3. 结构化重组（Recomposition）
- 将切片重组为多种结构化知识单元
- StuffList：扁平化的内容列表
- Timeline：按时间顺序排列的内容
- RelationGraph：内容之间的逻辑关系

### 4. Web界面
- 提供直观的用户界面
- 支持视频URL输入和处理结果展示
- 展示原始切片和结构化项目

### 5. RESTful API
- 支持程序化调用
- 返回JSON格式的处理结果

## 开发说明

### 扩展新的Item类型

1. 在 `dev/MilanoBook/Item/` 目录下创建新的Python文件
2. 继承自 `Item` 基类
3. 实现自定义的属性和方法
4. 在 `dev/video_processor.py` 中添加相应的重组逻辑

### 扩展新的模态处理

1. 修改 `dev/video_processor.py` 中的 `tokenization` 方法
2. 添加新的模态数据提取逻辑
3. 在 `Paragraph` 类中添加相应的属性支持

## 后续改进方向

- 支持更多视频平台
- 实现真实的视频帧提取和ASR转写
- 添加更智能的内容切片算法
- 支持更多类型的结构化知识单元
- 实现知识库的持久化存储
- 添加检索和查询功能

## 许可证

MIT License

## 原始项目要求

见 `docs/48h 题目（全栈版）.pdf`
