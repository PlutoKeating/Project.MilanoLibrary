import uuid
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.db_manager import DBManager
from app.models import NoteCreateRequest, NoteResponse, NoteListResponse
from app.services.openai_client import robust_llm_call
from app.config import settings

router = APIRouter(prefix="/api/notes", tags=["notes"])

def _build_notes_prompt(milano_books_data: List[Dict[str, Any]], user_prompt: Optional[str] = "") -> str:
    prompt_parts = []
    prompt_parts.append("请根据以下视频内容，生成一份结构化的学习笔记：\n\n")
    
    for i, book_data in enumerate(milano_books_data, 1):
        prompt_parts.append(f"## 视频 {i}: {book_data.get('title', 'Untitled')}\n")
        prompt_parts.append(f"作者: {book_data.get('author', 'Unknown')}\n")
        prompt_parts.append(f"来源: {book_data.get('source_url', 'None')}\n\n")
        
        # Add paragraphs summary
        paragraphs = book_data.get("paragraphs") or []
        if paragraphs:
            prompt_parts.append("### 内容概要\n")
            for j, para in enumerate(paragraphs[:20], 1): # Take up to 20 paragraphs for richer context
                prompt_parts.append(f"  - [{para.get('start_time', 0.0):.1f}s] {para.get('text_content', '')}\n")
            prompt_parts.append("\n")
        
        # Add items
        items = book_data.get("items") or []
        if items:
            prompt_parts.append("### 结构化信息\n")
            for item in items:
                prompt_parts.append(f"- {item.get('type')}: {item.get('name')} ({item.get('description')})\n")
            prompt_parts.append("\n")
            
    prompt_parts.append("\n请生成一份包含以下内容的详细系统化笔记：\n")
    prompt_parts.append("1. 核心知识点总结\n")
    prompt_parts.append("2. 关键概念解释\n")
    prompt_parts.append("3. 学习要点梳理\n")
    prompt_parts.append("4. 实践建议\n")
    prompt_parts.append("5. 相关资源链接\n\n")
    
    if user_prompt:
        prompt_parts.append(f"\n用户特殊要求：{user_prompt}\n\n")
        
    prompt_parts.append("请使用Markdown格式输出，确保内容结构清晰、易于阅读。并且全面、细致地归纳，不忽略任何重要的技术、公式或代码细节。")
    return "".join(prompt_parts)

@router.get("", response_model=NoteListResponse)
async def list_notes():
    notes = DBManager.list_notes()
    return {"notes": notes}

@router.post("", response_model=NoteResponse)
async def compile_note(req: NoteCreateRequest):
    # 1. Load book details
    milano_books_data = []
    for b_id in req.book_ids:
        book = DBManager.get_book(b_id)
        if book:
            milano_books_data.append(book)
            
    if not milano_books_data:
        raise HTTPException(status_code=400, detail="No valid books found for note aggregation")
        
    # 2. Build prompt
    prompt = _build_notes_prompt(milano_books_data, req.user_prompt)
    
    # 3. Call LLM to synthesize notes
    try:
        # Determine model
        model = settings.openai_compatible_model
        note_content = await robust_llm_call(
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的笔记整理助手，擅长从多个视频内容中提取关键信息，生成结构化、易读且极其详尽的学习笔记。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=model,
            temperature=0.7,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM compilation failed: {e}")
        
    # 4. Save Note on disk
    note_id = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    note_data = DBManager.create_note(
        note_id=note_id,
        book_ids=req.book_ids,
        content=note_content,
        user_prompt=req.user_prompt
    )
    return note_data

@router.delete("/{note_id}")
async def delete_note(note_id: str):
    success = DBManager.delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"success": True}
