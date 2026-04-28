from datetime import datetime
from typing import Optional, Any
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Float, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import sys

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


class Base(DeclarativeBase):
    pass


JsonList = Annotated[list[Any], "json"]
JsonDict = Annotated[dict[str, Any], "json"]


class TaxDecision(Base):
    __tablename__ = "tax_decisions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    project_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    activity_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    legal_version_timestamp: Mapped[str] = mapped_column(String(30), nullable=False)
    
    legal_basis: Mapped[JsonList] = mapped_column(JSONB, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    risks: Mapped[JsonList] = mapped_column(JSONB, default=list)
    assumptions: Mapped[JsonList] = mapped_column(JSONB, default=list)
    required_followup: Mapped[JsonList] = mapped_column(JSONB, default=list)
    
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="rule_engine")
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    extra_metadata: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("ix_tax_decisions_created_decision", "created_at", "decision"),
        Index("ix_tax_decisions_entity_type", "entity_type"),
        Index("ix_tax_decisions_project_type", "project_type"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    user: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    details: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    __table_args__ = (
        Index("ix_audit_logs_timestamp_action", "timestamp", "action"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )
