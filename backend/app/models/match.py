import datetime

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    statsbomb_match_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("seasons.id"), nullable=False
    )
    home_team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    away_team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    match_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
