from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def test_get_db_yields_working_session(monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", "sqlite:///:memory:")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def get_db() -> Generator[Session, None, None]:
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    db_generator = get_db()
    db = next(db_generator)

    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1

    db_generator.close()
