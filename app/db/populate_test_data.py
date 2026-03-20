import json
import logging
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.db.session import engine
from app.models import Article, Search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        test_query = "Artificial Intelligence"
        statement = select(Search).where(Search.query_text == test_query)
        search_record = session.exec(statement).first()

        if not search_record:
            logger.info(f"Creating new Search record for: {test_query}")
            search_record = Search(
                query_text=test_query, request_limit=20, all_sources_requested=True
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


if __name__ == "__main__":
    populate_test_articles()
