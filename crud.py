"""Create / read / delete operations for analysis records."""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import Analysis

VALID_FILE_TYPES = ("image", "video", "overall")
VALID_RISK_LEVELS = ("Low", "Medium", "High")


def create_analysis(
    db: Session,
    *,
    file_type: str,
    file_name: str,
    result_label: str,
    risk_score: float,
    risk_level: str,
    confidence: Optional[float] = None,
    explanation: str = "",
    details: Optional[dict] = None,
) -> Analysis:
    if file_type not in VALID_FILE_TYPES:
        raise ValueError(f"file_type must be one of {VALID_FILE_TYPES}")
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(f"risk_level must be one of {VALID_RISK_LEVELS}")
    if not 0 <= risk_score <= 100:
        raise ValueError("risk_score must be between 0 and 100")
    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    record = Analysis(
        file_type=file_type,
        file_name=file_name[:255],
        result_label=result_label,
        risk_score=float(risk_score),
        risk_level=risk_level,
        confidence=confidence,
        explanation=explanation,
        details_json=json.dumps(details or {}, default=str),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_analysis(db: Session, analysis_id: str) -> Optional[Analysis]:
    return db.get(Analysis, analysis_id)


def list_analyses(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    file_type: Optional[str] = None,
) -> list[Analysis]:
    stmt = select(Analysis).order_by(Analysis.created_at.desc())
    if file_type:
        stmt = stmt.where(Analysis.file_type == file_type)
    stmt = stmt.limit(max(1, min(limit, 500))).offset(max(0, offset))
    return list(db.scalars(stmt))


def count_analyses(db: Session, file_type: Optional[str] = None) -> int:
    stmt = select(func.count()).select_from(Analysis)
    if file_type:
        stmt = stmt.where(Analysis.file_type == file_type)
    return db.scalar(stmt) or 0


def delete_analysis(db: Session, analysis_id: str) -> bool:
    record = db.get(Analysis, analysis_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True
