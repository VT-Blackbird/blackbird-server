from typing import Any, List, Optional, Tuple, Union

from playwright.async_api import Browser, BrowserContext, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.workers.core.browser_manager import BrowserManager
from app.workers.core.proxy_manager import ProxyConfig, ProxyManager
from app.workers.core.utils import random_delay, save_json


# =============================================
# ParentScraper: Base class for all scrapers,
#  handles browser setup, proxy management,
# and common scraping tasks.
# =============================================
class ParentScraper:
    # initializes parent scraper, optional proxies and user agent
    def __init__(self, proxies: Optional[List[ProxyConfig]] = None,
                 user_agent: Optional[str] = None) -> None:
        self.browser_manager: BrowserManager = BrowserManager()
        self.proxy_manager: ProxyManager = ProxyManager(proxies)

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.curr_proxy: Optional[ProxyConfig] = None

        self.user_agent: Optional[str] = user_agent

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
            self.page = await self.context.new_page()

    # Closes browser and cleans up resources
    async def close(self) -> None:
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.browser_manager:
            await self.browser_manager.close() #closing might invalidate future launches if shared obj across scrpers

        #reset references
        self.page = None
        self.context = None
        self.browser = None

    # Navigates to a URL and waits for the DOM to load,
    # with random delay to mimic human behavior

    # ret boolean if successful or not
    async def goto(self, url: str) -> bool:
        if not self.page:
            return False
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=15000) #timeout in ms
            await random_delay()
            return True
        except PlaywrightTimeoutError:
            print(f"Timeout while navigating to {url}")
            return False

    async def fetch_rss(self, url: str) -> Union[str, bool]:
        if not self.context:
            return False
        try:
            response = await self.context.request.get(url, timeout=30000)
            if not response.ok:
                print(f"RSS fetch failed with status: {response.status}")
                return False

            return await response.text()
        except Exception as e:
            print(f"RSS fetch failed: {e}")
            return False

    async def load(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        if self.context:
            try:
                response = await self.context.request.get(url, timeout=15000)
                content_type = response.headers.get("content-type", "")

                if "xml" in content_type:
                    return await response.text(), "xml"

                # If it's HTML but static, return directly
                if "text/html" in content_type:
                    return await response.text(), "html"
            except Exception:
                pass  # fallback to browser

        success: bool = await self.goto(url)
        if not success or not self.page:
            return None, None

        return await self.page.content(), "html"

    # Placeholder for actual scraping, to be implemented by subclasses
    async def scrape(self, query: Any, lan: str, region: str) -> List[Any]:
        raise NotImplementedError

    # # Placeholder for saving results, to be implemented by subclasses
    @staticmethod
    async def save_results(query: Any, results: List[Any]) -> None:
        save_json(results, f"./Query_{query.id}_results.json")

    # usage: for infinite scrolling pages
    # Scrolls until number of elements matching selector stops increasing
    # random delay between scrolls
    async def scroll_until_stable(
        self,
        selector: str,
        max_rounds: int = 10,
        scroll_step: int = 3000,
        delay_range: Tuple[float, float]=(1.5, 3.0),
    ) -> None:
        if not self.page:
            return
        print("called Scroll until stable")
        last_count = 0

        for round_num in range(max_rounds):
            print(f"[scroll] round={round_num} of {max_rounds}")
            elements = await self.page.query_selector_all(selector)
            current_count = len(elements)

            print(f"items={current_count}")

            # stop condition
            if current_count == last_count:
                print("[scroll] content stabilized")
                break

            last_count = current_count

            # human(ish) scrolling
            await self.page.mouse.wheel(0, scroll_step)

            await random_delay(*delay_range)

    def get_curr_proxy(self) -> Optional[ProxyConfig]:
        return self.curr_proxy

    # Main method to run the scraper, handles setup,
    # scraping, saving results, and cleanup
    # Orchestrates scraping workflow:
    # 1. Sets up browser and proxy
    # 2. Executes scraping logic defined in subclass
    # 3. Saves results using subclass implementation
    # lan  - language of proxy
    # region - region proxy is based
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
