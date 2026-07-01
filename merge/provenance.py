from typing import Dict, Any
from models.canonical import ProvenanceEntry

def create_provenance_entry(source: str, method: str) -> ProvenanceEntry:
    """Creates a standardized ProvenanceEntry."""
    return ProvenanceEntry(source=source, method=method)
