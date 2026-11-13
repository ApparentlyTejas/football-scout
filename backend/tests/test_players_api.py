from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.main import app
from app.models.base import Base
from app.models.player import Player


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_players_paginates(client: TestClient, session: Session) -> None:
    session.add_all(
        [
            Player(name="Lionel Messi", nationality="Argentina"),
            Player(name="Cristiano Ronaldo", nationality="Portugal"),
            Player(name="Kylian Mbappe", nationality="France"),
        ]
    )
    session.commit()

    response = client.get("/api/v1/players", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get("/api/v1/players", params={"limit": 2, "offset": 2})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_player_by_id_returns_404_for_missing(client: TestClient) -> None:
    response = client.get("/api/v1/players/999999")

    assert response.status_code == 404
    body = response.json()
    assert list(body.keys()) == ["detail"]
    assert isinstance(body["detail"], str)


def test_get_player_by_id_returns_player(client: TestClient, session: Session) -> None:
    player = Player(
        name="Youssef En-Nesyri",
        nationality="Morocco",
        primary_position="Forward",
    )
    session.add(player)
    session.commit()

    response = client.get(f"/api/v1/players/{player.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == player.id
    assert body["name"] == "Youssef En-Nesyri"
    assert body["nationality"] == "Morocco"
    assert body["primary_position"] == "Forward"
