from typing import Optional, Dict, Any

class BaseAdapter:
    # Class attributes to identify the adapter
    service_id: str = "base"
    display_name: str = "Base Adapter"
    description: str = "Base description"

    def __init__(self, url_or_id: str, page_number: Optional[str] = None):
        self.url_or_id = url_or_id
        self.page_number = page_number

    async def get_metadata(self) -> Dict[str, Any]:
        return {}

    async def get_download_url(self) -> Optional[str]:
        return None

    def get_headers(self) -> Dict[str, str]:
        return {}
