import random
import httpx
from typing import Optional, Dict, Any
from app.adapters.base import BaseAdapter
from app.config import settings

class BilibiliAdapter(BaseAdapter):
    service_id: str = "bilibili"
    display_name: str = "Bilibili"
    description: str = "哔哩哔哩视频平台解析适配器"

    def __init__(self, url_or_id: str, page_number: Optional[str] = None):
        super().__init__(url_or_id, page_number)
        self._cached_metadata: Optional[Dict[str, Any]] = None

    async def get_metadata(self) -> Dict[str, Any]:
        if self._cached_metadata is not None:
            return self._cached_metadata

        from app.services.subtitles import fetch_bilibili_subtitle_urls
        import re
        video_id = self.url_or_id
        if "bilibili.com" in video_id:
            match = re.search(r"/(BV\w+|av\d+)", video_id)
            if match:
                video_id = match.group(1)
        try:
            data = await fetch_bilibili_subtitle_urls(video_id, self.page_number)
            title = data.get("title", "")
            uploader = data.get("owner", {}).get("name", "")
            desc = data.get("desc", "")
            dynamic = data.get("dynamic", "")
            description = f"{desc}\n{dynamic}".strip()
            cid = data.get("cid")
            aid = data.get("aid")
            duration = data.get("duration", 0)
            res = {
                "title": title,
                "uploader": uploader,
                "description": description,
                "cid": cid,
                "aid": aid,
                "duration_seconds": duration,
            }
            self._cached_metadata = res
            return res
        except Exception as e:
            print(f"Bilibili get_metadata error: {e}")
            return {"title": "Bilibili Video", "uploader": "Bilibili 博主", "description": ""}

    async def get_download_url(self) -> Optional[str]:
        meta = await self.get_metadata()
        aid = meta.get("aid")
        cid = meta.get("cid")
        if not aid or not cid:
            return None

        headers = self.get_headers()
        session_tokens = []
        if settings.bilibili_session_token:
            session_tokens = [t.strip() for t in settings.bilibili_session_token.split(",") if t.strip()]
        sessdata = random.choice(session_tokens) if session_tokens else None
        if sessdata:
            headers["Cookie"] = f"SESSDATA={sessdata}"

        playurl = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=16&fnval=16"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(playurl, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    dash = data.get("dash", {})
                    audio_list = dash.get("audio", [])
                    if audio_list:
                        return audio_list[0].get("baseUrl") or audio_list[0].get("base_url")
                    durl = data.get("durl", [])
                    if durl:
                        return durl[0].get("url")
        except Exception as e:
            print(f"Bilibili playurl fetch error: {e}")
        return None

    def get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.bilibili.com",
        }
