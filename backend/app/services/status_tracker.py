from typing import Dict, Any, List, Optional
import time

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
    def __init__(self, task_id: str, flow_type: str):
        self.task_id = task_id
        self.flow_type = flow_type  # "url" or "local"
        self.last_updated = time.time()
        self.steps: List[TaskStep] = []
        
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
            "steps": [s.to_dict() for s in self.steps]
        }

# Global task state storage
_tasks: Dict[str, TaskState] = {}

def init_task(task_id: str, flow_type: str) -> None:
    if not task_id:
        return
    _tasks[task_id] = TaskState(task_id, flow_type)

def update_step(
    task_id: Optional[str],
    step_id: str,
    status: str,
    progress: Optional[float] = None,
    message: Optional[str] = None
) -> None:
    if not task_id or task_id not in _tasks:
        return
    
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
