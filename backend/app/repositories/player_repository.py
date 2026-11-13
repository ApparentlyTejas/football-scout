from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.player_external_id import PlayerExternalId

STATSBOMB_SOURCE = "statsbomb"


def get_or_create_player(
    session: Session,
    statsbomb_player_id: int,
    name: str,
    nationality: str | None,
) -> Player:
    """Look up a Player through its `PlayerExternalId(source="statsbomb",
    external_id=str(statsbomb_player_id))` row, updating the matched
    Player's fields in place if found, or creating both the Player and its
    external-id row together if missing."""
    external_id_value = str(statsbomb_player_id)

    external_id = session.execute(
        select(PlayerExternalId).where(
            PlayerExternalId.source == STATSBOMB_SOURCE,
            PlayerExternalId.external_id == external_id_value,
        )
    ).scalar_one_or_none()

    if external_id is None:
        player = Player(name=name, nationality=nationality)
        session.add(player)
        session.flush()

        session.add(
            PlayerExternalId(
                player_id=player.id,
                source=STATSBOMB_SOURCE,
                external_id=external_id_value,
            )
        )
        session.flush()
        return player

    player = session.get(Player, external_id.player_id)
    assert player is not None
    player.name = name
    player.nationality = nationality
    session.flush()
    return player


def list_players(session: Session, limit: int, offset: int) -> list[Player]:
    """Return a page of players ordered by id, for pagination via
    `limit`/`offset`."""
    return list(
        session.execute(
            select(Player).order_by(Player.id).limit(limit).offset(offset)
        ).scalars()
    )


def get_player(session: Session, player_id: int) -> Player | None:
    """Look up a single Player by primary key, or None if missing."""
    return session.get(Player, player_id)
