from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repositories.player_repository import get_player, list_players
from app.schemas.player import PlayerOut

router = APIRouter()


@router.get("", response_model=list[PlayerOut])
def list_players_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[PlayerOut]:
    return list(list_players(db, limit=limit, offset=offset))


@router.get("/{player_id}", response_model=PlayerOut)
def get_player_endpoint(player_id: int, db: Session = Depends(get_db)) -> PlayerOut:
    player = get_player(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player
