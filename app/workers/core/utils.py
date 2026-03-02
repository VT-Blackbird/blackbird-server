import asyncio
import json
import random
from typing import Any

# Utility functions for scrapers, including random delay and JSON saving


async def random_delay(min_s:float=1, max_s:float=3) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


def save_json(data: Any, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
