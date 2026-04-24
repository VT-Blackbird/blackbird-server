# manages proxies for scraping tasks

import random

# =============================================
# ProxyManager: Handles proxy management for scraping tasks
# - Initializes with a list of proxies
# - Provides method to get a random proxy for browser setup
# We will be using Webshare to handle proxies
# =============================================
from typing import List, Optional, TypedDict


class ProxyConfig(TypedDict):
    id: Optional[int]
    server: str
    username: Optional[str]
    password: Optional[str]
    language: Optional[str]
    region: Optional[str]


class ProxyManager:

    def __init__(self, proxies: Optional[List[ProxyConfig]] = None) -> None:

        if proxies is None:
            self.proxies: List[ProxyConfig] = []
        else:
            assert isinstance(
                proxies, list
            ), "Proxies should be a list of proxy configuration dicts"

            self.proxies = proxies
        if self.proxies is None:
            raise AttributeError("Proxies should not be None")
        self.curr_proxy: Optional[ProxyConfig] = None

    # --------------------------------------------------
    # Return rotating proxy
    # --------------------------------------------------

    def get_proxy(self) -> Optional[ProxyConfig]:

        if not self.proxies:
            return None

        base = self.proxies[random.randint(0,
                                           len(self.proxies) -1)]

        proxy = ProxyConfig(
            id=base.get("id"),
            server=base["server"],
            username=base["username"],
            password=base.get("password"),
            language=base.get("language"),
            region=base.get("region"),
        )
        assert proxy is not None
        self.curr_proxy = proxy
        return proxy

    def get_curr_proxy(self) -> Optional[ProxyConfig]:
        return self.curr_proxy

    # --------------------------------------------------
    # Proxy string helper (for httpx / gnewsdecoder)
    # --------------------------------------------------
    def get_rotating_proxy_url(self) -> Optional[str]:
        """
        Returns proxy string with new Webshare session.
        Forces IP rotation.
        """
        try:
            proxy: Optional[ProxyConfig] = self.get_proxy()
        except Exception as e:
            print("error with get_proxy in url func. ", e)
        if proxy is None:
            print("Proxy is None")
            return None
        #must be single quotes to access proxy key
        pr:str =""

        if proxy:
            if proxy["username"] and proxy["password"]:
                pr = f"http://{proxy['username']}:{proxy['password']}@{proxy['server']}"
            else:
                pr = f"http://{proxy['server']}"
        # pr=f"http://{proxy['username']}:{proxy['password']}@{proxy['server']}"
        return pr
