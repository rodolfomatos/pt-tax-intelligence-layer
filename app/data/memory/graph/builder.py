"""
Knowledge Graph Builder

Builds graph from tax decisions with GMIF classification.
"""

import logging
from typing import Optional, List, Dict
from uuid import uuid4
from sqlalchemy import select, func
from app.data.memory.graph.models import GraphNode, GraphEdge
from app.data.memory.graph.gmif import get_gmif_classifier
from app.database.session import get_db_session

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """
    Builds and maintains the knowledge graph.
    
    Creates nodes and edges from tax decisions with GMIF classification.
    """
    
    def __init__(self):
        self.classifier = get_gmif_classifier()
    
    async def add_decision(
        self,
        decision_id: str,
        description: str,
        decision_type: str,
        confidence: float,
        legal_basis: List[Dict],
        entity_type: str,
        project_type: str,
        risks: List[str],
        assumptions: List[str],
    ) -> str:
        """
        Add a decision to the knowledge graph.
        
        Returns:
            GMIF classification type
        """
        contradictions = await self._check_contradictions(legal_basis)
        
        # Classify by GMIF
        gmif_type = self.classifier.classify(
            decision=decision_type,
            confidence=confidence,
            legal_basis=legal_basis,
            risks=risks,
            assumptions=assumptions,
            contradictions=contradictions,
        )
        
        async with get_db_session() as session:
            # Create decision node
            node = GraphNode(
                id=uuid4(),
                node_type="decision",
                label=f"{decision_type}: {description[:100]}",
                properties={
                    "decision_id": decision_id,
                    "decision_type": decision_type,
                    "description": description,
                    "confidence": confidence,
                    "risks": risks,
                    "assumptions": assumptions,
                    "entity_type": entity_type,
                    "project_type": project_type,
                },
                gmif_type=gmif_type.value,
                external_id=decision_id,
            )
            session.add(node)
            await session.flush()
            decision_node_id = node.id
            
            # Create legal basis nodes and edges
            for lb in legal_basis:
                legal_node = await self._get_or_create_legal_node(session, lb)
                
                edge = GraphEdge(
                    id=uuid4(),
                    source_id=decision_node_id,
                    target_id=legal_node.id,
                    relation_type="based_on",
                    confidence=1.0,
                    evidence_type="EXTRACTED",
                )
                session.add(edge)
            
            # Create entity node and edge
            entity_node = await self._get_or_create_entity_node(session, entity_type, project_type)
            
            edge = GraphEdge(
                id=uuid4(),
                source_id=entity_node.id,
                target_id=decision_node_id,
                relation_type="requested",
                confidence=1.0,
                evidence_type="EXTRACTED",
            )
            session.add(edge)
        
        logger.info(f"Added decision to graph with GMIF: {gmif_type.value}")
        return gmif_type.value
    
    async def _get_or_create_legal_node(self, session, legal_citation: Dict) -> GraphNode:
        """Get or create a legal basis node."""
        from sqlalchemy import select
        
        code = legal_citation.get("code", "")
        article = legal_citation.get("article", "")
        
        result = await session.execute(
            select(GraphNode).where(
                GraphNode.node_type == "legal_basis",
                GraphNode.external_id == f"{code}:{article}"
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
        
        node = GraphNode(
            id=uuid4(),
            node_type="legal_basis",
            label=f"{code} - {article}",
            properties={
                "code": code,
                "article": article,
                "excerpt": legal_citation.get("excerpt", ""),
            },
            external_id=f"{code}:{article}",
        )
        session.add(node)
        await session.flush()
        return node
    
    async def _get_or_create_entity_node(self, session, entity_type: str, project_type: str) -> GraphNode:
        """Get or create an entity node."""
        from sqlalchemy import select
        
        entity_key = f"{entity_type}:{project_type}"
        
        result = await session.execute(
            select(GraphNode).where(
                GraphNode.node_type == "entity",
                GraphNode.external_id == entity_key
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
        
        node = GraphNode(
            id=uuid4(),
            node_type="entity",
            label=f"{entity_type} ({project_type})",
            properties={
                "entity_type": entity_type,
                "project_type": project_type,
            },
            external_id=entity_key,
        )
        session.add(node)
        await session.flush()
        return node
    
    async def _check_contradictions(self, legal_basis: List[Dict]) -> List[Dict]:
        """Check for contradictions in legal basis."""
        # Simple check - in production, use more sophisticated logic
        contradictions = []
        
        codes = [lb.get("code") for lb in legal_basis]
        
        # Example: CIVA and CIRS contradictory interpretation
        if "CIVA" in codes and len(codes) > 1:
            # This is a simplified check
            pass
        
        return contradictions
    
    async def add_similarity_edge(
        self,
        decision_id_a: str,
        decision_id_b: str,
        similarity_score: float,
    ):
        """Add a similarity edge between two decisions."""
        async with get_db_session() as session:
            from sqlalchemy import select
            
            result_a = await session.execute(
                select(GraphNode).where(
                    GraphNode.node_type == "decision",
                    GraphNode.external_id == decision_id_a
                )
            )
            node_a = result_a.scalar_one_or_none()
            
            result_b = await session.execute(
                select(GraphNode).where(
                    GraphNode.node_type == "decision",
                    GraphNode.external_id == decision_id_b
                )
            )
            node_b = result_b.scalar_one_or_none()
            
            if node_a and node_b:
                edge = GraphEdge(
                    id=uuid4(),
                    source_id=node_a.id,
                    target_id=node_b.id,
                    relation_type="similar_to",
                    confidence=similarity_score,
                    evidence_type="INFERRED",
                )
                session.add(edge)
                logger.info(f"Added similarity edge between {decision_id_a} and {decision_id_b}")

    async def get_stats(self) -> dict:
        """Get knowledge graph statistics."""
        async with get_db_session() as session:
            total_nodes = await session.scalar(select(func.count(GraphNode.id))) or 0
            total_edges = await session.scalar(select(func.count(GraphEdge.id))) or 0

            # GMIF distribution for decision nodes
            gmif_dist_result = await session.execute(
                select(GraphNode.gmif_type, func.count(GraphNode.id))
                .where(GraphNode.node_type == "decision")
                .group_by(GraphNode.gmif_type)
            )
            gmif_dist = {row[0]: row[1] for row in gmif_dist_result.all()}

            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "gmif_distribution": gmif_dist,
            }

    async def get_gmif_summary(self) -> dict:
        """Get GMIF classification summary (same as get_stats for now)."""
        return await self.get_stats()

    async def get_decisions_by_gmif(self, gmif_type: str, limit: int = 100) -> List[Dict]:
        """Get decisions by GMIF classification type."""
        async with get_db_session() as session:
            result = await session.execute(
                select(GraphNode)
                .where(
                    GraphNode.node_type == "decision",
                    GraphNode.gmif_type == gmif_type
                )
                .limit(limit)
            )
            nodes = result.scalars().all()
            return [
                {
                    "id": str(node.id),
                    "label": node.label,
                    "gmif_type": node.gmif_type,
                    "properties": node.properties,
                }
                for node in nodes
            ]

    async def find_contradictions(self, decision_id: Optional[str] = None) -> List[Dict]:
        """Find contradictory decisions (currently stub)."""
        # TODO: Implement contradiction detection logic
        return []


# Singleton
_builder: Optional[KnowledgeGraphBuilder] = None


def get_graph_builder() -> KnowledgeGraphBuilder:
    global _builder
    if _builder is None:
        _builder = KnowledgeGraphBuilder()
    return _builder