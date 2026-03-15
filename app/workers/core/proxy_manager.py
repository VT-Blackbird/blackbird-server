# manages proxies for scraping tasks
##TODO: implement proxy rotation and error handling for failed proxies,
## TODO: integrate external service for proxy management

import random
from typing import List, Optional, TypedDict

# =============================================
# ProxyManager: Handles proxy management for scraping tasks
# - Initializes with a list of proxies
# - Provides method to get a random proxy for browser setup
# We will be using Webshare to handle proxies
# =============================================
class ProxyConfig(TypedDict):
    server: str
    username: Optional[str]
    password: Optional[str]
    language: Optional[str]
    region: Optional[str]
class ProxyManager:
    # proxies should be in format
    #[{"server": "ip:port", "username": "user", "password": "pass"}, ...]
    def __init__(self, proxies:Optional[List[ProxyConfig]]=None)->None:
        if proxies is None:
            self.proxies:List[ProxyConfig] = []
        else:
            assert isinstance(
                proxies, list
            ), "Proxies should be a list of proxy configuration dicts"
            self.proxies = proxies

    # Returns Random Proxy config from list
    def get_proxy(self)-> Optional[ProxyConfig]:
        if not self.proxies:
            return None

        proxy = random.choice(self.proxies)

        return  ProxyConfig(
            server=proxy["server"],
            username=proxy.get("username"),
            password=proxy.get("password"),
            language=proxy.get("language"),
            region=proxy.get("region"),
        )
        
