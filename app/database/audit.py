import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import TaxDecision, AuditLog
from app.database.session import get_db_session
from app.models import TaxAnalysisInput, TaxAnalysisOutput

logger = logging.getLogger(__name__)


class AuditRepository:
    """Repository for audit logging."""
    
    async def log_decision(
        self,
        input_data: TaxAnalysisInput,
        output_data: TaxAnalysisOutput,
        source: str = "rule_engine",
        processing_time_ms: Optional[int] = None,
    ) -> TaxDecision:
        """Log a tax decision to the database."""
        
        async with get_db_session() as session:
            decision = TaxDecision(
                id=uuid4(),
                created_at=datetime.utcnow(),
                operation_type=input_data.operation_type,
                description=input_data.description,
                amount=input_data.amount,
                currency=input_data.currency,
                entity_type=input_data.entity_type,
                project_type=input_data.context.project_type,
                activity_type=input_data.context.activity_type,
                location=input_data.context.location,
                decision=output_data.decision,
                confidence=output_data.confidence,
                risk_level=output_data.risk_level,
                legal_version_timestamp=output_data.legal_version_timestamp,
                legal_basis=[lb.model_dump() for lb in output_data.legal_basis],
                explanation=output_data.explanation,
                risks=output_data.risks,
                assumptions=output_data.assumptions,
                required_followup=output_data.required_followup,
                source=source,
                processing_time_ms=processing_time_ms,
                extra_metadata=input_data.metadata,
            )
            session.add(decision)
            await session.flush()
            
            logger.info(f"Logged decision: {decision.id} - {output_data.decision}")
            return decision
    
    async def log_action(
        self,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log an audit action."""
        
        async with get_db_session() as session:
            log_entry = AuditLog(
                id=uuid4(),
                timestamp=datetime.utcnow(),
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user=user,
                request_id=request_id,
                details=details or {},
                ip_address=ip_address,
            )
            session.add(log_entry)
            await session.flush()
            return log_entry
    
    async def get_decisions(
        self,
        limit: int = 100,
        offset: int = 0,
        decision_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[TaxDecision]:
        """Get decisions with filters."""
        
        async with get_db_session() as session:
            query = select(TaxDecision).order_by(desc(TaxDecision.created_at))
            
            if decision_type:
                query = query.where(TaxDecision.decision == decision_type)
            if entity_type:
                query = query.where(TaxDecision.entity_type == entity_type)
            if start_date:
                query = query.where(TaxDecision.created_at >= start_date)
            if end_date:
                query = query.where(TaxDecision.created_at <= end_date)
            
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_decisions_count(
        self,
        decision_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get total count of decisions matching filters."""
        
        async with get_db_session() as session:
            from sqlalchemy import func
            query = select(func.count(TaxDecision.id))
            
            if decision_type:
                query = query.where(TaxDecision.decision == decision_type)
            if entity_type:
                query = query.where(TaxDecision.entity_type == entity_type)
            if start_date:
                query = query.where(TaxDecision.created_at >= start_date)
            if end_date:
                query = query.where(TaxDecision.created_at <= end_date)
            
            result = await session.execute(query)
            return result.scalar() or 0
    
    async def get_decision_by_id(self, decision_id: str) -> Optional[TaxDecision]:
        """Get a specific decision by ID."""
        
        async with get_db_session() as session:
            query = select(TaxDecision).where(TaxDecision.id == decision_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def get_statistics(self) -> dict:
        """Get decision statistics."""
        
        async with get_db_session() as session:
            from sqlalchemy import func, case
            
            query = select(
                func.count(TaxDecision.id).label("total"),
                func.sum(case((TaxDecision.decision == "deductible", 1), else_=0)).label("deductible"),
                func.sum(case((TaxDecision.decision == "non_deductible", 1), else_=0)).label("non_deductible"),
                func.sum(case((TaxDecision.decision == "partially_deductible", 1), else_=0)).label("partially_deductible"),
                func.sum(case((TaxDecision.decision == "uncertain", 1), else_=0)).label("uncertain"),
                func.avg(TaxDecision.confidence).label("avg_confidence"),
            )
            result = await session.execute(query)
            row = result.one()
            
            return {
                "total": row.total or 0,
                "by_decision": {
                    "deductible": row.deductible or 0,
                    "non_deductible": row.non_deductible or 0,
                    "partially_deductible": row.partially_deductible or 0,
                    "uncertain": row.uncertain or 0,
                },
                "avg_confidence": float(row.avg_confidence or 0),
            }


_audit_repo: Optional[AuditRepository] = None


def get_audit_repository() -> AuditRepository:
    global _audit_repo
    if _audit_repo is None:
        _audit_repo = AuditRepository()
    return _audit_repo
