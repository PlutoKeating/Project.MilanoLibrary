import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "settings.json")
HOST_HOME_ENV = os.environ.get("HOST_HOME_PATH")

def get_host_separator() -> str:
    if HOST_HOME_ENV:
        if "\\" in HOST_HOME_ENV or (len(HOST_HOME_ENV) > 1 and HOST_HOME_ENV[1] == ":"):
            return "\\"
    return "/"

def get_default_host_home() -> str:
    if HOST_HOME_ENV:
        return HOST_HOME_ENV
    return os.path.expanduser("~")

def to_container_path(host_path: str) -> str:
    if not HOST_HOME_ENV or not host_path:
        return host_path
        
    host_path_std = host_path.replace("\\", "/")
    host_home_std = HOST_HOME_ENV.replace("\\", "/")
    
    if host_path_std.startswith(host_home_std):
        relative = host_path_std[len(host_home_std):].lstrip("/")
        return os.path.join("/host_home", relative).replace("\\", "/")
        
    return host_path

def to_host_path(container_path: str) -> str:
    if not HOST_HOME_ENV or not container_path:
        return container_path
        
    container_path_std = container_path.replace("\\", "/")
    
    if container_path_std.startswith("/host_home"):
        relative = container_path_std[len("/host_home"):].lstrip("/")
        sep = get_host_separator()
        relative_formatted = relative.replace("/", sep)
        base = HOST_HOME_ENV.rstrip("\\/")
        return f"{base}{sep}{relative_formatted}"
        
    return container_path

def get_active_root_dir_host() -> str:
    default_dir = get_default_host_home()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("root_dir", default_dir)
        except Exception:
            pass
    return default_dir

def get_active_root_dir() -> str:
    host_path = get_active_root_dir_host()
    container_path = to_container_path(host_path)
    os.makedirs(container_path, exist_ok=True)
    return container_path

def set_active_root_dir(path: str) -> None:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"root_dir": path}, f, ensure_ascii=False, indent=2)

class DBManager:
    @staticmethod
    def create_book(
        book_id: str,
        title: str,
        author: str,
        description: Optional[str],
        source_url: Optional[str],
        media_type: str,
        media_path: Optional[str],
        audio_path: Optional[str],
        duration_seconds: float
    ) -> Dict[str, Any]:
        root_dir = get_active_root_dir()
        book_dir = os.path.join(root_dir, book_id)
        os.makedirs(book_dir, exist_ok=True)
        
        book_json_path = os.path.join(book_dir, "book.json")
        now = datetime.now().isoformat()
        
        # Load existing book if it exists
        if os.path.exists(book_json_path):
            try:
                with open(book_json_path, "r", encoding="utf-8") as f:
                    book_data = json.load(f)
            except Exception:
                book_data = {}
        else:
            book_data = {}
            
        book_data.update({
            "id": book_id,
            "title": title,
            "author": author,
            "description": description or book_data.get("description", ""),
            "source_url": source_url or book_data.get("source_url", None),
            "media_type": media_type,
            "media_path": media_path or book_data.get("media_path", None),
            "audio_path": audio_path or book_data.get("audio_path", None),
            "duration_seconds": duration_seconds,
            "created_at": book_data.get("created_at", now),
            "updated_at": now,
        })
        
        # Ensure paragraphs and items are never in book.json basic info
        book_data.pop("paragraphs", None)
        book_data.pop("items", None)
        
        with open(book_json_path, "w", encoding="utf-8") as f:
            json.dump(book_data, f, ensure_ascii=False, indent=2)
            
        return book_data

    @staticmethod
    def save_book_paragraphs_and_items(
        book_id: str,
        paragraphs_list: List[Dict[str, Any]],
        items_list: List[Dict[str, Any]]
    ) -> None:
        # No-op since basic book.json no longer stores these details.
        pass

    @staticmethod
    def get_book(book_id: str) -> Optional[Dict[str, Any]]:
        root_dir = get_active_root_dir()
        book_json_path = os.path.join(root_dir, book_id, "book.json")
        if os.path.exists(book_json_path):
            try:
                with open(book_json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    @staticmethod
    def list_books() -> List[Dict[str, Any]]:
        root_dir = get_active_root_dir()
        if not os.path.exists(root_dir):
            return []
            
        books = []
        for book_id in os.listdir(root_dir):
            book_dir = os.path.join(root_dir, book_id)
            if os.path.isdir(book_dir):
                book_json_path = os.path.join(book_dir, "book.json")
                if os.path.exists(book_json_path):
                    try:
                        with open(book_json_path, "r", encoding="utf-8") as f:
                            books.append(json.load(f))
                    except Exception:
                        pass
        books.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
        return books

    @staticmethod
    def update_book_metadata(book_id: str, title: str, author: str, description: Optional[str]) -> Optional[Dict[str, Any]]:
        book_data = DBManager.get_book(book_id)
        if book_data:
            book_data["title"] = title
            book_data["author"] = author
            book_data["description"] = description
            book_data["updated_at"] = datetime.now().isoformat()
            
            book_dir = os.path.join(get_active_root_dir(), book_id)
            book_json_path = os.path.join(book_dir, "book.json")
            with open(book_json_path, "w", encoding="utf-8") as f:
                json.dump(book_data, f, ensure_ascii=False, indent=2)
            return book_data
        return None

    @staticmethod
    def delete_book(book_id: str) -> bool:
        import shutil
        root_dir = get_active_root_dir()
        book_dir = os.path.join(root_dir, book_id)
        if os.path.exists(book_dir):
            try:
                shutil.rmtree(book_dir)
                return True
            except Exception:
                pass
        return False

    @staticmethod
    def list_notes() -> List[Dict[str, Any]]:
        root_dir = get_active_root_dir()
        notes_dir = os.path.join(root_dir, ".notes")
        if not os.path.exists(notes_dir):
            return []
            
        notes = []
        for file in os.listdir(notes_dir):
            if file.endswith(".json"):
                note_path = os.path.join(notes_dir, file)
                try:
                    with open(note_path, "r", encoding="utf-8") as f:
                        notes.append(json.load(f))
                except Exception:
                    pass
        notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return notes

    @staticmethod
    def create_note(note_id: str, book_ids: List[str], content: str, user_prompt: Optional[str]) -> Dict[str, Any]:
        root_dir = get_active_root_dir()
        notes_dir = os.path.join(root_dir, ".notes")
        os.makedirs(notes_dir, exist_ok=True)
        
        note_data = {
            "id": note_id,
            "book_ids": book_ids,
            "content": content,
            "user_prompt": user_prompt,
            "created_at": datetime.now().isoformat()
        }
        
        note_path = os.path.join(notes_dir, f"{note_id}.json")
        with open(note_path, "w", encoding="utf-8") as f:
            json.dump(note_data, f, ensure_ascii=False, indent=2)
            
        return note_data

    @staticmethod
    def delete_note(note_id: str) -> bool:
        root_dir = get_active_root_dir()
        note_path = os.path.join(root_dir, ".notes", f"{note_id}.json")
        if os.path.exists(note_path):
            try:
                os.remove(note_path)
                return True
            except Exception:
                pass
        return False
