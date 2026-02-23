import asyncio
from datetime import datetime

from app.workers.scrapers.gov_scraper import GovScraper
from app.workers.scrapers.social_scraper import SocialScraper
from scrapers.news_scraper import NewsScraper
from app.workers.core.query import Query   # if you created one

import traceback
# -----------------------------
# USER CONFIGURATION
# -----------------------------

QUERIES = [
    Query(text="Hegseth AND DOW Spending"),
    Query(text="vibe coding"),
]

#No proxies implemented yet, but you can add them here if needed
# country_code = "US"     # User can change this to FR, DE, GB, etc.
PROXIES = [{
        'server':"23.95.150.145:6114",    # enter your password
        'username':"glsdbmdq",
        'password':"b0p2nqm0pc47",
        'region':"US", #generally country
        'language': "en-US",
    }, {
        'server': "198.23.239.134:6540",
        'username':"glsdbmdq",
        'password':"b0p2nqm0pc47",
        'region':"US", 'language': "en-US",
}]
# # PROXIES = None #disable proxies for now, not fully implemented yet
# 23.95.150.145:6114:glsdbmdq:b0p2nqm0pc47
# 198.23.239.134:6540:glsdbmdq:b0p2nqm0pc47
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# -----------------------------
# Runner
# -----------------------------

async def run_scraper():
    scrapers = [NewsScraper(
        proxies=PROXIES,
        user_agent=USER_AGENT,
    ), SocialScraper(
        proxies=PROXIES,
        user_agent=USER_AGENT,
    ), GovScraper(
        proxies=PROXIES,
        user_agent=USER_AGENT,
    )]

    all_results = []

    start_time = datetime.now()
    for scraper in scrapers:
        print(f"\n=== Running scraper: {scraper.__class__.__name__} ===")

        for i, query in enumerate(QUERIES, start=1):
            print(f"\n[{i}/{len(QUERIES)}] Running query: {query.text}")
            await scraper.setup()
            try:
                proxy = scraper.get_curr_proxy()
                results = await scraper.run(query, proxy['language'], proxy['region'])
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