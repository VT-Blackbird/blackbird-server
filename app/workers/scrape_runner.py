import asyncio
import traceback
from datetime import datetime
from typing import Any, List

from app.workers.core.proxy_manager import ProxyConfig
from app.workers.core.query import Query  # if you created one
from app.workers.scrapers.gov_scraper import GovScraper
from app.workers.scrapers.news_scraper import NewsScraper
from app.workers.scrapers.social_scraper import SocialScraper

# -----------------------------
# USER CONFIGURATION
# -----------------------------

QUERIES = [
    # Query(text="Hegseth AND DOW Spending"),
    # Query(text="AFA")
    # Query(text="DOW AI"),
    Query(text="Drone CCA")
    # Query(text="Artificial Intelligence")
]

# No proxies implemented yet, but you can add them here if needed
# country_code = "US"     # User can change this to FR, DE, GB, etc.
#Proxy Manager, rotation

PROXIES: List[ProxyConfig] = [
    {
        "server": "38.55.72.2:80",
        "username": "glsdbmdq-us-1",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "37.120.205.78:80",
        "username": "glsdbmdq-us-2",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "162.218.95.11:80",
        "username": "glsdbmdq-us-3",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "193.19.206.5:80",
        "username": "glsdbmdq-us-4",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "198.20.161.66:80",
        "username": "glsdbmdq-us-5",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "192.3.28.110:80",
        "username": "glsdbmdq-us-6",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "209.127.184.242:80",
        "username": "glsdbmdq-us-7",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "38.120.82.27:80",
        "username": "glsdbmdq-us-8",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "38.55.72.2:80",
        "username": "glsdbmdq-us-9",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
    {
        "server": "37.120.205.78:80",
        "username": "glsdbmdq-us-10",
        "password": "b0p2nqm0pc47",
        "region": "US",
        "language": "en-US"
    },
]
# # PROXIES = None #disable proxies for now, not fully implemented yet
# 23.95.150.145:6114:glsdbmdq:b0p2nqm0pc47
# 198.23.239.134:6540:glsdbmdq:b0p2nqm0pc47
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# -----------------------------
# Runner
# -----------------------------


async def run_scraper() ->None:
    scrapers: List[Any] = {
        NewsScraper(
            proxies=PROXIES,
            user_agent=USER_AGENT,
        ),
        SocialScraper(
            proxies=PROXIES,
            user_agent=USER_AGENT,
        ),
        GovScraper(
            proxies=PROXIES,
            user_agent=USER_AGENT,
        ),
    }

    all_results :List[Any]= []

    start_time = datetime.now()
    for scraper in scrapers:
        print(f"\n=== Running scraper: {scraper.__class__.__name__} ===")

        for i, query in enumerate(QUERIES, start=1):
            print(f"\n[{i}/{len(QUERIES)}] Running query: {query.text}")
            await scraper.setup()
            try:
                proxy = scraper.get_curr_proxy()
                results = await scraper.run(query, proxy["language"], proxy["region"])
                all_results.extend(results or [])

            except Exception as e:
                print(f"Query failed: {query.text}")
                print(e)
                traceback.print_exc()  # Prints to console

    elapsed = datetime.now() - start_time

    print("\n===== SUMMARY =====")
    print(f"Total results: {len(all_results)}")
    print(f"Elapsed time: {elapsed}")


# -----------------------------
# Entry Point
# -----------------------------

if __name__ == "__main__":
    asyncio.run(run_scraper())
