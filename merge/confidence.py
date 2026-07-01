import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

RESUME_BASE_CONFIDENCE = 0.9
CSV_BASE_CONFIDENCE = 0.8
CONFLICT_REDUCTION_FACTOR = 0.75
AGREEMENT_BOOST = 0.05

def get_base_confidence(source: str) -> float:
    """Returns the default base confidence score for a source."""
    if not source:
        return 0.0
    if "resume" in source.lower():
        return RESUME_BASE_CONFIDENCE
    if "csv" in source.lower() or "recruiter" in source.lower():
        return CSV_BASE_CONFIDENCE
    return 0.5  # Fallback for unknown sources

def compute_merged_confidence(val1: Any, val2: Any, source1: str, source2: str, chosen_source: str) -> float:
    """
    Computes confidence score for a field when values are present in multiple sources.
    Boosts confidence if they match; reduces if they conflict.
    """
    conf1 = get_base_confidence(source1)
    conf2 = get_base_confidence(source2)
    
    # Standardize values for comparison
    s_val1 = str(val1).strip().lower() if val1 is not None else ""
    s_val2 = str(val2).strip().lower() if val2 is not None else ""
    
    if s_val1 == s_val2 and s_val1 != "":
        # Agreement: boost max confidence
        return min(1.0, max(conf1, conf2) + AGREEMENT_BOOST)
    else:
        # Conflict: reduce chosen source's confidence
        chosen_conf = conf1 if chosen_source == source1 else conf2
        return round(chosen_conf * CONFLICT_REDUCTION_FACTOR, 3)

def calculate_overall_confidence(field_confidences: Dict[str, float], provenance: Optional[Dict[str, Any]] = None) -> float:
    """
    Computes overall candidate profile confidence.
    Calculated as the average confidence of all evaluated fields, scaled by source presence.
    """
    if not field_confidences:
        return 0.0
        
    # Filter out internal/technical keys
    clean_confidences = {k: v for k, v in field_confidences.items() if not k.startswith("_")}
    if not clean_confidences:
        return 0.0
    
    scores = list(clean_confidences.values())
    overall = sum(scores) / len(scores)
    
    if provenance:
        has_resume = False
        has_csv = False
        for entry in provenance.values():
            src = entry.source.lower() if hasattr(entry, "source") else str(entry).lower()
            if "resume" in src:
                has_resume = True
            if "csv" in src or "recruiter" in src:
                has_csv = True
                
        if has_resume and has_csv:
            # Both sources match: typically 80-95
            pass
        elif has_resume:
            # Resume only: scale average to around 70-80
            overall = overall * 0.85
        elif has_csv:
            # CSV only: scale average to around 45-60
            overall = overall * 0.70
            
    return round(overall, 3)
