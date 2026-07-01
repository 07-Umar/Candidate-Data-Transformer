from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Location(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None  # Normalized to ISO-3166-1 alpha-2

class ExperienceEntry(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    start_date: Optional[str] = None  # Format: YYYY-MM
    end_date: Optional[str] = None    # Format: YYYY-MM
    description: Optional[str] = None
    years: Optional[float] = None

class EducationEntry(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None  # Format: YYYY-MM
    end_date: Optional[str] = None    # Format: YYYY-MM

class SkillEntry(BaseModel):
    name: str
    confidence: float = 1.0

class ProvenanceEntry(BaseModel):
    source: str
    method: str

class CanonicalProfile(BaseModel):
    candidate_id: Optional[str] = None
    full_name: Optional[str] = None
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Optional[Location] = None
    links: List[str] = Field(default_factory=list)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[SkillEntry] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)  # Maps field path (e.g. "full_name") to ProvenanceEntry
    overall_confidence: float = 0.0
    field_confidences: Dict[str, float] = Field(default_factory=dict)  # Maps field path to confidence score
