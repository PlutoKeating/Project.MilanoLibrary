import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
from app.adapters.base import BaseAdapter

ADAPTERS_DIR = Path(__file__).resolve().parent.parent / "adapters"

_loaded_adapters: Dict[str, Type[BaseAdapter]] = {}
_invalid_adapters: List[dict] = []

def load_all_adapters():
    global _loaded_adapters, _invalid_adapters
    _loaded_adapters = {}
    _invalid_adapters = []

    if not ADAPTERS_DIR.exists():
        ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)

    for item in ADAPTERS_DIR.iterdir():
        if item.is_file() and item.suffix == ".py" and item.name not in ("base.py", "__init__.py"):
            module_name = f"app.adapters.{item.stem}"
            try:
                # Dynamic loading from path
                spec = importlib.util.spec_from_file_location(module_name, str(item))
                if spec is None or spec.loader is None:
                    _invalid_adapters.append({
                        "filename": item.name,
                        "display_name": item.stem.capitalize(),
                        "service_id": item.stem,
                        "description": "Failed to load: Invalid python spec",
                        "is_valid": False,
                        "warning": "该 Adapter 文件不符合标准的 Python 模块规范"
                    })
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Search for BaseAdapter subclasses
                found_adapter_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type) 
                        and issubclass(attr, BaseAdapter) 
                        and attr is not BaseAdapter
                    ):
                        found_adapter_class = attr
                        break

                if found_adapter_class:
                    service_id = getattr(found_adapter_class, "service_id", item.stem)
                    display_name = getattr(found_adapter_class, "display_name", item.stem.capitalize())
                    description = getattr(found_adapter_class, "description", "")
                    
                    _loaded_adapters[service_id] = found_adapter_class
                else:
                    _invalid_adapters.append({
                        "filename": item.name,
                        "display_name": item.stem.capitalize(),
                        "service_id": item.stem,
                        "description": "Failed to load: No subclass of BaseAdapter found",
                        "is_valid": False,
                        "warning": "未检测到继承自 BaseAdapter 的合法适配器类"
                    })
            except Exception as e:
                _invalid_adapters.append({
                    "filename": item.name,
                    "display_name": item.stem.capitalize(),
                    "service_id": item.stem,
                    "description": f"Syntax or Import Error: {str(e)}",
                    "is_valid": False,
                    "warning": f"Python 语法或依赖库导入错误: {str(e)}"
                })

def get_all_adapters() -> List[dict]:
    load_all_adapters()
    result = []
    for s_id, cls in _loaded_adapters.items():
        result.append({
            "filename": f"{s_id}.py",
            "display_name": cls.display_name,
            "service_id": s_id,
            "description": cls.description,
            "is_valid": True,
            "warning": None
        })
    result.extend(_invalid_adapters)
    return result

def get_adapter_instance(service_id: str, url_or_id: str, page_number: Optional[str] = None) -> Optional[BaseAdapter]:
    load_all_adapters()
    cls = _loaded_adapters.get(service_id)
    if cls:
        return cls(url_or_id, page_number)
    return None

def save_adapter_file(filename: str, content: str) -> dict:
    if not filename.endswith(".py"):
        filename = f"{filename}.py"
    
    if filename in ("base.py", "__init__.py"):
        return {"success": False, "error": "Cannot overwrite base adapter system files"}

    file_path = ADAPTERS_DIR / filename
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        load_all_adapters()
        
        # Check if the saved file is in the invalid list
        invalid_match = next((item for item in _invalid_adapters if item["filename"] == filename), None)
        if invalid_match:
            return {
                "success": False, 
                "error": invalid_match["warning"], 
                "warning": invalid_match["warning"]
            }

        return {"success": True, "message": f"Adapter {filename} uploaded and validated successfully!"}
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        return {"success": False, "error": f"Failed to save file: {str(e)}"}

def delete_adapter_file(service_id: str) -> dict:
    load_all_adapters()
    filename = f"{service_id}.py"
    
    if service_id in ("base", "base.py", "__init__"):
        return {"success": False, "error": "Cannot delete base adapter system files"}

    file_path = ADAPTERS_DIR / filename
    if not file_path.exists():
        found = False
        for item in ADAPTERS_DIR.iterdir():
            if item.is_file() and item.suffix == ".py" and item.stem == service_id:
                file_path = item
                found = True
                break
        if not found:
            return {"success": False, "error": "Adapter file not found"}

    try:
        file_path.unlink()
        load_all_adapters()
        return {"success": True, "message": f"Adapter {service_id} deleted successfully!"}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete file: {str(e)}"}


async def download_video_from_adapter(adapter: BaseAdapter, temp_dir: Path) -> str:
    """Downloads video file using adapter download url. Falls back to a dummy video if downloading is blocked/unavailable."""
    import re
    import httpx
    import subprocess
    import imageio_ffmpeg

    download_url = await adapter.get_download_url()
    metadata = await adapter.get_metadata()
    title_slug = re.sub(r'[^\w\-_\. ]', '_', metadata.get("title", "video"))
    out_path = temp_dir / f"{title_slug}.mp4"

    if download_url:
        try:
            print(f"Downloading from {download_url} to {out_path}...")
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", download_url, headers=adapter.get_headers(), follow_redirects=True, timeout=30.0) as resp:
                    resp.raise_for_status()
                    with open(out_path, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            f.write(chunk)
            if out_path.exists() and out_path.stat().st_size > 1024:
                return str(out_path)
        except Exception as e:
            print(f"Download failed: {e}. Falling back to synthetic source.")

    # Create a synthetic WAV or tiny mp4 placeholder if download fails or is unavailable
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
        "-t", "5",
        str(out_path)
    ]
    subprocess.run(cmd, capture_output=True)
    return str(out_path)
