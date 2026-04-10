"""
Knowledge Graph Models - Nodes and Edges

Based on GMIF classification system.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Float, JSON, Index, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GraphNode(Base):
    """
    Node in the knowledge graph.
    
    Types:
    - decision: Tax decision
    - legal_basis: Legal article (CIVA, CIRC)
    - entity: Researcher, department, project
    - rule: Applied tax rule
    """
    __tablename__ = "graph_nodes"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Node identification
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)  # decision, legal_basis, entity, rule
    label: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Properties (JSON for flexibility)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # GMIF classification (for decisions)
    gmif_type: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # M1-M7
    
    # Temporal validity
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # External references
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., article code
    
    __table_args__ = (
        Index("ix_graph_nodes_type_label", "node_type", "label"),
        Index("ix_graph_nodes_gmif", "gmif_type"),
        Index("ix_graph_nodes_external_id", "external_id"),
    )


class GraphEdge(Base):
    """
    Edge in the knowledge graph with temporal validity.
    
    Relation types:
    - similar_to: Similar decision
    - based_on: Decision based on legal basis
    - requested: Entity requested decision
    - applied_to: Rule applied to decision
    - contradicts: Legal basis contradiction
    - supports: Support relationship
    - opposes: Opposition relationship
    """
    __tablename__ = "graph_edges"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Edge endpoints
    source_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False)
    target_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False)
    
    # Edge properties
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False)  # similar_to, based_on, etc.
    confidence: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0-1.0
    source_file: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Evidence type (EXTRACTED vs INFERRED)
    evidence_type: Mapped[str] = mapped_column(String(20), default="EXTRACTED")  # EXTRACTED, INFERRED
    
    # Temporal validity
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_graph_edges_source_target", "source_id", "target_id"),
        Index("ix_graph_edges_relation", "relation_type"),
        Index("ix_graph_edges_temporal", "valid_from", "valid_to"),
    )


class Contradiction(Base):
    """
    Detected contradictions between legal bases or decisions.
    """
    __tablename__ = "contradictions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Contradiction parties
    claim_a: Mapped[str] = mapped_column(String(200), nullable=False)
    claim_b: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Context
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high
    
    # Status
    resolved: Mapped[bool] = mapped_column(default=False)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    __table_args__ = (
        Index("ix_contradictions_claims", "claim_a", "claim_b"),
        Index("ix_contradictions_resolved", "resolved"),
    )