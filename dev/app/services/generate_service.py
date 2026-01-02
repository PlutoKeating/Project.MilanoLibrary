import os
from typing import List, Dict, Any
from openai import OpenAI
from app.utils import read_config

class GenerateService:
    """使用ModelScope OpenAI兼容接口生成笔记内容"""
    
    def __init__(self):
        """初始化生成服务，从config.ini读取配置"""
        config = read_config()
        self.api_key = config["api_key"]
        self.model_name = config["model_name"]
        self.base_url = os.environ.get("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_notes(self, milano_books_data: List[Dict[str, Any]], user_prompt: str = "") -> str:
        """
        根据多个MilanoBook生成笔记
        
        Args:
            milano_books_data: MilanoBook数据列表，每个元素包含book_id, title, paragraphs, items等
            user_prompt: 用户自定义提示词，用于指定内容偏好
        
        Returns:
            生成的笔记内容
        """
        prompt = self._build_prompt(milano_books_data, user_prompt)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的笔记整理助手，擅长从多个视频内容中提取关键信息，生成结构化、易读的学习笔记。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000,
                stream=True
            )
            
            # 收集流式返回的内容
            full_content = ""
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    full_content += chunk.choices[0].delta.content
            
            return full_content
        except Exception as e:
            print(f"生成笔记失败：{str(e)}")
            return f"生成笔记失败：{str(e)}"
    
    def generate_notes_stream(self, milano_books_data: List[Dict[str, Any]], user_prompt: str = ""):
        """
        流式生成笔记，支持实时返回结果
        
        Args:
            milano_books_data: MilanoBook数据列表
            user_prompt: 用户自定义提示词
        
        Returns:
            generator: 流式返回生成的内容片段
        """
        prompt = self._build_prompt(milano_books_data, user_prompt)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的笔记整理助手，擅长从多个视频内容中提取关键信息，生成结构化、易读的学习笔记。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000,
                stream=True
            )
            
            # 流式返回生成的内容
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"生成笔记失败：{str(e)}")
            yield f"生成笔记失败：{str(e)}"

    def _build_prompt(self, milano_books_data: List[Dict[str, Any]], user_prompt: str = "") -> str:
        """
        构建生成笔记的提示词
        
        Args:
            milano_books_data: MilanoBook数据列表
            user_prompt: 用户自定义提示词
        
        Returns:
            提示词字符串
        """
        prompt_parts = []
        
        prompt_parts.append("请根据以下视频内容，生成一份结构化的学习笔记：\n\n")
        
        for i, book_data in enumerate(milano_books_data, 1):
            prompt_parts.append(f"## 视频 {i}: {book_data['title']}\n")
            prompt_parts.append(f"作者: {book_data['author']}\n")
            prompt_parts.append(f"来源: {book_data['source_url']}\n\n")
            
            # 添加段落内容
            if book_data.get('paragraphs'):
                prompt_parts.append("### 内容概要\n")
                for j, para in enumerate(book_data['paragraphs'][:5], 1):  # 只取前5个段落避免过长
                    prompt_parts.append(f"{j}. {para['text_content'][:200]}...\n")
                prompt_parts.append("\n")
            
            # 添加Items信息
            if book_data.get('items'):
                prompt_parts.append("### 结构化信息\n")
                for item in book_data['items']:
                    prompt_parts.append(f"- {item['type']}: {item['name']} ({item['description']})\n")
                prompt_parts.append("\n")
        
        prompt_parts.append("\n请生成一份包含以下内容的笔记：\n")
        prompt_parts.append("1. 核心知识点总结\n")
        prompt_parts.append("2. 关键概念解释\n")
        prompt_parts.append("3. 学习要点梳理\n")
        prompt_parts.append("4. 实践建议\n")
        prompt_parts.append("5. 相关资源链接\n\n")
        
        # 添加用户自定义提示词
        if user_prompt:
            prompt_parts.append(f"\n用户特殊要求：{user_prompt}\n\n")
        
        prompt_parts.append("请使用Markdown格式输出，确保内容结构清晰、易于阅读。")
        
        return "".join(prompt_parts)
    
    def analyze_structure(self, milano_book_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用大模型分析MilanoBook的结构，提取逻辑关系
        
        Args:
            milano_book_data: MilanoBook数据
        
        Returns:
            包含结构化分析结果的字典
        """
        prompt = self._build_structure_prompt(milano_book_data)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的知识结构分析助手，擅长从视频内容中提取逻辑关系和结构化信息。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
                enable_thinking=False
            )
            
            return {
                "success": True,
                "analysis": response.choices[0].message.content
            }
        except Exception as e:
            print(f"结构分析失败：{str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_structure_prompt(self, milano_book_data: Dict[str, Any]) -> str:
        """
        构建结构分析的提示词
        
        Args:
            milano_book_data: MilanoBook数据
        
        Returns:
            提示词字符串
        """
        prompt_parts = []
        
        prompt_parts.append("请分析以下视频内容的逻辑结构：\n\n")
        prompt_parts.append(f"标题: {milano_book_data['title']}\n")
        prompt_parts.append(f"作者: {milano_book_data['author']}\n\n")
        
        # 添加所有段落内容
        if milano_book_data.get('paragraphs'):
            prompt_parts.append("### 内容段落\n")
            for i, para in enumerate(milano_book_data['paragraphs'], 1):
                prompt_parts.append(f"{i}. [{para['start_time']:.1f}s-{para['end_time']:.1f}s] {para['text_content']}\n")
            prompt_parts.append("\n")
        
        prompt_parts.append("\n请分析并输出以下信息：\n")
        prompt_parts.append("1. 识别主要的故事线或逻辑主线\n")
        prompt_parts.append("2. 提取关键的时间节点\n")
        prompt_parts.append("3. 识别概念之间的关系\n")
        prompt_parts.append("4. 建议的Items类型（Timeline, StuffList, RelationGraph等）\n")
        prompt_parts.append("5. 每个Item应该包含哪些内容\n\n")
        prompt_parts.append("请使用Markdown格式输出，确保分析结果清晰、可操作。")
        
        return "".join(prompt_parts)
        return "".join(prompt_parts)
