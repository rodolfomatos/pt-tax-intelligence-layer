"""
GMIF Classifier - Graphical Meta-Information Framework

Based on epistemic-memory-architecture's GMIF system.
Categorizes decisions by epistemic confidence level.
"""

import logging
from typing import Optional, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class GMIFType(str, Enum):
    """GMIF classification types."""
    M1_PRIMARY_EVIDENCE = "M1"  # High confidence, multiple sources
    M2_CONTEXTUAL_CONDITION = "M2"  # With assumptions
    M3_PARTIAL_DESCRIPTION = "M3"  # Unclassified
    M4_DOUBTFUL_TESTIMONY = "M4"  # Contradictions detected
    M5_INTERPRETATION = "M5"  # Clear basis, no contestation
    M6_DERIVED_EVIDENCE = "M6"  # Derived from alignment
    M7_SYNTHESIS = "M7"  # Final decision


class GMIFClassifier:
    """
    Classifies tax decisions by epistemic confidence level.
    
    Categories:
    - M1: Primary Evidence - multiple legal sources, no contradictions
    - M2: Contextual Condition - with assumptions needing validation
    - M3: Partial Description - unclassified
    - M4: Doubtful Testimony - contradictory legal sources
    - M5: Interpretation - clear legal basis, no contestation
    - M6: Derived Evidence - derived from alignment
    - M7: Synthesis - final aggregated decision
    """
    
    def classify(
        self,
        decision: str,
        confidence: float,
        legal_basis: List[Dict],
        risks: List[str],
        assumptions: List[str],
        contradictions: Optional[List[Dict]] = None,
    ) -> GMIFType:
        """
        Classify a decision by GMIF type.
        
        Args:
            decision: The decision type (deductible, non_deductible, etc.)
            confidence: Confidence score (0.0-1.0)
            legal_basis: List of legal citations
            risks: Identified risks
            assumptions: Assumptions made
            contradictions: List of detected contradictions
            
        Returns:
            GMIF type classification
        """
        contradictions = contradictions or []
        
        # M4: Contradictions detected in legal sources
        if contradictions:
            logger.info(f"Decision {decision} classified as M4 - contradictions detected")
            return GMIFType.M4_DOUBTFUL_TESTIMONY
        
        # M7: Final/aggregated decision
        if decision in ("final", "aggregated"):
            return GMIFType.M7_SYNTHESIS
        
        # M1: High confidence, multiple legal sources, no risks
        if (confidence >= 0.8 and 
            len(legal_basis) >= 2 and 
            not risks and
            not assumptions):
            return GMIFType.M1_PRIMARY_EVIDENCE
        
        # M5: Clear legal basis, no contestation, no contradictions
        if (len(legal_basis) >= 1 and 
            confidence >= 0.7 and
            not risks):
            return GMIFType.M5_INTERPRETATION
        
        # M2: With assumptions needing validation
        if assumptions and confidence >= 0.5:
            return GMIFType.M2_CONTEXTUAL_CONDITION
        
        # M6: Derived evidence - when decision is based on alignment
        if "alignment" in risks or "derived" in str(assumptions).lower():
            return GMIFType.M6_DERIVED_EVIDENCE
        
        # M3: Default - unclassified
        return GMIFType.M3_PARTIAL_DESCRIPTION
    
    def get_color(self, gmif_type: GMIFType) -> str:
        """Get color for GMIF type (for visualization)."""
        color_map = {
            GMIFType.M1_PRIMARY_EVIDENCE: "#4CAF50",  # green
            GMIFType.M2_CONTEXTUAL_CONDITION: "#FFC107",  # yellow
            GMIFType.M3_PARTIAL_DESCRIPTION: "#FF9800",  # orange
            GMIFType.M4_DOUBTFUL_TESTIMONY: "#F44336",  # red
            GMIFType.M5_INTERPRETATION: "#8BC34A",  # light green
            GMIFType.M6_DERIVED_EVIDENCE: "#03A9F4",  # light blue
            GMIFType.M7_SYNTHESIS: "#9C27B0",  # purple
        }
        return color_map.get(gmif_type, "#9E9E9E")
    
    def get_description(self, gmif_type: GMIFType) -> str:
        """Get human-readable description."""
        desc_map = {
            GMIFType.M1_PRIMARY_EVIDENCE: "Multiple legal sources, high confidence, no risks",
            GMIFType.M2_CONTEXTUAL_CONDITION: "With assumptions that need validation",
            GMIFType.M3_PARTIAL_DESCRIPTION: "Classification pending or undetermined",
            GMIFType.M4_DOUBTFUL_TESTIMONY: "Contradictory legal sources detected",
            GMIFType.M5_INTERPRETATION: "Clear legal basis, no contestation",
            GMIFType.M6_DERIVED_EVIDENCE: "Derived from alignment or inference",
            GMIFType.M7_SYNTHESIS: "Final aggregated decision",
        }
        return desc_map.get(gmif_type, "Unknown")
    
    def is_high_risk(self, gmif_type: GMIFType) -> bool:
        """Check if GMIF type indicates high risk."""
        return gmif_type in (GMIFType.M4_DOUBTFUL_TESTIMONY, GMIFType.M3_PARTIAL_DESCRIPTION)
    
    def requires_followup(self, gmif_type: GMIFType) -> bool:
        """Check if GMIF type requires follow-up."""
        return gmif_type in (
            GMIFType.M2_CONTEXTUAL_CONDITION,
            GMIFType.M3_PARTIAL_DESCRIPTION,
            GMIFType.M4_DOUBTFUL_TESTIMONY,
        )


# Singleton instance
_classifier: Optional[GMIFClassifier] = None


def get_gmif_classifier() -> GMIFClassifier:
    global _classifier
    if _classifier is None:
        _classifier = GMIFClassifier()
    return _classifier