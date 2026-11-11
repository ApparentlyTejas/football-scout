from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint(
            "competition_id", "statsbomb_season_id", name="uq_season_competition_statsbomb"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitions.id"), nullable=False
    )
    statsbomb_season_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
