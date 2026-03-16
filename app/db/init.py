import logging

from sqlmodel import Session, select

from app.db.session import engine

# Importing app.models ensures all classes are registered with SQLModel.metadata
from app.models import Source, SQLModel

# Setup logging to see init progress in docker logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    """
    Creates tables based on models and seeds initial data.
    """
    logger.info("Verifying database schema...")
    # This looks at the metadata collected from app.models.__init__
    SQLModel.metadata.create_all(engine)

    logger.info("Checking for initial seed data...")
    seed_sources()


def seed_sources():
    """
    Ensures the 'Source' table has the necessary entries for the scrapers.
    """
    with Session(engine) as session:
        # Define the baseline sources required for Pass 1
        initial_sources = [
            Source(
                id=1,
                name="Reddit",
                source_type="Social",
                extraction_method="RSS",
                base_url="https://www.reddit.com/search.rss?",
                is_enabled=True,
            ),
            Source(
                id=2,
                name="Google News",
                source_type="News",
                extraction_method="RSS",
                base_url="https://news.google.com/rss/search?",
                is_enabled=True,
            ),
        ]

        for source_data in initial_sources:
            # Check by name to avoid duplicates if ID sequences reset
            statement = select(Source).where(Source.name == source_data.name)
            existing = session.exec(statement).first()

            if not existing:
                logger.info(f"Seeding source: {source_data.name}")
                session.add(source_data)

        session.commit()


if __name__ == "__main__":
    init_db()
