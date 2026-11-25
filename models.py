"""Database tables (SQLAlchemy 2.0 style).

Only plain column types are used (String, Float, Text, DateTime), so the same
model works on SQLite today and PostgreSQL later without changes.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    # stored as UTC, without tzinfo, so SQLite and PostgreSQL behave the same
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    file_type: Mapped[str] = mapped_column(String(16), index=True)   # image | video | overall
    file_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    result_label: Mapped[str] = mapped_column(String(64))            # e.g. "Likely manipulated"
    risk_score: Mapped[float] = mapped_column(Float)                 # 0 - 100
    risk_level: Mapped[str] = mapped_column(String(16))              # Low | Medium | High
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0 - 1
    explanation: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")    # evidence, per-model scores

    @property
    def details(self) -> dict:
        try:
            return json.loads(self.details_json or "{}")
        except json.JSONDecodeError:
            return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_type": self.file_type,
            "file_name": self.file_name,
            "created_at": self.created_at.isoformat() + "Z",
            "result_label": self.result_label,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "details": self.details,
        }
