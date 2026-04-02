import json
import os
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.query import Query
from app.workers.core.utils import save_json


class SocialScraper(ParentScraper):
    # Bluesky requires custom auth URL; not in Source table base_url
    BSKY_AUTH_URL = "https://bsky.social/xrpc/com.atproto.server.createSession"

    # Authentication credentials
    BSKY_HANDLE = os.environ.get("BSKY_HANDLE", "")
    BSKY_APP_PASSWORD = os.environ.get("BSKY_APP_PASSWORD", "")

    _bsky_token: Optional[str] = None

    async def _login_bsky(self) -> Optional[str]:
        """Authenticates Bluesky using environment credentials."""
        if self._bsky_token:
            return self._bsky_token

        if not self.BSKY_HANDLE or not self.BSKY_APP_PASSWORD or not self.context:
            return None

        print(f"[SocialScraper] Authenticating Bluesky for {self.BSKY_HANDLE}...")

        try:
            response = await self.context.request.post(
                self.BSKY_AUTH_URL,
                data={
                    "identifier": self.BSKY_HANDLE,
                    "password": self.BSKY_APP_PASSWORD,
                },
                timeout=10000,
            )

            if response.ok:
                data = await response.json()
                self._bsky_token = data.get("accessJwt")
                return self._bsky_token
            else:
                print(f"[SocialScraper] Auth failed with status {response.status}")
        except Exception as e:
            print(f"[SocialScraper] Auth error: {e}")

        return None

    def build_url(
        self,
        base_url: str,
        platform: str,
        query: Query,
        language: str,
        region: str,
    ) -> str:
        if platform == "Reddit":
            params = {
                "q": query.text,
                "sort": "relevance",
                "t": "all",
                "hl": language,
                "gl": region,
            }
            return f"{base_url}{urllib.parse.urlencode(params)}"

        elif platform == "Bluesky":
            q_encoded = urllib.parse.quote(query.text)
            params = {"limit": "50", "sort": "top"}
            if language:
                params["lang"] = language.split("-")[0]
            return f"{base_url}q={q_encoded}&{urllib.parse.urlencode(params)}"

        return ""

    async def scrape(self, query: Query, lan: str, region: str) -> List[Dict[str, Any]]:
        all_results: List[Dict[str, Any]] = []

        # 1. Fetch Reddit from DB
        reddit_cfg = self.get_source_config("Reddit")
        if reddit_cfg and reddit_cfg.is_enabled:
            url = self.build_url(reddit_cfg.base_url, "Reddit", query, lan, region)
            print(f"[SocialScraper] Fetching reddit: {url}")
            content, _ = await self.load(url)
            if content:
                all_results.extend(self.parse_rss(content, reddit_cfg.id))

        # 2. Fetch Bluesky from DB
        bsky_cfg = self.get_source_config("Bluesky")
        if bsky_cfg and bsky_cfg.is_enabled:
            token = await self._login_bsky()
            url = self.build_url(bsky_cfg.base_url, "Bluesky", query, lan, region)
            print(f"[SocialScraper] Fetching bluesky: {url}")

            headers = {
                "User-Agent": self.user_agent or "Mozilla/5.0",
                "Accept": "application/json",
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            try:
                if self.context:
                    response = await self.context.request.get(
                        url, headers=headers, timeout=15000
                    )
                    if response.ok:
                        content = await response.text()
                        all_results.extend(
                            self.parse_bluesky_json(content, bsky_cfg.id)
                        )
            except Exception as e:
                print(f"[SocialScraper] Bluesky request error: {e}")

        return all_results

    def parse_bluesky_json(self, content: str, source_id: int) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        try:
            data = json.loads(content)
            for post in data.get("posts", []):
                author = post.get("author", {})
                record = post.get("record", {})
                handle = author.get("handle", "unknown")
                uri = post.get("uri", "")
                rkey = uri.split("/")[-1] if "/" in uri else ""
                post_url = f"https://bsky.app/profile/{handle}/post/{rkey}"

                articles.append(
                    {
                        "source_id": source_id,
                        "title": f"Post by @{handle}",
                        "content": record.get("text", ""),
                        "url": post_url,
                        "published_at": record.get("createdAt"),
                        "sentiment_label": None,
                        "sentiment_score": None,
                    }
                )
        except Exception as e:
            print(f"[SocialScraper] Bluesky parsing error: {e}")
        return articles

    def parse_rss(self, content: str, source_id: int) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        try:
            namespaces = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(content)
            for entry in root.findall("atom:entry", namespaces):
                link_tag = entry.find("atom:link", namespaces=namespaces)
                url = link_tag.get("href") if link_tag is not None else ""
                if "/comments/" not in url:
                    continue

                articles.append(
                    {
                        "source_id": source_id,
                        "title": entry.findtext("atom:title", namespaces=namespaces),
                        "content": (
                            entry.findtext("atom:content", namespaces=namespaces) or ""
                        ),
                        "url": url,
                        "published_at": entry.findtext(
                            "atom:updated", namespaces=namespaces
                        ),
                        "sentiment_label": None,
                        "sentiment_score": None,
                    }
                )
        except Exception as e:
            print(f"[SocialScraper] Reddit RSS error: {e}")
        return articles

    @staticmethod
    async def save_results(query: Query, results: List[Any]) -> None:
        filename = f"./Query_{query.id}_SocialScraper_results.json"
        save_json(results, filename)
        print(f"[SocialScraper] Results saved to {filename}")
