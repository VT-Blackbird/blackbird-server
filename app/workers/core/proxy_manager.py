# manages proxies for scraping tasks
##TODO: implement proxy rotation and error handling for failed proxies,
## TODO: integrate external service for proxy management

import random


# =============================================
# ProxyManager: Handles proxy management for scraping tasks
# - Initializes with a list of proxies
# - Provides method to get a random proxy for browser setup
# We will be using Webshare to handle proxies
# =============================================
class ProxyManager:
    # proxies should be in format
    #[{"server": "ip:port", "username": "user", "password": "pass"}, ...]
    def __init__(self, proxies=None):
        if proxies is None:
            proxies = []
        else:
            assert isinstance(
                proxies, list
            ), "Proxies should be a list of proxy configuration dicts"
            self.proxies = proxies

    # Returns Random Proxy config from list
    def get_proxy(self):
        if not self.proxies:
            return None

        proxy = random.choice(self.proxies)

        return {
            "server": proxy["server"],
            "username": proxy.get("username"),  # optional
            "password": proxy.get(
                "password"
            ),  # optional, depends on proxy provider and setup
            "language": proxy.get("language"),
            "region": proxy.get("region"),
        }
