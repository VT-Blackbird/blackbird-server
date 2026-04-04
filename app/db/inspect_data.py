from typing import Any, List, Type

from sqlmodel import Session, SQLModel, select

from app.db.session import engine
from app.models import Article, Proxy, ProxyLog, Search, SearchSource, Source


def inspect_tables() -> None:
    """
    Connects to the database and prints the first 5 entries of every table.
    """

    models: List[Type[SQLModel]] = [
        Search,
        Source,
        Article,
        Proxy,
        ProxyLog,
        SearchSource,
    ]

    with Session(engine) as session:
        print("\n" + "=" * 50)
        print("DATABASE INSPECTION: FIRST 5 ENTRIES PER TABLE")
        print("=" * 50 + "\n")

        for model in models:
            table_name = (
                model.__tablename__
                if hasattr(model, "__tablename__")
                else model.__name__.lower()
            )
            print(f"--- TABLE: {table_name} ---")

            statement: Any = select(model).limit(5)
            results = session.exec(statement).all()

            if not results:
                print("[No entries found]")
            else:
                for idx, row in enumerate(results, start=1):
                    row_dict = row.model_dump()

                    if "content" in row_dict and row_dict["content"]:
                        if len(str(row_dict["content"])) > 50:
                            row_dict["content"] = str(row_dict["content"])[:47] + "..."

                    print(f" {idx}. {row_dict}")

            print("-" * 30 + "\n")


if __name__ == "__main__":
    try:
        inspect_tables()
    except Exception as e:
        print(f"Error connecting to database: {e}")
