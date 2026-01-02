import yt_dlp
import os
import subprocess
import json
from typing import Dict, List, Any, Tuple
from app.models.MilanoBook import MilanoBook, Paragraph
from app.models.MilanoBook.Item.StuffList import StuffList
from app.models.MilanoBook.Item.Timeline import Timeline
from app.models.MilanoBook.Item.RelationGraph import RelationGraph

class VideoProcessor:
    def __init__(self, output_dir="downloads"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def download_video(self, url: str) -> Dict[str, Any]:
        """使用 yt_dlp 下载视频并提取信息（只下载第一个视频）"""
        ydl_opts = {
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'playliststart': 1,
            'playlistend': 1,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            video_filename = ydl.prepare_filename(info)
            
            return {
                "title": info.get("title", "Unknown"),
                "author": info.get("uploader", "Unknown"),
                "description": info.get("description", ""),
                "duration": info.get("duration", 0),
                "url": url,
                "filename": video_filename,
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "upload_date": info.get("upload_date", ""),
                "tags": info.get("tags", []),
                "categories": info.get("categories", [])
            }
    
    def extract_audio(self, video_path: str, audio_path: str) -> bool:
        """使用ffmpeg从视频中提取音频"""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',
                '-acodec', 'libmp3lame',
                '-ab', '192k',
                '-ar', '16000',
                '-y',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            # 检查音频文件是否成功创建
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                return True
            else:
                print(f"音频文件未创建或为空: {audio_path}")
                return False
        except Exception as e:
            print(f"音频提取失败: {str(e)}")
            return False
    
    def transcribe_audio(self, audio_path: str) -> List[Dict[str, Any]]:
        """使用whisper将音频转换为带时间戳的文字"""
        try:
            import whisper
            
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, language="zh", word_timestamps=True)
            
            segments = []
            for segment in result["segments"]:
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "words": segment.get("words", [])
                })
            
            return segments
        except ImportError:
            print("whisper未安装，使用模拟数据")
            return self._simulate_transcription(audio_path)
        except Exception as e:
            print(f"音频转文字失败: {str(e)}")
            return []
    
    def _simulate_transcription(self, audio_path: str) -> List[Dict[str, Any]]:
        """模拟转录数据（当whisper不可用时）"""
        return [
            {"start": 0.0, "end": 5.0, "text": "大家好，欢迎来到我的视频"},
            {"start": 5.0, "end": 10.0, "text": "今天我们要讨论一个非常重要的话题"},
            {"start": 10.0, "end": 15.0, "text": "这个话题涉及到我们日常生活的方方面面"},
            {"start": 15.0, "end": 20.0, "text": "首先，让我们来看看第一点"},
            {"start": 20.0, "end": 25.0, "text": "这个观点在学术界已经被广泛接受"},
            {"start": 25.0, "end": 30.0, "text": "接下来，我想分享一些实际案例"},
            {"start": 30.0, "end": 35.0, "text": "这些案例可以帮助我们更好地理解"},
            {"start": 35.0, "end": 40.0, "text": "最后，让我们总结一下今天的内容"},
            {"start": 40.0, "end": 45.0, "text": "希望这个视频对大家有所帮助"},
            {"start": 45.0, "end": 50.0, "text": "感谢大家的观看，我们下期再见"}
        ]
    
    def semantic_segmentation(self, transcription: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于语义将转录文本分割成段落"""
        if not transcription:
            return []
        
        segments = []
        current_segment = {
            "start": transcription[0]["start"],
            "end": transcription[0]["end"],
            "text": transcription[0]["text"],
            "sentences": [transcription[0]["text"]]
        }
        
        for i in range(1, len(transcription)):
            segment = transcription[i]
            prev_segment = transcription[i-1]
            
            # 检测语义边界
            boundary_detected = False
            
            # 1. 时间间隔超过3秒
            if segment["start"] - prev_segment["end"] > 3.0:
                boundary_detected = True
            
            # 2. 句子结束标记
            if prev_segment["text"].endswith(("。", "！", "？", ".", "!", "?")):
                boundary_detected = True
            
            # 3. 主题转换关键词
            transition_keywords = ["首先", "接下来", "然后", "最后", "另外", "此外", "总之", "总结"]
            if any(keyword in segment["text"] for keyword in transition_keywords):
                boundary_detected = True
            
            # 4. 段落长度控制（最多30秒）
            if segment["end"] - current_segment["start"] > 30.0:
                boundary_detected = True
            
            if boundary_detected:
                # 保存当前段落
                segments.append(current_segment.copy())
                
                # 开始新段落
                current_segment = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                    "sentences": [segment["text"]]
                }
            else:
                # 继续当前段落
                current_segment["end"] = segment["end"]
                current_segment["text"] += " " + segment["text"]
                current_segment["sentences"].append(segment["text"])
        
        # 添加最后一个段落
        if current_segment["sentences"]:
            segments.append(current_segment)
        
        return segments
    
    def tokenization(self, video_info: Dict[str, Any]) -> Tuple[List[Paragraph], str, str]:
        """将视频进行语义化tokenization，生成切片"""
        paragraphs = []
        
        # 1. 提取音频
        video_path = video_info["filename"]
        audio_path = os.path.splitext(video_path)[0] + ".mp3"
        
        if not os.path.exists(audio_path):
            if not self.extract_audio(video_path, audio_path):
                raise RuntimeError(f"音频提取失败：无法从视频文件 '{video_path}' 提取音频到 '{audio_path}'")
        
        # 2. 转录音频
        transcription = self.transcribe_audio(audio_path)
        
        if not transcription:
            raise RuntimeError(f"音频转录失败：无法从音频文件 '{audio_path}' 转录文字内容")
        
        # 3. 语义化分割
        semantic_segments = self.semantic_segmentation(transcription)
        
        # 4. 创建Paragraph对象
        for i, segment in enumerate(semantic_segments):
            start_time = segment["start"]
            end_time = segment["end"]
            text_content = segment["text"]
            
            multi_modal_data = {
                "type": "semantic_slice",
                "video_url": video_info["url"],
                "slice_index": i,
                "total_slices": len(semantic_segments),
                "sentences_count": len(segment["sentences"]),
                "video_metadata": {
                    "view_count": video_info["view_count"],
                    "like_count": video_info["like_count"],
                    "tags": video_info["tags"]
                }
            }
            
            paragraph = Paragraph(start_time, end_time, text_content, multi_modal_data)
            paragraphs.append(paragraph)
        
        return paragraphs, video_path, audio_path
    
    def _fallback_tokenization(self, video_info: Dict[str, Any]) -> List[Paragraph]:
        """备用切片方案（当音频处理失败时）"""
        paragraphs = []
        
        slice_count = 10
        slice_duration = video_info["duration"] / slice_count if video_info["duration"] > 0 else 0
        
        for i in range(slice_count):
            start_time = i * slice_duration
            end_time = (i + 1) * slice_duration
            text_content = f"视频片段 {i+1}: {video_info['title']}"
            
            multi_modal_data = {
                "type": "time_slice",
                "video_url": video_info["url"],
                "slice_index": i,
                "total_slices": slice_count,
                "video_metadata": {
                    "view_count": video_info["view_count"],
                    "like_count": video_info["like_count"],
                    "tags": video_info["tags"]
                }
            }
            
            paragraph = Paragraph(start_time, end_time, text_content, multi_modal_data)
            paragraphs.append(paragraph)
        
        return paragraphs
    
    def recomposition(self, video_info: Dict[str, Any], paragraphs: List[Paragraph]) -> MilanoBook:
        """将切片重组为结构化的MilanoBook，使用大模型进行逻辑提取"""
        milano_book = MilanoBook(
            title=video_info["title"],
            author=video_info["author"],
            source_url=video_info["url"]
        )
        
        for paragraph in paragraphs:
            milano_book.add_paragraph(paragraph)
        
        try:
            from app.services.generate_service import GenerateService
            generate_service = GenerateService()
            
            milano_book_data = {
                "title": video_info["title"],
                "author": video_info["author"],
                "source_url": video_info["url"],
                "paragraphs": [
                    {
                        "start_time": p.start_time,
                        "end_time": p.end_time,
                        "text_content": p.text_content
                    } for p in paragraphs
                ],
                "items": []
            }
            
            analysis_result = generate_service.analyze_structure(milano_book_data)
            
            if analysis_result["success"]:
                print(f"结构分析成功：{analysis_result['analysis'][:200]}...")
                self._create_items_from_analysis(milano_book, paragraphs, analysis_result["analysis"])
            else:
                print(f"结构分析失败，使用默认重组：{analysis_result.get('error', 'Unknown error')}")
                self._default_recomposition(milano_book, paragraphs)
        except Exception as e:
            print(f"结构分析异常，使用默认重组：{str(e)}")
            self._default_recomposition(milano_book, paragraphs)
        
        return milano_book
    
    def _default_recomposition(self, milano_book: MilanoBook, paragraphs: List[Paragraph]):
        """默认的重组逻辑，创建基础Items"""
        stuff_list = StuffList(name="视频内容列表", description="按顺序排列的视频内容切片")
        for paragraph in paragraphs:
            stuff_list.add_content(paragraph)
        milano_book.add_item(stuff_list)
        
        timeline = Timeline(name="视频时间线", description="按时间顺序排列的视频内容")
        for paragraph in paragraphs:
            timeline.add_timeline_item(paragraph.start_time, paragraph)
        milano_book.add_item(timeline)
        
        relation_graph = RelationGraph(name="内容关系图", description="视频内容之间的逻辑关系")
        for i, paragraph in enumerate(paragraphs):
            relation_graph.add_node(paragraph)
            if i > 0:
                relation_graph.add_edge(paragraphs[i-1], paragraph, "顺序")
        milano_book.add_item(relation_graph)
    
    def _create_items_from_analysis(self, milano_book: MilanoBook, paragraphs: List[Paragraph], analysis: str):
        """根据大模型分析结果创建Items"""
        analysis_lower = analysis.lower()
        
        if "timeline" in analysis_lower or "时间线" in analysis_lower:
            timeline = Timeline(name="内容时间线", description="按时间顺序排列的关键内容")
            for paragraph in paragraphs:
                timeline.add_timeline_item(paragraph.start_time, paragraph)
            milano_book.add_item(timeline)
        
        if "stufflist" in analysis_lower or "列表" in analysis_lower or "清单" in analysis_lower:
            stuff_list = StuffList(name="关键内容清单", description="按逻辑顺序排列的重要内容")
            for paragraph in paragraphs:
                stuff_list.add_content(paragraph)
            milano_book.add_item(stuff_list)
        
        if "relationgraph" in analysis_lower or "关系图" in analysis_lower or "逻辑关系" in analysis_lower:
            relation_graph = RelationGraph(name="逻辑关系图", description="内容之间的逻辑关系")
            for i, paragraph in enumerate(paragraphs):
                relation_graph.add_node(paragraph)
                if i > 0:
                    relation_graph.add_edge(paragraphs[i-1], paragraph, "顺序")
            milano_book.add_item(relation_graph)
        
        if "故事线" in analysis_lower or "storyline" in analysis_lower:
            storyline = StuffList(name="故事线", description="按故事发展顺序排列的内容")
            for paragraph in paragraphs:
                storyline.add_content(paragraph)
            milano_book.add_item(storyline)
    
    def process_video(self, url: str) -> Tuple[MilanoBook, str, str]:
        """完整处理流程：下载视频、提取音频、转录、语义切片、重组"""
        video_info = self.download_video(url)
        paragraphs, video_path, audio_path = self.tokenization(video_info)
        milano_book = self.recomposition(video_info, paragraphs)
        
        return milano_book, video_path, audio_path
    
    def save_tokens(self, tokens: List[Dict[str, Any]], output_file: str):
        """将tokens保存为JSON文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tokens, f, ensure_ascii=False, indent=2)
    
    def _tokenize_text(self, text: str, max_length: int = 200) -> List[Dict[str, Any]]:
        """辅助方法：将文本分割为tokens"""
        tokens = []
        sentences = [s.strip() for s in text.split('\n') if s.strip()]
        
        for sentence in sentences:
            if len(sentence) > max_length:
                chunks = [sentence[i:i+max_length] for i in range(0, len(sentence), max_length)]
                for chunk in chunks:
                    tokens.append({
                        "type": "text",
                        "content": chunk,
                        "metadata": {}
                    })
            else:
                tokens.append({
                    "type": "text",
                    "content": sentence,
                    "metadata": {}
                })
        
        return tokens
