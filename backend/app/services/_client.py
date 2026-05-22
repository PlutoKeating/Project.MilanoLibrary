import random
from typing import Optional
from openai import AsyncOpenAI
from app.config import settings


def select_api_key(user_key: Optional[str]) -> str:
    if user_key:
        keys = [k.strip() for k in user_key.split(",") if k.strip()]
        return random.choice(keys)

    my_keys = settings.openai_compatible_api_key or settings.openai_api_key
    if my_keys:
        keys = [k.strip() for k in my_keys.split(",") if k.strip()]
        return random.choice(keys)
    return ""


def create_client(base_url: Optional[str] = None) -> AsyncOpenAI:
    url = base_url or settings.openai_compatible_base_url or "https://api.openai.com/v1"
    return AsyncOpenAI(
        base_url=url,
        api_key="dummy",  # will be set per-request
    )
