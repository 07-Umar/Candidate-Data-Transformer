# Design Strategy & Methodology

This document outlines the product requirements, design decisions, and strategies behind the Candidate Data Transformer.

---

## 1. Engineering Design Principles

The Candidate Data Transformer is built entirely around four engineering principles:
- **Deterministic execution**: All pipeline components are reproducible and rule-based.
- **Explainable transformations**: Calculations and normalizations are fully explainable.
- **Config-driven output projection**: Dynamic schemas and output formats are configured at runtime.
- **End-to-end traceability using provenance**: Field origins are preserved throughout the lifecycle.

---

## 2. Dynamic Configurations & Projection

Rather than hardcoding output keys (e.g. assuming fields like `full_name` always exist), the application uses a configuration-driven architecture:

### Config-Driven Schema Mapping
- The **Projection Engine** reads the config JSON (e.g. `default_config.json` or `custom_config.json`) and maps fields dynamically at runtime.
- The UI scans the projected JSON properties rather than reading hardcoded dictionary fields. If the configuration changes (for example, mapping `full_name` to `candidate_name`), the Streamlit Dashboard automatically adjusts its metric cards, headers, and fields to match.

### Schema Validation
- Rather than maintaining a static JSON schema, the **Schema Validation** dynamically compiles a JSON Schema from the fields and types specified in the active runtime configuration.
- Any type deviation or missing required field is immediately caught before exporting.

---

## 3. Merge Strategy & Priority Policy

To consolidate unstructured resumes and structured recruiter records, the system enforces a strict priority policy:

- **Contact details take priority from Recruiter CSV Parser**: System databases are assumed to contain the latest vetted contact channels (emails, phones, location).
- **Professional experience history takes priority from Resume Parser**: Resumes contain rich chronological timelines, detailed descriptions, and skills list entries self-reported by the candidate.
- **Identity Safety**: Multi-source merging is only executed if the **Identity Consistency Check** passes (matching email, matching phone, or high fuzzy name similarity $\ge 80$). Mismatched profiles are blocked to prevent data cross-contamination.

---

## 4. Deterministic Confidence Scoring

The **Confidence Engine** models field reliability without employing statistical predictions:

- **Confidence Definition**:
  "Confidence represents the reliability of normalized candidate information after parsing, normalization, and merge processing."
- **Source Trust Base Coefficients**:
  - Resume Parser base trust = `0.9` (candidate direct input).
  - Recruiter CSV Parser base trust = `0.8` (recruiter database record).
- **Agreement Boost Heuristics**:
  - If both sources match on a normalized field, confidence is boosted by `+0.05` (up to a max of `1.0`).
- **Conflict Penalization Heuristics**:
  - If sources contain conflicting values, the higher priority value is merged, but confidence is penalized by multiplying the preferred source base trust by `0.75` (e.g., `0.9 * 0.75 = 0.675`).
- **Overall Score**:
  - Summarized as the simple average of all populated field confidence scores.
- **Explainability**:
  - If the candidate score is below `90%`, the UI presents a neutral explanation:
    `Confidence reflects extraction quality and agreement across available sources.`

---

## 5. UI Layout Design

The **Streamlit Dashboard** design follows a clean, engineering-focused look:
- **Modular Metrics**: Renders summary metrics dynamically depending on the keys exported in the configuration.
- **Formatting Hygiene**:
  - Formats experiences with proper readable bullet lists, cleaning line break wraps.
  - Standardizes timelines to clean human-readable date formats (e.g., `May 2024 – Aug 2024`).
- **Transparency**: Tabular **Provenance Tracking** details and step-by-step processing indicators show exactly how the data was transformed.
