# TECHNICAL ABSTRACT

### Candidate Data Transformer
**Multi-Source Candidate Profile Normalization Pipeline**

Developed by Umar Mohmed | Institute of Aeronautical Engineering | umarmd0507@gmail.com

---

### Project Objective
This system normalizes fragmented candidate details from Resume PDFs and Recruiter CSVs into a single canonical profile. The pipeline performs parsing, normalization, identity consistency validation, merge engine resolution, confidence scoring, provenance tracking, and schema validation. This deterministic architecture ensures data consistency, explainability, and downstream search usability. (49 words)

---

### System Pipeline

```
Resume PDF & Recruiter CSV
           |
           v
        Parsing
           |
           v
     Normalization
           |
           v
  Identity Validation
           |
           v
     Merge Engine
           |
           v
  Confidence Scoring
           |
           v
  Provenance Tracking
           |
           v
   Projection Engine
           |
           v
   Schema Validation
           |
           v
 Canonical Candidate JSON
```

---

### Key Features & Technology Stack

| Key Features | Technology Stack |
| :--- | :--- |
| ✓ Deterministic candidate pipeline. | • Python |
| ✓ Resume PDF parsing using `pdfplumber`. | • Streamlit |
| ✓ Recruiter CSV ingestion and field mapping. | • Pandas |
| ✓ Canonical field normalization. | • pdfplumber |
| ✓ Identity consistency validation. | • RapidFuzz |
| ✓ Configurable override merge logic. | • Pydantic |
| ✓ Confidence scoring based on source agreement. | • JSON |
| ✓ Explainable outputs with field-level provenance. | • YAML |
| ✓ Config-driven JSON projections. | |
| ✓ Draft-07 JSON Schema validation. | |

---

### Outputs & Results

| Outputs | Results |
| :--- | :--- |
| • Canonical Candidate Profile JSON | • Successfully transforms Resume-only candidate profiles. |
| • Configured Projected JSON Output | • Successfully transforms Recruiter CSV candidate profiles. |
| • Descriptive Stage Ingestion Summary | • Supports deterministic multi-source profile merging. |
| • Detailed Confidence Scores Matrix | • Gracefully handles incomplete candidate information. |
| • Field-Level Provenance Trace Logs | • Prevents unsafe merges after identity validation. |
| • JSON Schema Validation Reports | • Produces explainable outputs with complete provenance tracking. |

---

Developed by Umar Mohmed | Institute of Aeronautical Engineering
umarmd0507@gmail.com | github.com/07-Umar/Candidate-Data-Transformer

*Eightfold Engineering Internship Assignment 2026*
