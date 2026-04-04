import asyncio
import json
import os
import random
from typing import Any, List

from dotenv import load_dotenv

from app.workers.core.proxy_manager import ProxyConfig

load_dotenv()


def load_proxies() -> List[ProxyConfig]:
    raw = os.getenv("PROXIES_JSON")

    if not raw:
        return []

    try:
        proxies = json.loads(raw)

        # Validate structure matches ProxyConfig
        cleaned = []
        for p in proxies:
            cleaned.append(
                ProxyConfig(
                    server=p["server"],
                    username=p.get("username"),
                    password=p.get("password"),
                    region=p.get("region"),
                    language=p.get("language"),
                )
            )

        return cleaned

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid PROXIES_JSON format: {e}")

async def random_delay(min_s:float=1, max_s:float=3)->None:
    await asyncio.sleep(random.uniform(min_s, max_s))


def save_json(data:Any, filename:str)->None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
