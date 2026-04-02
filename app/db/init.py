import logging

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, select

from app.db.session import engine
from app.models import ExtractionMethod, Source, SourceType
from app.models.proxy import Proxy
from app.workers.core.utils import load_proxies

# Logging to see init progress in docker logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Creates tables based on models and seeds initial data.
    """
    logger.info("Verifying database schema...")
    # This command creates any tables that don't already exist in the DB
    SQLModel.metadata.create_all(engine)

    logger.info("Checking for initial seed data...")
    seed_sources()
    seed_proxies()


def seed_sources() -> None:
    """
    Ensures the 'Source' table has the necessary entries for the scrapers.
    """
    with Session(engine) as session:
        initial_sources = [
            Source(
                id=1,
                name="Reddit",
                source_type=SourceType.SOCIAL,
                extraction_method=ExtractionMethod.RSS,
                base_url="https://www.reddit.com/search.rss?",
                is_enabled=True,
            ),
            Source(
                id=2,
                name="Google News",
                source_type=SourceType.NEWS,
                extraction_method=ExtractionMethod.RSS,
                base_url="https://news.google.com/rss/search?",
                is_enabled=True,
            ),
            Source(
                id=3,
                name="USA.gov",
                source_type=SourceType.OFFICIAL,
                extraction_method=ExtractionMethod.STATIC_HTML,
                base_url="https://search.usa.gov/search?affiliate=aflink_all&query=",
                is_enabled=True,
            ),
            Source(
                id=4,
                name="Bluesky",
                source_type=SourceType.SOCIAL,
                extraction_method=ExtractionMethod.JSON_API,
                base_url="https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?",
                is_enabled=True,
            ),
        ]

        for source_data in initial_sources:
            statement = select(Source).where(Source.name == source_data.name)
            existing = session.exec(statement).first()

            if not existing:
                logger.info(f"Seeding source: {source_data.name}")
                session.add(source_data)
            else:
                # Update existing source in case extraction_method or base_url changed
                existing.extraction_method = source_data.extraction_method
                existing.base_url = source_data.base_url
                session.add(existing)

        session.commit()


def seed_proxies() -> None:
    """
    Seeds the 'Proxy' table using proxies loaded from environment via utils.
    Checks uniqueness based on both server and username.
    """
    try:
        proxies_config = load_proxies(source="env")
    except ValueError as e:
        logger.error(f"Failed to seed proxies: {e}")
        return

    if not proxies_config:
        logger.warning(
            "No proxies found to seed. Check PROXIES_JSON environment variable."
        )
        return

    with Session(engine) as session:
        for p in proxies_config:
            server_addr = p.get("server")
            username = p.get("username")

            if not server_addr:
                continue

            # Check for existing proxy using both server and username
            statement = select(Proxy).where(
                Proxy.server == server_addr,
                Proxy.username == username
            )
            existing = session.exec(statement).first()

            if not existing:
                logger.info(f"Seeding proxy: {server_addr} (User: {username})")
                new_proxy = Proxy(
                    server=server_addr,
                    username=username,
                    password=p.get("password"),
                    region=p.get("region") or "Unknown",
                    language=p.get("language") or "en-US",
                    is_active=True
                )
                session.add(new_proxy)

        session.commit()
        logger.info("Proxy seeding complete.")


if __name__ == "__main__":
    init_db()
