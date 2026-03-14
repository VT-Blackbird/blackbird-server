from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.workers.core.browser_manager import BrowserManager
from app.workers.core.proxy_manager import ProxyManager
from app.workers.core.utils import random_delay, save_json


# =============================================
# ParentScraper: Base class for all scrapers,
#  handles browser setup, proxy management,
# and common scraping tasks.
# =============================================
class ParentScraper:
    # initializes parent scraper, optional proxies and user agent
    def __init__(self, proxies=None, user_agent=None):
        self.browser_manager = BrowserManager()
        self.proxy_manager = ProxyManager(proxies)

        self.browser = None
        self.context = None
        self.page = None
        self.curr_proxy = None

        self.user_agent = user_agent

    # Setup browser with proxy and user agent
    async def setup(self):
        if self.browser:
            return  # If already set up

        self.curr_proxy = self.proxy_manager.get_proxy()

        self.browser = await self.browser_manager.launch(self.curr_proxy)

        self.context = await self.browser_manager.new_context(
            user_agent=self.user_agent
        )

        self.page = await self.context.new_page()  # Pagination

    # Closes browser and cleans up resources
    async def close(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        await self.browser_manager.close()

    # Navigates to a URL and waits for the DOM to load,
    # with random delay to mimic human behavior

    # ret boolean if successful or not
    async def goto(self, url):
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await random_delay()
            return True
        except PlaywrightTimeoutError:
            print(f"Timeout while navigating to {url}")
            return False

    async def fetch_rss(self, url):
        try:
            response = await self.context.request.get(url, timeout=30000)
            response.raise_for_status()
            return await response.text()
        except Exception as e:
            print(f"RSS fetch failed: {e}")
            return False

    async def load(self, url):
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

        success = await self.goto(url)
        if not success:
            return None, None

        return await self.page.content(), "html"

    # Placeholder for actual scraping, to be implemented by subclasses
    async def scrape(self, query, lan, region):
        raise NotImplementedError

    # Placeholder for saving results, to be implemented by subclasses
    @staticmethod
    async def save_results(query, results):
        save_json(results, f"./Query_{query.id}_results.json")

    # usage: for infinite scrolling pages
    # Scrolls until number of elements matching selector stops increasing
    # random delay between scrolls
    async def scroll_until_stable(
        self,
        selector: str,
        max_rounds: int = 10,
        scroll_step: int = 3000,
            delay_range=(1.5, 3.0),
    ):
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

    def get_curr_proxy(self):
        return self.curr_proxy

    # Main method to run the scraper, handles setup,
    # scraping, saving results, and cleanup
    # Orchestrates scraping workflow:
    # 1. Sets up browser and proxy
    # 2. Executes scraping logic defined in subclass
    # 3. Saves results using subclass implementation
    # lan  - language of proxy
    # region - region proxy is based
    async def run(self, query, lan, region):
        await self.setup()
        results = None
        try:
            results = await self.scrape(query, lan, region)
            await self.save_results(query, results)

        finally:
            # print("Done!")
            await self.close()
            return results
