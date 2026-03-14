# purpose is to manage playwright lifecycle and identity

from playwright.async_api import async_playwright


# import asyncio
class BrowserManager:
    def __init__(self):
        self.browser = None  # chromium browser obj
        self.playwright = None  # playwright crawler, manages browser

    # Launches Playwright browser with optional proxy settings,
    # and includes args to make it more stealthy.
    # Returns the browser instance.
    async def launch(self, proxy=None):
        self.playwright = await async_playwright().start()
        launch_args = {
            "headless": True,
            "args": [  # look more into these args,
                # they are meant to make the browser more stealthy
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        }

        if proxy:
            launch_args["proxy"] = proxy

        self.browser = await self.playwright.chromium.launch(**launch_args)
        return self.browser

    # Creates browser context + optional user agent (for identity)
    # and includes a script to make it more stealthy. Returns the context instance.
    async def new_context(self, user_agent=None):
        if not self.browser:
            raise Exception("Browser not launched. Call launch() first.")

        context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800}, user_agent=user_agent
        )

        # for stealth
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        return context

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
