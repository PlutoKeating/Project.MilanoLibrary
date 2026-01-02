import json
import os
import shutil
from datetime import datetime
from .__init__ import MilanoBook, Paragraph
from .Item.__init__ import Item
from .Item.StuffList import StuffList
from .Item.Timeline import Timeline
from .Item.RelationGraph import RelationGraph

class MilanoBookStorage:
    """MilanoBook对象的持久化存储管理器"""
    
    def __init__(self, storage_dir="milano_books"):
        """初始化存储管理器"""
        # 创建存储目录
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def _get_book_dir(self, book_id):
        """获取书籍文件夹路径"""
        return os.path.join(self.storage_dir, book_id)
    
    def _get_file_path(self, book_id):
        """获取书籍JSON文件路径"""
        return os.path.join(self._get_book_dir(book_id), "book.json")
    
    def _serialize_paragraph(self, paragraph):
        """序列化Paragraph对象"""
        return {
            "type": "Paragraph",
            "start_time": paragraph.start_time,
            "end_time": paragraph.end_time,
            "text_content": paragraph.text_content,
            "multi_modal_data": paragraph.multi_modal_data
        }
    
    def _deserialize_paragraph(self, data):
        """反序列化Paragraph对象"""
        return Paragraph(
            start_time=data["start_time"],
            end_time=data["end_time"],
            text_content=data["text_content"],
            multi_modal_data=data["multi_modal_data"]
        )
    
    def _serialize_item(self, item):
        """序列化Item对象"""
        item_type = type(item).__name__
        data = {
            "type": item_type,
            "name": item.name,
            "description": item.description
        }
        
        # 根据不同的Item类型序列化内容
        if item_type == "StuffList":
            # 直接序列化内容，避免递归调用
            content_list = []
            for content in item.content:
                if hasattr(content, 'start_time') and hasattr(content, 'end_time') and hasattr(content, 'text_content'):  # 检查是否是Paragraph
                    content_list.append(self._serialize_paragraph(content))
                elif hasattr(content, 'name') and hasattr(content, 'description'):  # 检查是否是Item
                    content_list.append(self._serialize_item(content))
                else:
                    content_list.append(content)
            data["content"] = content_list
        elif item_type == "Timeline":
            # 转换为可序列化的列表格式，元组转换为列表
            content_list = []
            for time_point, content in item.content:
                if hasattr(content, 'start_time') and hasattr(content, 'end_time') and hasattr(content, 'text_content'):  # 检查是否是Paragraph
                    serialized_content = self._serialize_paragraph(content)
                elif hasattr(content, 'name') and hasattr(content, 'description'):  # 检查是否是Item
                    serialized_content = self._serialize_item(content)
                else:
                    serialized_content = content
                content_list.append([time_point, serialized_content])
            data["content"] = content_list
        elif item_type == "RelationGraph":
            data["nodes_count"] = len(item._nodes)
            data["edges_count"] = len(item._edges)
            data["content"] = []
            edge_types = []
            for edge in item._edges:
                if len(edge) >= 3:
                    edge_types.append(edge[2])
            data["edge_types"] = edge_types
        else:  # 处理Item基类
            if hasattr(item, 'content') and item.content:
                content_list = []
                for content in item.content:
                    if hasattr(content, 'start_time') and hasattr(content, 'end_time') and hasattr(content, 'text_content'):  # 检查是否是Paragraph
                        content_list.append(self._serialize_paragraph(content))
                    elif hasattr(content, 'name') and hasattr(content, 'description'):  # 检查是否是Item
                        content_list.append(self._serialize_item(content))
                    else:
                        content_list.append(content)
                data["content"] = content_list
            else:
                data["content"] = []
        
        return data
    
    def _deserialize_item(self, data):
        """反序列化Item对象"""
        item_type = data["type"]
        
        # 根据不同的Item类型创建对象
        if item_type == "StuffList":
            item = StuffList(name=data["name"], description=data["description"])
            # 反序列化内容
            for content_data in data["content"]:
                content = self._deserialize_content(content_data)
                item.add_content(content)
        elif item_type == "Timeline":
            item = Timeline(name=data["name"], description=data["description"])
            # 反序列化内容
            for time_point, content_data in data["content"]:
                content = self._deserialize_content(content_data)
                item.add_timeline_item(time_point, content)
        elif item_type == "RelationGraph":
            item = RelationGraph(name=data["name"], description=data["description"])
            # 对于简化的RelationGraph数据，只需要创建空的节点和边列表
            # 这里不进行详细的反序列化，因为我们在序列化时已经简化了数据
            # 如果需要完整的反序列化，需要在序列化时保存完整的节点和边数据
            pass
        else:
            # 未知类型，创建基础Item对象
            item = Item(name=data["name"], description=data["description"])
        
        return item
    
    def _serialize_content(self, content):
        """序列化内容，可以是Paragraph或Item对象"""
        if isinstance(content, Paragraph):
            return self._serialize_paragraph(content)
        elif isinstance(content, Item):
            return self._serialize_item(content)
        else:
            # 其他类型，直接返回
            return content
    
    def _deserialize_content(self, data):
        """反序列化内容，可以是Paragraph或Item对象"""
        if isinstance(data, dict) and "type" in data:
            if data["type"] == "Paragraph":
                return self._deserialize_paragraph(data)
            else:
                return self._deserialize_item(data)
        else:
            # 其他类型，直接返回
            return data
    
    def save_book(self, milano_book, book_id=None, video_path=None, audio_path=None):
        """保存MilanoBook对象到文件"""
        # 如果没有提供book_id，使用当前时间戳生成
        if book_id is None:
            book_id = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(milano_book)}"
        
        # 创建书籍文件夹
        book_dir = self._get_book_dir(book_id)
        if not os.path.exists(book_dir):
            os.makedirs(book_dir)
        
        # 移动视频和音频文件到书籍目录
        if video_path and os.path.exists(video_path):
            video_filename = os.path.basename(video_path)
            video_target_path = os.path.join(book_dir, video_filename)
            shutil.move(video_path, video_target_path)
        
        if audio_path and os.path.exists(audio_path):
            audio_filename = os.path.basename(audio_path)
            audio_target_path = os.path.join(book_dir, audio_filename)
            shutil.move(audio_path, audio_target_path)
        
        # 序列化MilanoBook对象
        book_data = {
            "book_id": book_id,
            "title": milano_book.title,
            "author": milano_book.author,
            "source_url": milano_book.source_url,
            "created_at": datetime.now().isoformat(),
            "paragraphs": [self._serialize_paragraph(p) for p in milano_book.paragraphs],
            "items": [self._serialize_item(item) for item in milano_book.items]
        }
        
        # 写入文件
        file_path = self._get_file_path(book_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(book_data, f, ensure_ascii=False, indent=2)
        
        return book_id
    
    def load_book(self, book_id):
        """从文件加载MilanoBook对象"""
        file_path = self._get_file_path(book_id)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"书籍 {book_id} 不存在")
        
        # 读取文件
        with open(file_path, "r", encoding="utf-8") as f:
            book_data = json.load(f)
        
        # 反序列化MilanoBook对象
        milano_book = MilanoBook(
            title=book_data["title"],
            author=book_data["author"],
            source_url=book_data["source_url"]
        )
        
        # 反序列化段落
        for paragraph_data in book_data["paragraphs"]:
            paragraph = self._deserialize_paragraph(paragraph_data)
            milano_book.add_paragraph(paragraph)
        
        # 反序列化项目
        for item_data in book_data["items"]:
            item = self._deserialize_item(item_data)
            milano_book.add_item(item)
        
        return milano_book
    
    def list_books(self):
        """列出所有存储的书籍"""
        books = []
        if os.path.exists(self.storage_dir):
            for book_id in os.listdir(self.storage_dir):
                book_dir = os.path.join(self.storage_dir, book_id)
                if os.path.isdir(book_dir):
                    file_path = os.path.join(book_dir, "book.json")
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            book_data = json.load(f)
                        books.append({
                            "book_id": book_id,
                            "title": book_data["title"],
                            "author": book_data["author"],
                            "created_at": book_data["created_at"]
                        })
        
        # 按创建时间排序
        books.sort(key=lambda x: x["created_at"], reverse=True)
        return books
    
    def delete_book(self, book_id):
        """删除书籍文件夹"""
        book_dir = self._get_book_dir(book_id)
        if os.path.exists(book_dir) and os.path.isdir(book_dir):
            shutil.rmtree(book_dir)
            return True
        else:
            return False
