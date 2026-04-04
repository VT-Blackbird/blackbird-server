import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from googlenewsdecoder import gnewsdecoder
from playwright.async_api import Browser, BrowserContext, Page
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from sqlmodel import Session, select

from app.db.session import engine
from app.models.source import Source
from app.workers.core.browser_manager import BrowserManager
from app.workers.core.proxy_manager import ProxyConfig, ProxyManager
from app.workers.core.query import Query
from app.workers.core.utils import random_delay, save_json


# =============================================
# ParentScraper: Base class for all scrapers,
#  handles browser setup, proxy management,
# and common scraping tasks.
# =============================================
class ParentScraper:
    # initializes parent scraper, optional proxies and user agent
    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.browser_manager = BrowserManager()
        self.proxy_manager = ProxyManager(proxies)

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.curr_proxy: Optional[ProxyConfig] = None

        self.user_agent: Optional[str] = user_agent
        self.MAX_CONCURRENT: int = 10  # max concurrent article fetches
        # max number of articles will try to scrape full article contents from
        self.MAX_SECONDARY_SCRAPE: int = 25

    # Main method to run the scraper, handles setup,
    # scraping, saving results, and cleanup
    async def run(self, query: Any, lan: str, region: str) -> Optional[List[Any]]:
        await self.setup()
        results: Optional[List[Any]] = None
        try:
            results = await self.scrape(query, lan, region)
            if results:
                await self.save_results(query, results)
                print(f"Found Results for query: {query.text}")
            else:
                print(f"No results found for {query.text}")
        except Exception as e:
            print(f"received the following exception: {e}")
        finally:
            await self.close()
            return results

    # Setup browser with proxy and user agent
    async def setup(self) -> None:
        if self.page:
            return  # If already set up
        self.curr_proxy = self.proxy_manager.get_proxy()
        self.browser = await self.browser_manager.launch(self.curr_proxy)
        if not self.browser:
            return
        self.context = await self.browser_manager.new_context(
            user_agent=self.user_agent
        )
        if self.context:
            self.page = await self.context.new_page()  # Pagination

    # Closes browser and cleans up resources
    async def close(self) -> None:
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.browser_manager:
            await self.browser_manager.close()

        # reset references
        self.page = None
        self.context = None
        self.browser = None
        self.curr_proxy = None

    async def goto(self, url: str) -> Optional[str]:
        if not self.page or not self.context:
            return None
        temp_page = await self.context.new_page()
        if not temp_page:
            return None
        try:
            await temp_page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await random_delay()
            html = await temp_page.content()
            return html
        except PlaywrightTimeoutError:
            print(f"Timeout while navigating to {url}")
            await temp_page.close()
            return None
        except PlaywrightError as e:
            print(f"Playwright navigation error: {e}")
            return None

    def get_source_config(self, name: str) -> Optional[Source]:
        """Fetches source configuration from the database by name."""
        with Session(engine) as session:
            statement = select(Source).where(Source.name == name)
            return session.exec(statement).first()

    async def fetch_rss(self, url: str) -> Optional[str]:
        if self.user_agent is None:
            raise RuntimeError("User-Agent not initialized")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/rss+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://news.google.com/",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            if not resp or not resp.status_code:
                return None
            if resp.status_code == 200:
                return resp.text
        return None

    async def load(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        if self.context:
            try:
                response = await self.context.request.get(url, timeout=15000)
                content_type = response.headers.get("content-type", "")
                if "xml" in content_type:
                    return await response.text(), "xml"
                if "text/html" in content_type:
                    return await response.text(), "html"
            except Exception:
                pass

        success: Optional[str] = await self.goto(url)
        if not success or not self.page:
            return None, None

        return await self.page.content(), "html"

    async def scrape(self, query: Any, lan: str, region: str) -> List[Any]:
        raise NotImplementedError

    @staticmethod
    async def save_results(query: Any, results: List[Any]) -> None:
        save_json(results, f"./Query_{query.id}_results.json")

    async def scroll_until_stable(
        self,
        selector: str,
        max_rounds: int = 10,
        scroll_step: int = 3000,
        delay_range: Tuple[float, float] = (1.5, 3.0),
    ) -> None:
        if not self.page:
            return
        print("called Scroll until stable")
        last_count = 0

        for round_num in range(max_rounds):
            elements = await self.page.query_selector_all(selector)
            current_count = len(elements)
            if current_count == last_count:
                break
            last_count = current_count
            await self.page.mouse.wheel(0, scroll_step)
            await random_delay(*delay_range)

    async def html_fallback(
        self, query: Query, lan: str, region: str, source_id: int
    ) -> List[Dict[str, Any]]:
        print("RSS empty → falling back to HTML search")

        html_url = (
            "https://news.google.com/search?"
            f"q={urllib.parse.quote(query.text)}"
            f"&hl={lan}&gl={region}&ceid={region}:{lan.split('-')[0]}"
        )

        html, ct = await self.load(html_url)

        if not html or ct != "html" or self.is_blocked(html):
            print("HTML blocked → trying Playwright")
            success = await self.goto(html_url)
            if success and self.page:
                html = await self.page.content()

        if html and not self.is_blocked(html):
            return self._parse_google_html(html, source_id)

        return []

    async def resolve_entries(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return await asyncio.gather(
            *(self._resolve_entry(e) for e in entries[: self.MAX_SECONDARY_SCRAPE])
        )

    async def fetch_articles(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        return await asyncio.gather(
            *(
                self._fetch_entry(e, semaphore)
                for e in entries[: self.MAX_SECONDARY_SCRAPE]
            )
        )

    async def _fetch_entry(
        self, entry: Dict[str, Any], semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        url = entry.get("url")
        if not url:
            entry["content"] = None
            return entry

        async with semaphore:
            html, ct = await self.load(url)
            if html and ct == "html" and not self.is_blocked(html):
                entry["content"] = self._extract_article_text(html)
                return entry

            success = await self.goto(url)
            if success and self.page:
                html = await self.page.content()
                if html and not self.is_blocked(html):
                    entry["content"] = self._extract_article_text(html)
                    return entry

            entry["content"] = None
            return entry

    async def _resolve_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        wrapper = entry["url"]
        real_url = await asyncio.to_thread(self.resolve_google_news_url, wrapper)
        if real_url:
            entry["url"] = real_url
        else:
            entry["content"] = None
        return entry

    def is_blocked(self, html: str) -> bool:
        html = html.lower()
        blockers = [
            "just a moment",
            "access denied",
            "enable javascript",
            "enable js",
            "cf-browser-verification",
            "cloudflare",
            "Access to this page has been blocked",
            "Access to the page you are trying to view",
            "supports JavaScript and cookies",
            "sending automated queries",
        ]
        return any(b in html for b in blockers)

    def parse_rss(self, content: str, source_id: int) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        root = ET.fromstring(content)
        channel = root.find("channel")
        if channel is None:
            return articles

        for item in channel.findall("item"):
            title = item.findtext("title")
            caption = item.findtext("description")
            pub_date = item.findtext("pubDate")
            wrapper_url = item.findtext("link")
            articles.append(
                {
                    "source_id": source_id,
                    "title": title,
                    "content": caption if caption else title,
                    "url": wrapper_url,
                    "published_at": pub_date,
                    "sentiment_label": None,
                    "sentiment_score": None,
                }
            )
        return articles

    def _parse_google_html(self, html: str, source_id: int) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        articles: List[Dict[str, Any]] = []

        for link_tag in soup.select('a[href^="./articles"]'):
            if not link_tag:
                continue
            href_raw = link_tag.get("href")
            title_raw = link_tag.get("title")

            if not isinstance(href_raw, str) or not isinstance(title_raw, str):
                continue

            href = href_raw
            title = title_raw
            if href.startswith("./"):
                url = urllib.parse.urljoin("https://news.google.com/", href)
            else:
                url = href
            articles.append(
                {
                    "source_id": source_id,
                    "title": title,
                    "url": url,
                    "content": title,
                    "published_at": None,
                    "sentiment_label": None,
                    "sentiment_score": None,
                }
            )
        return articles

    def _extract_article_text(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        paragraphs = soup.select("article p")
        if not paragraphs:
            paragraphs = soup.select("p")

        text = " ".join(p.get_text(strip=True) for p in paragraphs)
        return text if len(text) > 50 else None

    def resolve_google_news_url(self, wrapper_url: str) -> Optional[str]:
        try:
            proxy_str: Optional[str] = self.proxy_manager.get_rotating_proxy_url()
            decoded: Any
            if not proxy_str:
                decoded = gnewsdecoder(wrapper_url)
            else:
                decoded = gnewsdecoder(wrapper_url, proxy=proxy_str)

            if not isinstance(decoded, dict):
                return None

            decoded_url = decoded.get("decoded_url")
            if not isinstance(decoded_url, str):
                return None

            return decoded_url

        except Exception as e:
            print(f"\t\t GNewsDecoder Error: {e}")
            return None