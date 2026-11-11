from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlayerMatchStat(Base):
    __tablename__ = "player_match_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "match_id", name="uq_player_match_stat_player_match"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    minutes_played: Mapped[int] = mapped_column(Integer, nullable=False)
    passes_attempted: Mapped[int] = mapped_column(Integer, nullable=False)
    passes_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    shots: Mapped[int] = mapped_column(Integer, nullable=False)
    carries: Mapped[int] = mapped_column(Integer, nullable=False)
    pressures: Mapped[int] = mapped_column(Integer, nullable=False)
    interceptions: Mapped[int] = mapped_column(Integer, nullable=False)
    ball_recoveries: Mapped[int] = mapped_column(Integer, nullable=False)
    dribbles: Mapped[int] = mapped_column(Integer, nullable=False)
    duels: Mapped[int] = mapped_column(Integer, nullable=False)
    aerial_duels: Mapped[int] = mapped_column(Integer, nullable=False)
    dispossessed: Mapped[int] = mapped_column(Integer, nullable=False)
    miscontrols: Mapped[int] = mapped_column(Integer, nullable=False)
