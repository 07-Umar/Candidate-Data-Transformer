# Technical Design Document: Candidate Data Transformer

**Candidate:** Umar Mohmed | **Email:** umarmd0507@gmail.com | **Role:** Engineering Intern Assignment

---

## 1. Pipeline Architecture
The Candidate Ingestion Pipeline is an explainable, 100% deterministic system structured into highly decoupled modules. It processes unstructured PDF resumes and optional structured CSV records through the following execution stages:

```
[Inputs: PDF / CSV] ──► [Parsers] ──► [Field Normalization] ──► [Identity Consistency Check]
                                                                          │
[Canonical Candidate Model] ◄── [Confidence / Provenance] ◄── [Merge Engine]
         │
         ▼
[Projection Engine] ──► [Schema Validation] ──► [JSON Output / Streamlit Dashboard]
```

### Decoupled Pipeline Components:
1. **Parsers Layer (`parsers/`)**: 
   * `resume_parser.py` (Resume Parser): Employs `pdfplumber` layout analysis and regular expression heuristics to extract text, education boundaries, skills, and timelines.
   * `csv_parser.py` (Recruiter CSV Parser): Ingests recruiter candidate notes safely using `pandas`, handling missing headers and empty entries.
2. **Field Normalization (`normalizers/`)**: Standardizes individual fields into clean canonical representations before any merge calculations are executed.
3. **Identity Consistency Check**: A pre-merge screening process. Evaluates identity consistency using available signals such as email, phone, and candidate name before merge decisions are made, preventing merging mismatched profile sources.
4. **Merge Engine (`merge/merge_engine.py`)**: Merges multiple sources using strict, deterministic priority rules.
5. **Confidence Engine (`merge/confidence.py`)**: Evaluates the completeness, consistency, and alignment of the data sources.
6. **Provenance Tracking (`merge/provenance.py`)**: Logs the source files and extraction methods for auditing.
7. **Projection Engine (`projection/projector.py`)**: Reshapes the canonical structure into a custom schema using runtime configuration parameters.
8. **Schema Validation (`validator/schema_validator.py`)**: Dynamically compiles a JSON Schema from the runtime projection config and validates the output JSON using `jsonschema`.

---

## 2. Canonical Candidate Model & Field Normalization Rules

The internal candidate data model (`CanonicalProfile`) guarantees field integrity via strict `Pydantic` validation:
- **`candidate_id` / `full_name` / `headline`**: Cleaned, whitespace-trimmed strings.
- **`emails`**: Standardized to lowercase, stripped of whitespace, validated via regex, and deduplicated.
- **`phones`**: Standardized to international **E.164** standard using the `phonenumbers` library.
- **`location`**: Standardized country code using **ISO-3166-1 alpha-2** mappings (e.g. `IN`, `US`).
- **`links`**: Cleaned URLs prefixed with standard `https://` protocols.
- **`skills`**: Normalized against a vocabulary database using `rapidfuzz` string similarity matches (threshold $\ge 80$).
- **`experience`**: Experience history sorted newest-to-oldest, containing standard YYYY-MM or `"Present"` dates.
- **`education`**: Education records sorted newest-to-oldest, containing standard YYYY-MM dates.

---

## 3. Merge & Identity Consistency Check Policy

### Identity Consistency Check
Before joining a Resume PDF and Recruiter CSV record, the system validates the sources:
- **Email comparison**: Checks for exact matching of normalized emails.
- **Phone comparison**: Checks for exact matching of normalized E.164 phone numbers.
- **Fuzzy name similarity**: Computes name similarity using `rapidfuzz` string matching.
- **Outcome**: Compatible sources progress to merge. Mismatched sources are logged, reported, and blocked from merging.

### Merge Engine Priority Rules
If fields exist in both the Resume PDF and Recruiter CSV, the pipeline applies deterministic source priorities:
- **Contact Info (`emails`, `phones`, `location`)**: Recruiter CSV Parser values take priority (considered the system record-of-truth).
- **Professional Details (`skills`, `headline`, `experience`, `education`)**: Resume Parser values take priority (considered the candidate's self-reported timeline).

---

## 4. Confidence Engine Rules

"Confidence represents the reliability of normalized candidate information after parsing, normalization, and merge processing. Higher confidence indicates more complete, internally consistent, and better supported candidate information."

Confidence is calculated deterministically with the following base trust coefficients:
- **Resume Parser Base Trust**: `0.9`
- **Recruiter CSV Parser Base Trust**: `0.8`

### Field-Level Calculations:
- **Agreement**: If both sources agree on a normalized value, the field score is boosted:
  $$\text{Confidence}_{\text{merged}} = \min(1.0, \max(C_{\text{resume}}, C_{\text{csv}}) + 0.05)$$
- **Conflict**: If the sources contain different values, the preferred source's value is taken, but the score is penalized:
  $$\text{Confidence}_{\text{merged}} = C_{\text{preferred}} \times 0.75$$
- **Single Source**: If only one source provides the field, it receives the source's base trust.

### Profile-Level Calculations:
- **Overall Confidence**: Simple average of all populated field-level confidence scores.

---

## 5. Provenance Tracking & Audit Trail
Every field in the canonical candidate profile records its history in a `ProvenanceEntry` object:
- **`source`**: The exact origin file name (e.g. `resume.pdf` or `recruiter.csv` or both).
- **`method`**: The exact extraction or transformation method used (e.g. `pdf_extraction`, `csv_parsing`, `rapidfuzz_normalization_and_merge`).

---

## 6. Runtime Projection & Dynamic Validation
- **Projection**: Reads the configuration file, maps paths (e.g. `emails[0]` -> `primary_email`), performs renames, and controls metadata toggles (`include_confidence`/`include_provenance`). It handles missing values dynamically:
  - `null`: Missing values are set to `null`.
  - `omit`: Missing values are omitted from the output.
  - `error`: Raises a `ValueError` for any missing required fields.
- **Validation**: Generates a strict JSON Schema from the config parameters and validates the output using `jsonschema` to ensure complete compliance.

---

## 7. Edge Cases & Scope Details
- **Malformed CSV (Missing Headers/Empty)**: Parser catches pandas exceptions gracefully, logging errors and returning an empty dict to proceed on the remaining source (Resume).
- **Missing / Garbage PDF**: PDF parser logs the exception, returns empty data, and lets the pipeline execute solely on CSV.
- **Invalid Config Formats**: Checked immediately; CLI aborts with clear parameters error before executing the pipeline.
- **Out of Scope**: Automatic OCR for scanned PDF resumes (assumes readable text stream), advanced NLP for deep semantic skill extraction (relies on rapidfuzz), and live internet-based location queries (uses mapped dictionary lookups).
