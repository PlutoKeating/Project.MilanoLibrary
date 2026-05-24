from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.db_manager import (
    DBManager, 
    get_active_root_dir, 
    set_active_root_dir, 
    get_active_root_dir_host, 
    get_default_host_home, 
    to_container_path, 
    to_host_path
)
from app.models import MilanoBookResponse, MilanoBookUpdateRequest, MilanoBookListResponse

router = APIRouter(prefix="/api/books", tags=["books"])

class BookCreateReq(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    source_url: Optional[str] = None

@router.get("/settings/root")
async def get_settings_root():
    return {"root_dir": get_active_root_dir_host()}

@router.get("/settings/browse")
async def browse_directories(path: Optional[str] = None):
    import os
    if not path or path.strip() == "":
        path = get_default_host_home()
        
    container_path = to_container_path(path)
    
    if not os.path.exists(container_path):
        return {"current_path": path, "parent_path": None, "subdirs": []}
        
    try:
        subdirs = []
        for item in os.listdir(container_path):
            full_item = os.path.join(container_path, item)
            if os.path.isdir(full_item) and not item.startswith("."):
                subdirs.append(item)
        subdirs.sort()
        
        parent_container_path = os.path.dirname(container_path) if os.path.dirname(container_path) != container_path else None
        
        current_host_path = to_host_path(container_path)
        parent_host_path = to_host_path(parent_container_path) if parent_container_path else None
        
        return {
            "current_path": current_host_path.replace("\\", "/"),
            "parent_path": parent_host_path.replace("\\", "/") if parent_host_path else None,
            "subdirs": subdirs
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read directory: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read directory: {e}")

@router.post("/settings/root")
async def post_settings_root(payload: dict = Body(...)):
    path = payload.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    set_active_root_dir(path)
    return {"root_dir": get_active_root_dir()}

@router.get("", response_model=MilanoBookListResponse)
async def list_books():
    books = DBManager.list_books()
    return {"books": books}

@router.post("", response_model=MilanoBookResponse)
async def create_book_placeholder(req: BookCreateReq):
    import uuid
    book_id = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    book = DBManager.create_book(
        book_id=book_id,
        title=req.title,
        author=req.author,
        description=req.description,
        source_url=req.source_url,
        media_type="local",
        media_path=None,
        audio_path=None,
        duration_seconds=0.0
    )
    return book

@router.get("/{book_id}", response_model=MilanoBookResponse)
async def get_book(book_id: str):
    book = DBManager.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.put("/{book_id}", response_model=MilanoBookResponse)
async def update_book(book_id: str, req: MilanoBookUpdateRequest):
    book = DBManager.update_book_metadata(book_id, req.title, req.author, req.description)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.delete("/{book_id}")
async def delete_book(book_id: str):
    success = DBManager.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"success": True}

@router.get("/{book_id}/content")
async def get_book_content(book_id: str):
    import os
    from app.services.book_persistence import get_book_dir
    book_dir = get_book_dir(book_id)
    complete_md_path = os.path.join(book_dir, "complete.md")
    if not os.path.exists(complete_md_path):
        return {"content": ""}
    try:
        with open(complete_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read book content: {str(e)}")

@router.get("/{book_id}/index")
async def get_book_index(book_id: str):
    import os
    import json
    from app.services.book_persistence import get_book_dir
    book_dir = get_book_dir(book_id)
    index_json_path = os.path.join(book_dir, "index.json")
    if not os.path.exists(index_json_path):
        raise HTTPException(status_code=404, detail="Index not found")
    try:
        with open(index_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read book index: {str(e)}")

@router.post("/{book_id}/compile")
async def compile_book_markdown_endpoint(book_id: str):
    from app.services.book_persistence import recompile_book_markdown
    success = recompile_book_markdown(book_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to recompile complete markdown document from current segments")
    return {"success": True}
