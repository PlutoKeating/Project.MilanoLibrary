from typing import Dict, Any, List, Optional
import time

class PipelinePausedException(Exception):
    pass

class PipelineStoppedException(Exception):
    pass

class TaskStep:
    def __init__(self, step_id: str, title: str):
        self.id = step_id
        self.title = title
        self.status = "pending"  # pending, running, completed, failed
        self.progress = 0.0      # 0 to 100
        self.message = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "progress": self.progress,
            "message": self.message
        }

class TaskState:
    def __init__(self, task_id: str, flow_type: str, book_id: Optional[str] = None, video_config: Optional[dict] = None):
        self.task_id = task_id
        self.flow_type = flow_type  # "url" or "local"
        self.last_updated = time.time()
        self.steps: List[TaskStep] = []
        self.book_id = book_id
        self.video_config = video_config
        self.is_paused = False
        self.is_stopped = False
        self.title: Optional[str] = None
        self.author: Optional[str] = None
        self.description: Optional[str] = None
        
        if flow_type == "url":
            self.steps = [
                TaskStep("fetch_metadata", "获取视频元数据"),
                TaskStep("download_video", "下载视频流数据"),
                TaskStep("extract_audio", "音频提取与标准化"),
                TaskStep("transcribe", "本地 Whisper 离线转录"),
                TaskStep("detect_chapters", "识别章节划分"),
                TaskStep("segment_video", "内存逻辑切片"),
                TaskStep("process_segments", "高并发分段提炼"),
                TaskStep("compose_summary", "AI 总结生成"),
            ]
        else:  # local upload
            self.steps = [
                TaskStep("upload_file", "保存上传文件"),
                TaskStep("extract_audio", "音频提取与标准化"),
                TaskStep("transcribe", "本地 Whisper 离线转录"),
                TaskStep("detect_chapters", "识别章节划分"),
                TaskStep("segment_video", "内存逻辑切片"),
                TaskStep("process_segments", "高并发分段提炼"),
                TaskStep("compose_summary", "AI 总结生成"),
            ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "flow_type": self.flow_type,
            "last_updated": self.last_updated,
            "steps": [s.to_dict() for s in self.steps],
            "book_id": self.book_id,
            "is_paused": self.is_paused,
            "is_stopped": self.is_stopped,
            "title": self.title,
            "author": self.author,
            "description": self.description,
        }

# Global task state storage
_tasks: Dict[str, TaskState] = {}

def init_task(task_id: str, flow_type: str, book_id: Optional[str] = None, video_config: Optional[dict] = None) -> None:
    if not task_id:
        return
    _tasks[task_id] = TaskState(task_id, flow_type, book_id=book_id, video_config=video_config)

def check_task_control(task_id: Optional[str]) -> None:
    if not task_id or task_id not in _tasks:
        return
    task = _tasks[task_id]
    if task.is_stopped:
        raise PipelineStoppedException(f"Pipeline {task_id} is stopped.")
    if task.is_paused:
        raise PipelinePausedException(f"Pipeline {task_id} is paused.")

def pause_task(task_id: str) -> bool:
    if not task_id or task_id not in _tasks:
        return False
    task = _tasks[task_id]
    task.is_paused = True
    for step in task.steps:
        if step.status == "running":
            step.status = "paused"
            step.message = "Pipeline paused by user."
    return True

def stop_task(task_id: str) -> bool:
    if not task_id or task_id not in _tasks:
        return False
    task = _tasks[task_id]
    task.is_stopped = True
    for step in task.steps:
        if step.status == "running":
            step.status = "failed"
            step.message = "Pipeline stopped and cancelled by user."
            
    # Clear all runtime cache/files
    # 1. Clear Redis cache key for this video config
    try:
        if task.video_config:
            from app.services.cache import get_cache_id, _get_redis
            cache_id = get_cache_id(task.video_config)
            r = _get_redis()
            if r:
                r.delete(cache_id)
                r.srem("milanolibrary:cache_keys", cache_id)
    except Exception as e:
        print(f"Error clearing redis cache: {e}")
        
    # 2. Delete MilanoBook directory and database entry
    try:
        if task.book_id:
            from app.services.db_manager import DBManager
            DBManager.delete_book(task.book_id)
    except Exception as e:
        print(f"Error deleting book: {e}")
        
    # 3. Delete temporary/original video storage
    try:
        if task.video_config and "video_id" in task.video_config:
            from app.services.video_ingest import VIDEO_DIR
            video_id = task.video_config["video_id"]
            video_path = VIDEO_DIR / video_id
            if video_path.exists():
                import shutil
                shutil.rmtree(video_path)
    except Exception as e:
        print(f"Error deleting video path: {e}")
        
    return True

def update_step(
    task_id: Optional[str],
    step_id: str,
    status: str,
    progress: Optional[float] = None,
    message: Optional[str] = None
) -> None:
    if not task_id or task_id not in _tasks:
        return
    
    # Check if the task is stopped or paused
    check_task_control(task_id)
    
    task = _tasks[task_id]
    task.last_updated = time.time()
    
    # Auto manage transition statuses:
    # If a step is running, we can mark all prior steps as completed
    # If a step is completed, we can set progress to 100
    found_target = False
    for step in task.steps:
        if step.id == step_id:
            step.status = status
            if progress is not None:
                step.progress = progress
            elif status == "completed":
                step.progress = 100.0
            
            if message is not None:
                step.message = message
            found_target = True
        elif not found_target:
            # All prior steps can be set to completed if we are running or completing the current step
            if status in ("running", "completed") and step.status != "completed":
                step.status = "completed"
                step.progress = 100.0

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    if not task_id or task_id not in _tasks:
        return None
    return _tasks[task_id].to_dict()

def get_task_status_by_book_id(book_id: str) -> Optional[Dict[str, Any]]:
    # Search for an active/recent task matching book_id
    for task in _tasks.values():
        if task.book_id == book_id:
            return task.to_dict()
    return None

def update_task_metadata(
    task_id: Optional[str],
    title: Optional[str] = None,
    author: Optional[str] = None,
    description: Optional[str] = None
) -> None:
    if not task_id or task_id not in _tasks:
        return
    task = _tasks[task_id]
    task.last_updated = time.time()
    if title is not None:
        task.title = title
    if author is not None:
        task.author = author
    if description is not None:
        task.description = description
