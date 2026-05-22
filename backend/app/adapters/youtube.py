from typing import Optional, Dict, Any
from app.adapters.base import BaseAdapter

class YoutubeAdapter(BaseAdapter):
    service_id: str = "youtube"
    display_name: str = "YouTube"
    description: str = "YouTube 国际视频平台解析适配器"

    async def get_metadata(self) -> Dict[str, Any]:
        from app.services.subtitles import fetch_youtube_subtitle_urls
        import re
        video_id = self.url_or_id
        if "youtube.com" in video_id or "youtu.be" in video_id:
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", video_id)
            if match:
                video_id = match.group(1)
        try:
            data = await fetch_youtube_subtitle_urls(video_id)
            title = data.get("title", "YouTube Video")
            return {
                "title": title,
                "uploader": "YouTube Creator",
                "description": f"YouTube Video Title: {title}",
            }
        except Exception as e:
            print(f"YoutubeAdapter get_metadata error: {e}")
            return {"title": "YouTube Video", "uploader": "YouTube Creator", "description": ""}

    async def get_download_url(self) -> Optional[str]:
        return None

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.youtube.com",
        }
