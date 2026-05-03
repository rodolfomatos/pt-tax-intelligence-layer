"""
Knowledge Graph Query API

Provides queries for the graph with temporal validity.
"""

import logging
import threading
from typing import Optional, List, Dict
from datetime import datetime, timezone
from sqlalchemy import select, or_
from app.data.memory.graph.models import GraphNode, GraphEdge, Contradiction
from app.database.session import get_db_session
from app.data.memory.graph.gmif import get_gmif_classifier

logger = logging.getLogger(__name__)


class GraphQuery:
    """
    Query API for the knowledge graph.
    """

    def __init__(self):
        self.classifier = get_gmif_classifier()

    async def query_entity(
        self,
        entity_id: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Get a node by ID or external ID."""
        async with get_db_session() as session:
            if entity_id:
                result = await session.execute(
                    select(GraphNode).where(GraphNode.id == entity_id)
                )
            else:
                result = await session.execute(
                    select(GraphNode).where(GraphNode.external_id == external_id)
                )

            node = result.scalar_one_or_none()
            if not node:
                return None

            return self._node_to_dict(node)

    async def query_as_of(
        self,
        node_type: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> List[Dict]:
        """Get nodes that were valid at a specific time."""
        as_of = as_of or datetime.now(timezone.utc)

        async with get_db_session() as session:
            query = select(GraphNode).where(
                GraphNode.valid_from <= as_of,
                or_(GraphNode.valid_to.is_(None), GraphNode.valid_to > as_of),
            )

            if node_type:
                query = query.where(GraphNode.node_type == node_type)

            result = await session.execute(query)
            nodes = result.scalars().all()

            return [self._node_to_dict(n) for n in nodes]

    async def timeline(
        self,
        entity_external_id: str,
    ) -> List[Dict]:
        """Get chronological timeline of an entity's decisions."""
        async with get_db_session() as session:
            # Get entity node
            entity_result = await session.execute(
                select(GraphNode).where(GraphNode.external_id == entity_external_id)
            )
            entity = entity_result.scalar_one_or_none()

            if not entity:
                return []

            # Get edges with target nodes joined (eager load)
            from sqlalchemy.orm import selectinload
            edges_result = await session.execute(
                select(GraphEdge)
                .options(selectinload(GraphEdge.target))
                .where(GraphEdge.source_id == entity.id)
            )
            edges = edges_result.scalars().all()

            timeline = []
            for edge in edges:
                if edge.target:
                    timeline.append(
                        {
                            "node": self._node_to_dict(edge.target),
                            "relation": edge.relation_type,
                            "timestamp": edge.created_at.isoformat(),
                        }
                    )

            # Sort by timestamp descending
            timeline.sort(key=lambda x: x["timestamp"], reverse=True)
            return timeline

    async def find_similar(
        self,
        decision_id: str,
        limit: int = 5,
    ) -> List[Dict]:
        """Find similar decisions to a given one."""
        async with get_db_session() as session:
            # Get the decision node
            decision_result = await session.execute(
                select(GraphNode).where(
                    GraphNode.external_id == decision_id,
                    GraphNode.node_type == "decision",
                )
            )
            decision = decision_result.scalar_one_or_none()

            if not decision:
                return []

            # Find similar decisions via edges
            similar_result = await session.execute(
                select(GraphEdge, GraphNode)
                .join(GraphNode, GraphEdge.target_id == GraphNode.id)
                .where(
                    GraphEdge.source_id == decision.id,
                    GraphEdge.relation_type == "similar_to",
                )
                .limit(limit)
            )

            similar = []
            for edge, node in similar_result:
                similar.append(
                    {
                        "node": self._node_to_dict(node),
                        "confidence": edge.confidence,
                    }
                )

            return similar

    async def find_contradictions(
        self,
        decision_id: Optional[str] = None,
    ) -> List[Dict]:
        """Find contradictions involving a decision or all."""
        async with get_db_session() as session:
            query = select(Contradiction).where(Contradiction.resolved.is_(False))

            if decision_id:
                query = query.where(
                    or_(
                        Contradiction.claim_a.contains(decision_id),
                        Contradiction.claim_b.contains(decision_id),
                    )
                )

            result = await session.execute(query)
            contradictions = result.scalars().all()

            return [
                {
                    "id": str(c.id),
                    "claim_a": c.claim_a,
                    "claim_b": c.claim_b,
                    "context": c.context,
                    "severity": c.severity,
                }
                for c in contradictions
            ]

    async def get_gmif_summary(self) -> Dict:
        """Get summary of decisions by GMIF type."""
        async with get_db_session() as session:
            from sqlalchemy import func

            result = await session.execute(
                select(
                    GraphNode.node_type,
                    GraphNode.gmif_type,
                    func.count(GraphNode.id).label("count"),
                )
                .where(
                    GraphNode.node_type == "decision", GraphNode.gmif_type.is_not(None)
                )
                .group_by(GraphNode.node_type, GraphNode.gmif_type)
            )

            summary = {"by_gmif": {}, "by_type": {}}
            for row in result:
                gmif = row.gmif_type or "unclassified"
                summary["by_gmif"][gmif] = row.count
                summary["by_type"][row.node_type] = row.count

            return summary

    async def get_decisions_by_gmif(
        self,
        gmif_type: str,
        limit: int = 100,
    ) -> List[Dict]:
        """Get all decisions with a specific GMIF type."""
        async with get_db_session() as session:
            result = await session.execute(
                select(GraphNode)
                .where(
                    GraphNode.node_type == "decision", GraphNode.gmif_type == gmif_type
                )
                .limit(limit)
            )

            nodes = result.scalars().all()
            return [self._node_to_dict(n) for n in nodes]

    async def get_graph_stats(self) -> Dict:
        """Get overall graph statistics."""
        async with get_db_session() as session:
            from sqlalchemy import func

            # Node counts
            nodes_result = await session.execute(
                select(
                    GraphNode.node_type, func.count(GraphNode.id).label("count")
                ).group_by(GraphNode.node_type)
            )

            node_counts = {row.node_type: row.count for row in nodes_result}

            # Edge counts
            edges_result = await session.execute(
                select(
                    GraphEdge.relation_type, func.count(GraphEdge.id).label("count")
                ).group_by(GraphEdge.relation_type)
            )

            edge_counts = {row.relation_type: row.count for row in edges_result}

            # Contradictions
            contra_result = await session.execute(
                select(func.count(Contradiction.id)).where(
                    Contradiction.resolved.is_(False)
                )
            )
            open_contradictions = contra_result.scalar()

            return {
                "nodes": node_counts,
                "edges": edge_counts,
                "open_contradictions": open_contradictions,
            }

    def _node_to_dict(self, node: GraphNode) -> Dict:
        """Convert node to dictionary."""
        return {
            "id": str(node.id),
            "node_type": node.node_type,
            "label": node.label,
            "properties": node.properties,
            "gmif_type": node.gmif_type,
            "external_id": node.external_id,
            "created_at": node.created_at.isoformat(),
            "valid_from": node.valid_from.isoformat() if node.valid_from else None,
            "valid_to": node.valid_to.isoformat() if node.valid_to else None,
        }


# Singleton
_query: Optional[GraphQuery] = None
_query_lock = threading.Lock()


def get_graph_query() -> GraphQuery:
    global _query
    if _query is None:
        with _query_lock:
            if _query is None:  # double-checked locking
                _query = GraphQuery()
    return _query
