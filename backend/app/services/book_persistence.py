import os
import re
import shutil
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.services.db_manager import DBManager, get_active_root_dir

def get_book_dir(book_id: str) -> str:
    """Gets the physical directory for a book dynamically resolved to the active root directory."""
    root_dir = get_active_root_dir()
    directory = os.path.join(root_dir, book_id)
    os.makedirs(directory, exist_ok=True)
    return directory

def copy_and_save_media(book_id: str, local_path: Optional[str], suffix_type: str = "video") -> Optional[str]:
    """Copies media file to books storage and returns the new absolute path."""
    if not local_path or not os.path.exists(local_path):
        return None
    
    book_dir = get_book_dir(book_id)
    ext = os.path.splitext(local_path)[1] or (".mp4" if suffix_type == "video" else ".mp3")
    target_filename = f"source_{suffix_type}{ext}"
    target_path = os.path.join(book_dir, target_filename)
    
    try:
        shutil.copy2(local_path, target_path)
        return target_path
    except Exception as e:
        print(f"Error copying media file: {e}")
        return local_path

def parse_stuff_list(markdown_text: str) -> Dict[str, Any]:
    """Helper to extract technical stuff (code, formulas, key points) from Markdown."""
    code_snippets = []
    # Find markdown code blocks
    code_blocks = re.findall(r'```(\w*)\n([\s\S]*?)\n```', markdown_text)
    for lang, code in code_blocks:
        code_snippets.append({
            "language": lang or "text",
            "code": code.strip()
        })
        
    formulas = []
    # Find inline and block LaTeX formulas
    inline_formulas = re.findall(r'\$([^$\n]+?)\$', markdown_text)
    for f in inline_formulas:
        formulas.append(f.strip())
        
    key_points = []
    # Find bullet list key points
    bullet_points = re.findall(r'^\s*-\s+(.+)$', markdown_text, re.MULTILINE)
    for p in bullet_points:
        key_points.append(p.strip())
        
    return {
        "code_snippets": code_snippets[:10],
        "formulas": list(set(formulas))[:10],
        "key_points": key_points[:20]
    }

def save_milano_book_from_pipeline(
    book_id: str,
    title: str,
    author: str,
    source_url: Optional[str],
    media_type: str,
    local_video_path: Optional[str],
    subtitles_array: List[Dict[str, Any]],
    outline_data: Dict[str, Any],
    summaries_map: Dict[str, str],
    final_markdown_text: str,
    duration: float
) -> Dict[str, Any]:
    """
    Saves a completed video processing run to the dynamic active root directory as a MilanoBook.
    Splits data into book.json (basic), raw.json (subtitles), index.json (outline), and segments/*.md.
    """
    # 1. Setup paths and copy media
    book_dir = get_book_dir(book_id)
    
    # Copy video if exists
    saved_video_path = copy_and_save_media(book_id, local_video_path, "video")
    
    # Extract description
    overall_summary = outline_data.get("overall_summary", "No description available.")
    
    # 2. Save raw.json
    raw_json_path = os.path.join(book_dir, "raw.json")
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump({"subtitles": subtitles_array}, f, ensure_ascii=False, indent=2)
        
    # 3. Save index.json (Outline with leaf node UUIDs)
    index_json_path = os.path.join(book_dir, "index.json")
    with open(index_json_path, "w", encoding="utf-8") as f:
        json.dump(outline_data, f, ensure_ascii=False, indent=2)

    # 4. Save separate .md files for leaf nodes in segments directory
    segments_dir = os.path.join(book_dir, "segments")
    os.makedirs(segments_dir, exist_ok=True)
    
    def collect_nodes_flat(node: dict) -> list:
        nodes = []
        if node.get("has_subchapters"):
            for child in node.get("children", []):
                nodes.extend(collect_nodes_flat(child))
        else:
            nodes.append(node)
        return nodes

    all_leaves = []
    for chapter in outline_data.get("outline", []):
        all_leaves.extend(collect_nodes_flat(chapter))
        
    for leaf in all_leaves:
        leaf_uuid = leaf.get("uuid") or leaf.get("id")
        if leaf_uuid:
            segment_md_content = summaries_map.get(leaf_uuid, "*(Summary generation failed)*")
            segment_path = os.path.join(segments_dir, f"{leaf_uuid}.md")
            with open(segment_path, "w", encoding="utf-8") as f:
                f.write(segment_md_content)

    # 5. Assemble all .md documents into complete.md in the root of the book directory
    def get_heading_prefix(indices: list) -> str:
        if not indices:
            return ""
        if len(indices) == 1:
            cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]
            idx = indices[0] - 1
            cn_str = cn_nums[idx] if idx < len(cn_nums) else str(indices[0])
            return f"{cn_str}、"
        return ".".join(str(x) for x in indices) + ". "

    def assemble_markdown_recursive(node: dict, segments_dir: str, depth: int = 3, indices: list = None) -> list:
        if indices is None:
            indices = []
        md_parts = []
        header_prefix = "#" * depth
        prefix = get_heading_prefix(indices)
        node_title = node.get("title", "Untitled")
        full_title = f"{prefix}{node_title}"
        
        if node.get("has_subchapters"):
            md_parts.append(f"\n{header_prefix} {full_title}\n")
            for c_idx, child in enumerate(node.get("children", []), 1):
                md_parts.extend(assemble_markdown_recursive(child, segments_dir, depth + 1, indices + [c_idx]))
        else:
            md_parts.append(f"\n{header_prefix} {full_title}\n")
            
            leaf_uuid = node.get("uuid") or node.get("id")
            segment_path = os.path.join(segments_dir, f"{leaf_uuid}.md")
            content = "*(Summary generation failed)*"
            if os.path.exists(segment_path):
                try:
                    with open(segment_path, "r", encoding="utf-8") as sf:
                        content = sf.read()
                except Exception:
                    pass
            md_parts.append(content)
            
        return md_parts

    assembled_parts = []
    if overall_summary:
        assembled_parts.append("## Summary\n")
        assembled_parts.append(f"{overall_summary}\n")
        assembled_parts.append("## Highlights\n")

    for idx, chapter in enumerate(outline_data.get("outline", []), 1):
        assembled_parts.extend(assemble_markdown_recursive(chapter, segments_dir, depth=3, indices=[idx]))

    complete_markdown = "\n".join(assembled_parts).strip()
    complete_md_path = os.path.join(book_dir, "complete.md")
    with open(complete_md_path, "w", encoding="utf-8") as f:
        f.write(complete_markdown)

    # 6. Save basic metadata to book.json (only basic metadata, no paragraphs or items)
    now_iso = datetime.now().isoformat()
    book_json_data = {
        "id": book_id,
        "title": title,
        "author": author,
        "description": overall_summary,
        "source_url": source_url,
        "media_type": media_type,
        "media_path": saved_video_path,
        "audio_path": None,
        "duration_seconds": duration,
        "created_at": now_iso,
        "updated_at": now_iso
    }
    
    # Save/Update Book metadata in DB
    DBManager.create_book(
        book_id=book_id,
        title=title,
        author=author,
        description=overall_summary,
        source_url=source_url,
        media_type=media_type,
        media_path=saved_video_path,
        audio_path=None,
        duration_seconds=duration
    )
    
    # Override/ensure the file book.json is exact and lightweight
    with open(os.path.join(book_dir, "book.json"), "w", encoding="utf-8") as f:
        json.dump(book_json_data, f, ensure_ascii=False, indent=2)
        
    return book_json_data

def recompile_book_markdown(book_id: str) -> bool:
    import os
    import json
    book_dir = get_book_dir(book_id)
    index_json_path = os.path.join(book_dir, "index.json")
    book_json_path = os.path.join(book_dir, "book.json")
    
    if not os.path.exists(index_json_path) or not os.path.exists(book_json_path):
        return False
        
    try:
        with open(index_json_path, "r", encoding="utf-8") as f:
            outline_data = json.load(f)
            
        overall_summary = outline_data.get("overall_summary", "")
        segments_dir = os.path.join(book_dir, "segments")
        
        def get_heading_prefix(indices: list) -> str:
            if not indices:
                return ""
            if len(indices) == 1:
                cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]
                idx = indices[0] - 1
                cn_str = cn_nums[idx] if idx < len(cn_nums) else str(indices[0])
                return f"{cn_str}、"
            return ".".join(str(x) for x in indices) + ". "

        def assemble_markdown_recursive(node: dict, segments_dir: str, depth: int = 3, indices: list = None) -> list:
            if indices is None:
                indices = []
            md_parts = []
            header_prefix = "#" * depth
            prefix = get_heading_prefix(indices)
            node_title = node.get("title", "Untitled")
            full_title = f"{prefix}{node_title}"
            
            if node.get("has_subchapters"):
                md_parts.append(f"\n{header_prefix} {full_title}\n")
                for c_idx, child in enumerate(node.get("children", []), 1):
                    md_parts.extend(assemble_markdown_recursive(child, segments_dir, depth + 1, indices + [c_idx]))
            else:
                md_parts.append(f"\n{header_prefix} {full_title}\n")
                
                leaf_uuid = node.get("uuid") or node.get("id")
                segment_path = os.path.join(segments_dir, f"{leaf_uuid}.md")
                content = "*(Summary generation failed)*"
                if os.path.exists(segment_path):
                    try:
                        with open(segment_path, "r", encoding="utf-8") as sf:
                            content = sf.read()
                    except Exception:
                        pass
                md_parts.append(content)
                
            return md_parts

        assembled_parts = []
        if overall_summary:
            assembled_parts.append("## Summary\n")
            assembled_parts.append(f"{overall_summary}\n")
            assembled_parts.append("## Highlights\n")

        for idx, chapter in enumerate(outline_data.get("outline", []), 1):
            assembled_parts.extend(assemble_markdown_recursive(chapter, segments_dir, depth=3, indices=[idx]))

        complete_markdown = "\n".join(assembled_parts).strip()
        complete_md_path = os.path.join(book_dir, "complete.md")
        with open(complete_md_path, "w", encoding="utf-8") as f:
            f.write(complete_markdown)
            
        return True
    except Exception as e:
        print(f"Error recompiling book {book_id}: {e}")
        return False
