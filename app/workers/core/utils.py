import asyncio
import json
import os
import random
from typing import Any, List, Literal

from dotenv import load_dotenv
from sqlmodel import Session, select

from app.db.session import engine
from app.models.proxy import Proxy
from app.workers.core.proxy_manager import ProxyConfig

load_dotenv()


def load_proxies(source: Literal["db", "env"] = "db") -> List[ProxyConfig]:
    """
    Load proxies from either the database or the environment JSON.

    Args:
        source: "db" to pull from PostgreSQL (default), "env" to pull .env PROXIES_JSON.
    Note: This assumes init.py has been run at least once to create the proxy table.
    """
    if source == "env":
        return load_proxies_from_env()
    return load_proxies_from_db()


def load_proxies_from_env() -> List[ProxyConfig]:
    """Parses PROXIES_JSON from environment variables."""
    raw = os.getenv("PROXIES_JSON")

    if not raw:
        return []

    try:
        proxies = json.loads(raw)
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
        print(f"[Utils] Loaded {len(cleaned)} proxies from environment.")
        return cleaned

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid PROXIES_JSON format: {e}")


def load_proxies_from_db() -> List[ProxyConfig]:
    """Queries active proxies from the database and formats them as ProxyConfig."""
    with Session(engine) as session:
        # Fetch only active proxies
        statement = select(Proxy).where(Proxy.is_active)
        results = session.exec(statement).all()
        print(f"[Utils] Loaded {len(results)} proxies from database.")

        return [
            ProxyConfig(
                server=p.server,
                username=p.username,
                password=p.password,
                region=p.region,
                language=p.language,
            )
            for p in results
        ]


async def random_delay(min_s: float = 1, max_s: float = 3) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


def save_json(data: Any, filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
