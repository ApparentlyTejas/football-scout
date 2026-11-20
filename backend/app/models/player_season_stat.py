from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlayerSeasonStat(Base):
    __tablename__ = "player_season_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "season_id", name="uq_player_season_stat_player_season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    position_group: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False)
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
    pass_completion_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    passes_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shots_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carries_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pressures_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    interceptions_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ball_recoveries_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dribbles_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duels_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aerial_duels_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dispossessed_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    miscontrols_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_completion_pct_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    passes_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shots_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carries_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pressures_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    interceptions_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ball_recoveries_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dribbles_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duels_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aerial_duels_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dispossessed_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    miscontrols_per_90_percentile: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
