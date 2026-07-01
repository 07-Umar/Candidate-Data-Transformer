# Pipeline Architecture & Data Flow

This document details the system design, module layout, and data flow boundaries of the Candidate Data Transformer Pipeline.

---

## 1. Directory Structure & Modular Breakdown

The project follows a modular, decoupled architecture where each step of the pipeline represents a single responsibility:

```
eightfold-transformer/
├── models/
│   └── canonical.py             # Canonical Candidate Model (Pydantic schema definition)
├── parsers/
│   ├── csv_parser.py            # Recruiter CSV Parser (Pandas ingest)
│   └── resume_parser.py         # Resume Parser (pdfplumber extractor)
├── normalizers/
│   ├── phone.py                 # E.164 phone normalizer
│   ├── email.py                 # Clean/lowercase email normalizer
│   ├── dates.py                 # YYYY-MM date parser
│   ├── skills.py                # rapidfuzz skills matching
│   └── location.py              # ISO-3166 alpha-2 location standardizer
├── merge/
│   ├── merge_engine.py          # Merge Engine & Identity Consistency Check logic
│   ├── confidence.py            # Confidence Engine (Deterministic scoring)
│   └── provenance.py            # Provenance Tracking (Audit trail logging)
├── projection/
│   └── projector.py             # Projection Engine (Output schema remapper)
├── validator/
│   └── schema_validator.py      # Schema Validation (Dynamic schema builder)
└── ui/
    └── streamlit_app.py         # Streamlit Dashboard UI
```

---

## 2. Core System Interfaces

### Canonical Candidate Model
All raw extracted data is normalized and stored inside a unified internal schema representation defined in `models/canonical.py`.

```python
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
    provenance: Dict[str, ProvenanceEntry] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    field_confidences: Dict[str, float] = Field(default_factory=dict)
```

---

## 3. Data Processing Pipeline Flow

Every run of the Candidate Data Transformer executes sequentially through these deterministic steps:

### Phase 1: Ingestion & Extraction
* Input files are loaded.
* **Resume Parser** extracts raw text lines, matching boundaries to extract segments.
* **Recruiter CSV Parser** parses candidate notes using Pandas.

### Phase 2: Field Normalization
* Candidate fields are normalized:
  * Emails are validated and lowercased.
  * Phone numbers are parsed and formatted using the international E.164 standard.
  * Date fields are parsed into YYYY-MM strings.
  * Candidate skills are matched against a standardized vocabulary list using `rapidfuzz` string similarity.
  * Country values are mapped to ISO-3166-1 alpha-2 codes.

### Phase 3: Identity Consistency Check
* The system evaluates whether the PDF resume and the CSV recruiter notes belong to the same candidate:
  * Compares emails (exact match).
  * Compares phones (exact match).
  * Compares name similarity using fuzzy logic.
* If a conflict is detected, the pipeline records the mismatch details and reports the warnings.

### Phase 4: Merging & Audit Generation
* The **Merge Engine** joins fields:
  * Prefers Recruiter CSV Parser for contact data.
  * Prefers Resume Parser for experience, skills, and education details.
* The **Confidence Engine** calculates deterministic values based on agreement/conflict heuristics.
* The **Provenance Tracking** logs origin metadata for auditing.

### Phase 5: Runtime Projection & Verification
* The **Projection Engine** maps fields to custom outputs (e.g. `full_name` → `candidate_name`), formats default missing values, and toggles metadata wrappers.
* The **Schema Validation** dynamically generates a JSON Schema from the projection config and verifies the output structure.
