import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.player_external_id import PlayerExternalId
from app.repositories.player_repository import get_or_create_player


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def test_dangling_external_id_raises_explicit_error(session: Session) -> None:
    # SQLite does not enforce the foreign key by default, so an external
    # id pointing at a missing Player can be stored here.
    session.add(PlayerExternalId(player_id=999, source="statsbomb", external_id="6301"))
    session.flush()

    with pytest.raises(LookupError, match="999"):
        get_or_create_player(
            session, statsbomb_player_id=6301, name="Youssef En-Nesyri", nationality=None
        )
