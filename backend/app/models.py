from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal, List, Dict, Any


class VideoConfig(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    video_id: str
    task_id: Optional[str] = None
    book_id: Optional[str] = None
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


# --- MILANOBOOK SCHEMAS ---

class ParagraphSchema(BaseModel):
    start_time: float
    end_time: float
    text_content: str
    multi_modal_data: Optional[Dict[str, Any]] = None


class ItemSchema(BaseModel):
    type: Literal["StuffList", "Timeline", "RelationGraph"]
    name: str
    description: str
    payload: Optional[Dict[str, Any]] = None


class MilanoBookCreateRequest(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    source_url: Optional[str] = None


class MilanoBookUpdateRequest(BaseModel):
    title: str
    author: str
    description: Optional[str] = None


class MilanoBookResponse(BaseModel):
    id: str
    title: str
    author: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    media_type: str
    media_path: Optional[str] = None
    audio_path: Optional[str] = None
    duration_seconds: float
    created_at: str
    updated_at: str
    paragraphs: Optional[List[ParagraphSchema]] = None
    items: Optional[List[ItemSchema]] = None


class MilanoBookListResponse(BaseModel):
    books: List[MilanoBookResponse]


# --- NOTES SCHEMAS ---

class NoteCreateRequest(BaseModel):
    book_ids: List[str]
    user_prompt: Optional[str] = None


class NoteResponse(BaseModel):
    id: str
    book_ids: List[str]
    content: str
    user_prompt: Optional[str] = None
    created_at: str


class NoteListResponse(BaseModel):
    notes: List[NoteResponse]
