import asyncio
import traceback
from datetime import datetime
from typing import Any, Dict, List, Type

from sqlmodel import Session, select

from app.db.session import engine
from app.models.source import Source, SourceType
from app.workers.core.proxy_manager import ProxyConfig
from app.workers.core.query import Query
from app.workers.core.utils import load_proxies
from app.workers.scrapers.gov_scraper import GovScraper
from app.workers.scrapers.news_scraper import NewsScraper
from app.workers.scrapers.social_scraper import SocialScraper

# -----------------------------
# USER CONFIGURATION
# -----------------------------

QUERIES = [
    # Query(text="Hegseth AND DOW Spending"),
    # Query(text="AFA"),
    # Query(text="DOW AI"),
    # Query(text="Drone CCA")
    Query(text="Artificial Intelligence")
]

# Pull proxies from Database
PROXIES: List[ProxyConfig] = load_proxies(source="db")

USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# -----------------------------
# Runner
# -----------------------------

async def run_scraper() -> None:
    # 1. Fetch all enabled sources from the database
    with Session(engine) as session:
        statement = select(Source).where(Source.is_enabled)
        all_sources = session.exec(statement).all()

    if not all_sources:
        print("No enabled sources found in database. Did you run the init script?")
        return

    # 2. Map SourceTypes to the correct Scraper Classes
    scraper_mapping: Dict[SourceType, Type] = {
        SourceType.NEWS: NewsScraper,
        SourceType.SOCIAL: SocialScraper,
        SourceType.OFFICIAL: GovScraper
    }

    # 3. Group sources by their type so we can run them in batches
    sources_by_type: Dict[SourceType, List[Source]] = {}
    for src in all_sources:
        sources_by_type.setdefault(src.source_type, []).append(src)

    all_results: List[Any] = []
    start_time = datetime.now()

    # 4. Iterate through each scraper type
    for s_type, sources in sources_by_type.items():
        scraper_cls = scraper_mapping.get(s_type)
        if not scraper_cls:
            continue

        scraper = scraper_cls(proxies=PROXIES, user_agent=USER_AGENT)
        scraper_name = scraper.__class__.__name__
        source_names = [s.name for s in sources]
        print(f"\n=== Running scraper: {scraper_name} for sources: {source_names} ===")

        for i, query in enumerate(QUERIES, start=1):
            print(f"[{i}/{len(QUERIES)}] Query: {query.text}")
            
            # Setup is handled inside .run() in our ParentScraper, 
            # but we need the proxy info for the language/region args
            await scraper.setup()
            
            try:
                proxy = scraper.get_curr_proxy()
                if not proxy:
                    print("Skipping: No proxy available.")
                    continue

                results = await scraper.run(
                    query, 
                    proxy["language"], 
                    proxy["region"], 
                    sources
                )
                all_results.extend(results or [])

            except Exception as e:
                print(f"Query failed: {query.text}")
                print(e)
                traceback.print_exc()
            finally:
                # Ensure the browser closes after each query/scraper set
                await scraper.close()

    elapsed = datetime.now() - start_time

    print("\n" + "="*25)
    print("===== SUMMARY =====")
    print(f"Total results: {len(all_results)}")
    print(f"Elapsed time: {elapsed}")
    print("="*25 + "\n")


if __name__ == "__main__":
    asyncio.run(run_scraper())