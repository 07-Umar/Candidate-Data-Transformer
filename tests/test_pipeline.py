import pytest
import os
import json
from models.canonical import CanonicalProfile, Location
from normalizers.phone import normalize_phone
from normalizers.email import normalize_email
from normalizers.dates import normalize_date
from normalizers.skills import normalize_skill
from normalizers.location import parse_location
from merge.merge_engine import merge_profiles
from projection.projector import project_candidate
from validator.schema_validator import validate_projected_output, SchemaValidationError, generate_json_schema
from parsers.csv_parser import parse_recruiter_csv

# --- Normalizer Tests ---

def test_normalize_phone():
    # Various Indian phone formats
    assert normalize_phone("+91-9392466218") == "+919392466218"
    assert normalize_phone("93924 66218") == "+919392466218"
    assert normalize_phone("+91 9392466218") == "+919392466218"
    # USA Format
    assert normalize_phone("4155552671", default_region="US") == "+14155552671"
    # Invalid fallback returns clean digits
    assert normalize_phone("invalid-phone-123") == "123"

def test_normalize_email():
    assert normalize_email(" UmarMD0507@GMAIL.COM ") == "umarmd0507@gmail.com"
    assert normalize_email("invalid_email") == ""
    assert normalize_email(None) == ""

def test_normalize_date():
    assert normalize_date("May 2024") == "2024-05"
    assert normalize_date("Oct. 2025") == "2025-10"
    assert normalize_date("2026 (Expected)") == "2026-06"
    assert normalize_date("Present") == "Present"
    assert normalize_date("Current") == "Present"
    # Malformed dates fallback gracefully
    assert normalize_date("not-a-date") == "not a date"

def test_normalize_skill():
    # Canonical match (PyTorch in list)
    assert normalize_skill("pytorch ") == "PyTorch"
    assert normalize_skill("python programming") == "Python"
    # Custom skill title-cased and preserved
    assert normalize_skill("quantum-computing") == "Quantum-Computing"

def test_normalize_location():
    parsed = parse_location("Hyderabad, Telangana, India")
    assert parsed["city"] == "Hyderabad"
    assert parsed["state"] == "Telangana"
    assert parsed["country"] == "IN"

    parsed_us = parse_location("San Francisco, CA, USA")
    assert parsed_us["city"] == "San Francisco"
    assert parsed_us["state"] == "Ca"
    assert parsed_us["country"] == "US"


# --- Parser Tests ---

def test_malformed_csv(tmp_path):
    # Empty CSV
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("")
    assert parse_recruiter_csv(str(csv_file)) is None

    # CSV missing expected headers
    malformed_csv = tmp_path / "malformed.csv"
    malformed_csv.write_text("random_col1,random_col2\nval1,val2")
    profile = parse_recruiter_csv(str(malformed_csv))
    assert profile is not None
    assert profile["full_name"] is None
    assert profile["emails"] == []


# --- Merge & Confidence Tests ---

def test_merge_missing_resume():
    csv_profile = {
        "candidate_id": "CAND-001",
        "full_name": "Umar Mohmed",
        "emails": ["umarmd0507@gmail.com"],
        "phones": ["+91-9392466218"],
        "location": "Hyderabad, India",
        "links": ["github.com/07-Umar"],
        "headline": "Software Engineer",
        "years_experience": 1.5,
        "skills": ["Python", "SQL"]
    }
    
    # Merge with missing resume profile
    merged = merge_profiles(csv_profile=csv_profile, resume_profile=None)
    
    assert merged.candidate_id == "CAND-001"
    assert merged.full_name == "Umar Mohmed"
    assert merged.field_confidences["full_name"] == 0.8  # Recruiter default
    assert merged.provenance["full_name"].source == "recruiter.csv"

def test_merge_conflicting_skills_and_data():
    csv_profile = {
        "candidate_id": "CAND-001",
        "full_name": "Umar Mohmed",
        "emails": ["umarmd0507@gmail.com"],
        "phones": ["+91-9392466218"],
        "location": "Hyderabad, India",
        "years_experience": 1.2, # Conflict
        "skills": ["Python", "C++"]
    }
    
    resume_profile = {
        "full_name": "Umar Mohmed",
        "emails": ["umarmd0507@gmail.com"],
        "phones": ["+91-9392466218"],
        "location": "Secunderabad, India", # Conflict
        "years_experience": 0.5, # Conflict
        "skills": ["Python", "Java", "PyTorch"]
    }
    
    merged = merge_profiles(csv_profile=csv_profile, resume_profile=resume_profile)
    
    # Skills check (Resume preferred + union)
    skill_names = [s.name for s in merged.skills]
    assert "Python" in skill_names
    assert "Java" in skill_names
    assert "PyTorch" in skill_names
    assert "C++" in skill_names
    
    # Conflicting location check (Recruiter preferred, i.e., Hyderabad)
    assert merged.location.city == "Hyderabad"
    # Location confidence reduced because of Secunderabad conflict
    assert merged.field_confidences["location"] < 0.8
    
    # Years of experience check (Resume preferred, 0.5)
    assert merged.years_experience == 0.5
    # Conflicting YOE reduces confidence of field
    assert merged.field_confidences["years_experience"] == round(0.9 * 0.75, 3)


# --- Projection and Validation Tests ---

def test_projection_missing_values_omit():
    profile = CanonicalProfile(
        full_name="Umar Mohmed",
        emails=["umarmd0507@gmail.com"],
        field_confidences={"full_name": 0.9, "emails": 0.9}
    )
    
    config = {
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "missing_phone", "from": "phones[0]", "type": "string", "required": False }
        ],
        "include_confidence": False,
        "include_provenance": False,
        "on_missing": "omit"
    }
    
    projected = project_candidate(profile, config)
    # missing_phone must be omitted from output
    assert "name" in projected
    assert "missing_phone" not in projected

def test_projection_missing_values_null():
    profile = CanonicalProfile(
        full_name="Umar Mohmed",
        emails=["umarmd0507@gmail.com"],
        field_confidences={"full_name": 0.9, "emails": 0.9}
    )
    
    config = {
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "missing_phone", "from": "phones[0]", "type": "string", "required": False }
        ],
        "include_confidence": False,
        "include_provenance": False,
        "on_missing": "null"
    }
    
    projected = project_candidate(profile, config)
    # missing_phone must be null in output
    assert projected["name"] == "Umar Mohmed"
    assert projected["missing_phone"] is None

def test_projection_missing_values_error():
    profile = CanonicalProfile(
        full_name="Umar Mohmed",
        emails=["umarmd0507@gmail.com"],
        field_confidences={"full_name": 0.9, "emails": 0.9}
    )
    
    config = {
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "missing_phone", "from": "phones[0]", "type": "string", "required": True } # Required & missing
        ],
        "include_confidence": False,
        "include_provenance": False,
        "on_missing": "error"
    }
    
    with pytest.raises(ValueError, match="Required field 'missing_phone'"):
        project_candidate(profile, config)

def test_schema_validation_success():
    projected = {
        "name": "Umar Mohmed",
        "primary_email": "umarmd0507@gmail.com",
        "_confidence": {
            "name": 0.9,
            "primary_email": 0.9
        },
        "_overall_confidence": 0.9
    }
    
    config = {
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "primary_email", "from": "emails[0]", "type": "string", "required": True }
        ],
        "include_confidence": True,
        "include_provenance": False
    }
    
    # Should not raise any exception
    validate_projected_output(projected, config)

def test_schema_validation_failure():
    # Value type mismatch (name should be string, but is int)
    projected = {
        "name": 12345,
        "primary_email": "umarmd0507@gmail.com"
    }
    
    config = {
        "fields": [
            { "path": "name", "from": "full_name", "type": "string", "required": True },
            { "path": "primary_email", "from": "emails[0]", "type": "string", "required": True }
        ],
        "include_confidence": False,
        "include_provenance": False
    }
    
    with pytest.raises(SchemaValidationError, match="Validation Error"):
        validate_projected_output(projected, config)
