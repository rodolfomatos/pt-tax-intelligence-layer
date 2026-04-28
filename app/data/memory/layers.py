"""
Memory Layers - Progressive Disclosure Pattern

Inspired by Claude-Mem:
- L0: Identity (~50 tokens) - sempre carregado
- L1: Critical facts (~120 tokens) - sempre carregado
- L2: Room-specific (on demand) - contexto do projeto
- L3: Deep search (on demand) - busca semântica
"""

import logging
from typing import Optional, List, Dict
from app.data.memory.semantic import get_semantic_memory

logger = logging.getLogger(__name__)


class MemoryLayers:
    """
    4-layer memory stack para otimizar contexto.
    
    L0: Identity - quem é o sistema, core prefs (~50 tokens)
    L1: Critical facts - team, projects, preferences (~120 tokens)  
    L2: Room recall - topic-specific context (on demand)
    L3: Deep semantic search - full retrieval (on demand)
    """
    
    # Layer 0 - Identity (always loaded)
    L0_IDENTITY = """Eres PT Tax Intelligence Layer, un sistema de apoyo a decisiones fiscales.
Función: Analizar operaciones y proporcionar decisiones fiscales estructuradas basadas en legislación portuguesa.
Principio: Si no hay base legal → decisión "uncertain"."""
    
    # Layer 1 - Critical Facts (always loaded)
    L1_CONTEXT = {
        "entity_types": ["university", "researcher", "department", "project"],
        "project_types": ["FCT", "Horizon", "internal", "other"],
        "activity_types": ["taxable", "exempt", "mixed"],
        "locations": ["PT", "EU", "non-EU"],
        "decisions": ["deductible", "non_deductible", "partially_deductible", "uncertain"],
    }
    
    def __init__(self):
        self.semantic = get_semantic_memory()
    
    def get_l0_identity(self) -> str:
        """Retorna L0 - Identity (~50 tokens)."""
        return self.L0_IDENTITY
    
    def get_l1_facts(
        self,
        recent_decisions: Optional[List[Dict]] = None,
        active_project: Optional[str] = None,
    ) -> str:
        """
        Retorna L1 - Critical facts (~120 tokens).
        
        Args:
            recent_decisions: Últimas decisões para contexto
            active_project: Projeto ativo
        """
        facts = []
        
        facts.append("Sistema: Análisis fiscal para Universidade do Porto")
        facts.append("Reglas: CIVA → deducción IVA, CIRC → amortizaciones")
        
        if recent_decisions:
            recent_summary = ", ".join([
                f"{d.get('decision', '?')}" 
                for d in recent_decisions[:3]
            ])
            facts.append(f"Recientes: {recent_summary}")
        
        if active_project:
            facts.append(f"Proyecto activo: {active_project}")
        
        return " | ".join(facts)
    
    def get_l2_room_context(
        self,
        entity_type: str,
        project_type: str,
    ) -> str:
        """
        Retorna L2 - Room-specific context (on demand).
        
        Carrega contexto baseado no tipo de entidade/projeto.
        """
        context_templates = {
            ("researcher", "FCT"): "Investigador FCT → deductible com verificação de elegibilidade",
            ("researcher", "Horizon"): "Investigador Horizon → dedução conforme regras EU",
            ("department", "internal"): "Departamento interno → dedução IVA padrão",
            ("project", "FCT"): "Projeto FCT → elegível com restrictions específicas",
            ("project", "Horizon"): "Projeto Horizon → regras EU aplicam",
        }
        
        key = (entity_type, project_type)
        return context_templates.get(key, "Contexto padrão - verificar regras gerais")
    
    def get_l3_deep_search(
        self,
        query: str,
        n_results: int = 3,
    ) -> List[Dict]:
        """
        Retorna L3 - Deep semantic search (on demand).
        
        Busca semântica em decisões passadas.
        """
        try:
            results = self.semantic.search(query, n_results=n_results)
            return results
        except Exception as e:
            logger.warning(f"Deep search failed: {e}")
            return []
    
    def save_to_memory(
        self,
        decision_id: str,
        description: str,
        decision: str,
        explanation: str,
        legal_basis: List[Dict],
        metadata: Dict,
    ):
        """Salva decisão para memória semantic (L3)."""
        try:
            self.semantic.add_decision(
                decision_id=decision_id,
                description=description,
                decision=decision,
                explanation=explanation,
                legal_basis=legal_basis,
                metadata=metadata,
            )
        except Exception as e:
            logger.warning(f"Failed to save to memory: {e}")
    
    def build_context(
        self,
        layer: str = "L1",
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        project_type: Optional[str] = None,
        recent_decisions: Optional[List[Dict]] = None,
        active_project: Optional[str] = None,
    ) -> str:
        """
        Constrói contexto baseado na layer especificada.
        
        Args:
            layer: L0, L1, L2, ou L3
            query: Para L3 deep search
            entity_type: Para L2
            project_type: Para L2
            recent_decisions: Para L1
            active_project: Para L1
        """
        parts = []
        
        # Always include L0
        parts.append(self.get_l0_identity())
        
        if layer in ("L1", "L2", "L3"):
            parts.append(self.get_l1_facts(recent_decisions, active_project))
        
        if layer in ("L2", "L3") and entity_type and project_type:
            parts.append(self.get_l2_room_context(entity_type, project_type))
        
        # L3 includes deep search results
        if layer == "L3" and query:
            results = self.get_l3_deep_search(query)
            if results:
                results_text = " | ".join([
                    f"[{r['id'][:8]}]: {r['description'][:100]}"
                    for r in results
                ])
                parts.append(f"Similar: {results_text}")
        
        return "\n".join(parts)


_memory_layers: Optional[MemoryLayers] = None


def get_memory_layers() -> MemoryLayers:
    global _memory_layers
    if _memory_layers is None:
        _memory_layers = MemoryLayers()
    return _memory_layers