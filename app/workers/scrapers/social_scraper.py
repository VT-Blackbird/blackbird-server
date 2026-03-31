import json
import os
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, cast

from app.workers.core.parent_scraper import ParentScraper
from app.workers.core.query import Query
from app.workers.core.utils import save_json


class SocialScraper(ParentScraper):
    # Platform configurations (Will be updated to use database soon)
    CONFIGS = {
        "reddit": {
            "url": "https://www.reddit.com/search.rss?",
            "type": "rss",
            "source_id": 1,
        },
        "bluesky": {
            # Standard AppView endpoint
            "url": "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?",
            "auth_url": "https://bsky.social/xrpc/com.atproto.server.createSession",
            "type": "json",
            "source_id": 4,
        },
    }

    # Authentication credentials (See env_example.txt for more info)
    BSKY_HANDLE = os.environ.get("BSKY_HANDLE", "")
    BSKY_APP_PASSWORD = os.environ.get("BSKY_APP_PASSWORD", "")

    _bsky_token: Optional[str] = None

    async def _login_bsky(self) -> Optional[str]:
        """Authenticates Bluesky. If 502/Auth fails, None for public fallback."""
        if self._bsky_token:
            return self._bsky_token

        if not self.BSKY_HANDLE or not self.BSKY_APP_PASSWORD:
            return None

        if not self.context:
            return None

        print(
            f"[SocialScraper] Authenticating Bluesky session for {self.BSKY_HANDLE}..."
        )

        try:
            auth_url = cast(str, self.CONFIGS["bluesky"]["auth_url"])
            response = await self.context.request.post(
                auth_url,
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
                print(f"[SocialScraper] Auth status {response.status}")
        except Exception as e:
            print(f"[SocialScraper] Auth error: {e}")

        return None

    def build_url(self, platform: str, query: Query, language: str, region: str) -> str:
        base = cast(str, self.CONFIGS[platform]["url"])

        if platform == "reddit":
            params = {
                "q": query.text,
                "sort": "relevance",
                "t": "all",
                "hl": language,
                "gl": region,
            }
            return f"{base}{urllib.parse.urlencode(params)}"

        elif platform == "bluesky":
            q_encoded = urllib.parse.quote(query.text)
            params = {"limit": "50", "sort": "top"}
            if language:
                params["lang"] = language.split("-")[0]

            query_string = urllib.parse.urlencode(params)
            return f"{base}q={q_encoded}&{query_string}"

        return ""

    async def scrape(self, query: Query, lan: str, region: str) -> List[Dict[str, Any]]:
        all_results: List[Dict[str, Any]] = []

        # 1. Reddit
        reddit_url = self.build_url("reddit", query, lan, region)
        print(f"[SocialScraper] Fetching reddit: {reddit_url}")
        r_content, _ = await self.load(reddit_url)
        if r_content:
            all_results.extend(self.parse_rss(r_content))

        # 2. Bluesky
        token = await self._login_bsky()
        bsky_url = self.build_url("bluesky", query, lan, region)
        print(f"[SocialScraper] Fetching bluesky: {bsky_url}")

        b_content = None
        if self.context:
            # Set headers. If auth failed, send a standard User-Agent only.
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            try:
                response = await self.context.request.get(
                    bsky_url, headers=headers, timeout=15000
                )
                if response.ok:
                    b_content = await response.text()
                else:
                    print(f"[SocialScraper] Bluesky request failed: {response.status}")
                    # If 403 occurs even with Auth, log the body for debugging
                    if response.status == 403:
                        body = await response.text()
                        print(f"[SocialScraper] 403 Details: {body[:100]}")
            except Exception as e:
                print(f"[SocialScraper] Bluesky request error: {e}")

        if b_content:
            stripped = b_content.strip()
            if stripped.startswith("{"):
                all_results.extend(self.parse_bluesky_json(stripped))
            else:
                print(
                    f"[SocialScraper] Received non-JSON from Bluesky: {stripped[:100]}"
                )

        return all_results

    def parse_bluesky_json(self, content: str) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        try:
            data = json.loads(content)
            if "error" in data:
                print(f"[SocialScraper] Bluesky API error: {data.get('message')}")
                return []

            for post in data.get("posts", []):
                author = post.get("author", {})
                record = post.get("record", {})
                handle = author.get("handle", "unknown")

                uri = post.get("uri", "")
                rkey = uri.split("/")[-1] if "/" in uri else ""
                post_url = f"https://bsky.app/profile/{handle}/post/{rkey}"

                articles.append(
                    {
                        "source_id": self.CONFIGS["bluesky"]["source_id"],
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

    def parse_rss(self, content: str) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        try:
            namespaces = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(content)
            for entry in root.findall("atom:entry", namespaces):
                link_tag = entry.find("atom:link", namespaces=namespaces)

                url = ""
                if link_tag is not None:
                    raw_url = link_tag.get("href")
                    url = raw_url if raw_url else ""

                if "/comments/" not in url:
                    continue

                articles.append(
                    {
                        "source_id": 1,
                        "title": entry.findtext("atom:title", namespaces=namespaces),
                        "content": entry.findtext("atom:content", namespaces=namespaces)
                        or "",
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
