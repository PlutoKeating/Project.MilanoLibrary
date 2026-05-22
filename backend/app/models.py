from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal


class VideoConfig(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    video_id: str
    task_id: Optional[str] = None
    service: Optional[Literal["bilibili", "youtube", "podcast", "meeting", "local-video", "local-audio"]] = "bilibili"
    page_number: Optional[str] = None
    enable_stream: bool = True
    model: Optional[str] = None
    show_timestamp: bool = False
    show_emoji: bool = True
    output_language: Optional[str] = "zh"
    use_structured_output: bool = True  # Enable JSON schema structured output
    respect_chapters: bool = True  # Respect video chapters when available
    model_type: Optional[Literal["online", "local"]] = "online"
    local_model: Optional[str] = None


class UserConfig(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    user_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    should_show_timestamp: bool = False


class SummarizeRequest(BaseModel):
    video_config: VideoConfig
    user_config: Optional[UserConfig] = None


class CacheClearResponse(BaseModel):
    success: bool
    deleted: int = 0
    message: Optional[str] = None
    error: Optional[str] = None
