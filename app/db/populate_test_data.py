import argparse
import json
import logging
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.db.session import engine
from app.models import Article, Search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_QUERY = "Artificial Intelligence"


def populate_test_articles(file_path: str = "candidate_test_articles.json") -> None:
    """
    Reads the candidate articles JSON and populates the database for testing.
    """
    try:
        with open(file_path, "r") as f:
            articles_data: List[Dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        logger.error(f"File {file_path} not found. Run the selection script first.")
        return

    with Session(engine) as session:
        statement = select(Search).where(Search.query_text == TEST_QUERY)
        search_record = session.exec(statement).first()

        if not search_record:
            logger.info(f"Creating new Search record for: {TEST_QUERY}")
            search_record = Search(
                query_text=TEST_QUERY, request_limit=20, all_sources_requested=True
            )
            session.add(search_record)
            session.commit()
            session.refresh(search_record)

        logger.info(f"Importing {len(articles_data)} articles...")
        for data in articles_data:
            s_id = data["source_id"]

            article = Article(
                title=data["title"],
                content=data["content"],
                url=data["url"],
                published_at=data["published_at"],
                source_id=s_id,
                search_id=search_record.id,
            )

            # Check for duplicates before adding
            dup_stmt = select(Article).where(Article.url == article.url)
            if not session.exec(dup_stmt).first():
                session.add(article)

        session.commit()
        logger.info("Test data population complete.")


def clear_test_data() -> None:
    """
    Removes the test Search record and relies on cascade to delete linked Articles.
    """
    with Session(engine) as session:
        statement = select(Search).where(Search.query_text == TEST_QUERY)
        search_record = session.exec(statement).first()

        if search_record:
            logger.info(
                f"Removing Search record: '{TEST_QUERY}' and associated articles..."
            )
            session.delete(search_record)
            session.commit()
            logger.info("Cleanup complete.")
        else:
            logger.info(f"No test data found for query: '{TEST_QUERY}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage database test data.")
    parser.add_argument(
        "--clear", action="store_true", help="Clear test data instead of populating."
    )
    args = parser.parse_args()

    if args.clear:
        clear_test_data()
    else:
        populate_test_articles()
