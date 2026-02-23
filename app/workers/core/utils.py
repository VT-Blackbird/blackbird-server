import asyncio
import random
import json

# Utility functions for scrapers, including random delay and JSON saving

async def random_delay(min_s=1, max_s=3):
    await asyncio.sleep(random.uniform(min_s, max_s))


def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)