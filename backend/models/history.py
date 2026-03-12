from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class History(Base):
    __tablename__ = "history"
    __table_args__ = (
        Index("idx_history_user_viewtime", "user_id", "view_time"),
        Index("fk_history_news_idx", "news_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news.id"), nullable=False)
    view_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
