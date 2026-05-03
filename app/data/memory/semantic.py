import logging
import json
import threading
from typing import Optional, List, Dict
from datetime import datetime, timezone
import chromadb
from chromadb.config import Settings
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SemanticMemory:
    """ChromaDB-based semantic memory for decisions."""
    
    def __init__(self, persist_directory: Optional[str] = None):
        persist = persist_directory or settings.chroma_persist_dir or "/data/chroma"
        self._enabled = False
        
        try:
            self.client = chromadb.PersistentClient(
                path=persist,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.client.get_or_create_collection(
                name="tax_decisions",
                metadata={"hnsw:space": "cosine"}
            )
            self._enabled = True
            logger.info(f"Semantic memory initialized at {persist}")
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}. Semantic memory disabled.")
            self.client = None
            self.collection = None
    
    def add_decision(
        self,
        decision_id: str,
        description: str,
        decision: str,
        explanation: str,
        legal_basis: List[Dict],
        metadata: Dict,
    ):
        """Add a decision to semantic memory."""
        if not self._enabled:
            logger.debug("Semantic memory disabled, skipping add")
            return
        
        text = f"{description}. {explanation}"
        
        self.collection.add(
            ids=[decision_id],
            documents=[text],
            metadatas=[{
                "decision": decision,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "legal_basis": json.dumps(legal_basis),
                **metadata
            }]
        )
        logger.info(f"Added decision to semantic memory: {decision_id}")
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_decision: Optional[str] = None,
    ) -> List[Dict]:
        """Search semantic memory for similar decisions."""
        if not self._enabled:
            return []
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"decision": filter_decision} if filter_decision else None,
        )
        
        if not results["ids"] or not results["ids"][0]:
            return []
        
        memories = []
        for i, doc_id in enumerate(results["ids"][0]):
            memories.append({
                "id": doc_id,
                "description": results["documents"][0][i],
                "decision": results["metadatas"][0][i].get("decision"),
                "timestamp": results["metadatas"][0][i].get("timestamp"),
                "distance": results["distances"][0][i] if "distances" in results else 0,
            })
        
        return memories
    
    def delete(self, decision_id: str):
        """Delete a decision from semantic memory."""
        if not self._enabled:
            return
        
        self.collection.delete(ids=[decision_id])
    
    def count(self) -> int:
        """Get total number of memories."""
        if not self._enabled:
            return 0
        
        return self.collection.count()


_memory: Optional[SemanticMemory] = None
_memory_lock = threading.Lock()


def get_semantic_memory() -> SemanticMemory:
    global _memory
    if _memory is None:
        with _memory_lock:
            if _memory is None:  # double-checked locking
                _memory = SemanticMemory()
    return _memory