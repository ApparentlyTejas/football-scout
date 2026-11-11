import datetime
from typing import Optional

from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    date_of_birth: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    primary_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    market_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    contract_expiry: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
