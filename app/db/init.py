import logging

from sqlmodel import Session, SQLModel, select  # SQLModel comes from the library

from app.db.session import engine

# Our custom models and enums come from our local package
from app.models import ExtractionMethod, Source, SourceType

# Setup logging to see init progress in docker logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    """
    Creates tables based on models and seeds initial data.
    """
    logger.info("Verifying database schema...")
    # This command creates any tables that don't already exist in the DB
    SQLModel.metadata.create_all(engine)

    logger.info("Checking for initial seed data...")
    seed_sources()


def seed_sources():
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
        ]

        for source_data in initial_sources:
            statement = select(Source).where(Source.name == source_data.name)
            existing = session.exec(statement).first()

            if not existing:
                logger.info(f"Seeding source: {source_data.name}")
                session.add(source_data)

        session.commit()


if __name__ == "__main__":
    init_db()
