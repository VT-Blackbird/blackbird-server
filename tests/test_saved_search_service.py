import uuid

import pytest
from sqlmodel import Session

from app.db.session import engine
from app.models.search import Search
from app.models.user import User  # Ensure you import your User model
from app.services.saved_search_service import saved_search_service


@pytest.fixture
def db_session() -> Session:
    with Session(engine) as session:
        yield session


@pytest.fixture
def mock_user(db_session: Session) -> User:
    """Creates a real user in the DB to satisfy Foreign Key constraints."""
    user_id = uuid.uuid4()
    new_user = User(
        id=user_id,
        username=f"user_{user_id.hex[:6]}",
        email=f"test_{user_id.hex[:6]}@example.com",
        hashed_password="not_a_real_hash",  # Added to satisfy NotNullViolation
        is_active=True
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)
    return new_user


@pytest.fixture
def mock_search(db_session: Session) -> Search:
    new_search = Search(
        query_text="Machine Learning Research",
        request_limit=10,
        all_sources_requested=True
    )
    db_session.add(new_search)
    db_session.commit()
    db_session.refresh(new_search)
    return new_search


def test_save_search_flow(db_session: Session, mock_search: Search,
                          mock_user: User) -> None:
    # Use the real ID from our mock_user fixture
    user_id = mock_user.id

    # 1. Test Initial Save
    result = saved_search_service.save(
        db_session,
        user_id=user_id,
        search_id=mock_search.id,
        custom_name="My ML Search"
    )
    assert result is not None
    assert result.custom_name == "My ML Search"

    # 2. Test Duplicate Prevention
    duplicate_result = saved_search_service.save(
        db_session,
        user_id=user_id,
        search_id=mock_search.id
    )
    assert duplicate_result.id == result.id

    # 3. Test Deletion
    deleted = saved_search_service.delete(db_session, user_id, result.id)
    assert deleted is True