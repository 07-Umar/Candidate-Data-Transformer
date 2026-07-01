import pytest
import os
import json
from merge.merge_engine import merge_profiles
from projection.projector import project_candidate
from validator.schema_validator import validate_projected_output

def test_confidence_ordering_and_mismatch():
    resume_profile = {
        "full_name": "Umar Mohmed",
        "emails": ["umarmd0507@gmail.com"],
        "phones": ["+91-9392466218"],
        "location": "Hyderabad, India",
        "years_experience": 1.0,
        "skills": ["Python", "Java"]
    }
    
    csv_profile_matching = {
        "candidate_id": "CAND-001",
        "full_name": "Umar Mohmed",
        "emails": ["umarmd0507@gmail.com"],
        "phones": ["+91-9392466218"],
        "location": "Hyderabad, India",
        "years_experience": 1.0,
        "skills": ["Python", "Java"]
    }
    
    csv_profile_mismatched = {
        "candidate_id": "CAND-999",
        "full_name": "Fareedha Begum",
        "emails": ["fareedha@gmail.com"],
        "phones": ["+91-9999999999"],
        "location": "Bangalore, India",
        "years_experience": 5.0,
        "skills": ["Project Management"]
    }
    
    # TEST 1: Resume only
    merged_resume = merge_profiles(csv_profile=None, resume_profile=resume_profile)
    assert 0.70 <= merged_resume.overall_confidence <= 0.80
    
    # TEST 2: CSV only
    merged_csv = merge_profiles(csv_profile=csv_profile_matching, resume_profile=None)
    assert 0.45 <= merged_csv.overall_confidence <= 0.60
    
    # TEST 3: Matching Resume + CSV
    merged_matching = merge_profiles(csv_profile=csv_profile_matching, resume_profile=resume_profile)
    assert merged_matching.overall_confidence >= merged_resume.overall_confidence
    assert 0.80 <= merged_matching.overall_confidence <= 0.95
    
    # TEST 4: Different Resume + CSV (mismatch)
    merged_mismatched = merge_profiles(csv_profile=csv_profile_mismatched, resume_profile=resume_profile)
    # Merge should be blocked (meaning fallback to resume profile only), and penalized
    assert merged_mismatched.full_name == "Umar Mohmed"  # resume data preferred, CSV ignored
    assert merged_mismatched.overall_confidence <= 0.65

def test_missing_email_schema_validation():
    # TEST 5: CSV missing email completely
    csv_profile_no_email = {
        "candidate_id": "CAND-001",
        "full_name": "Umar Mohmed",
        "phones": ["+91-9392466218"],
        "location": "Hyderabad, India",
        "years_experience": 1.0,
        "skills": ["Python"]
    }
    
    merged = merge_profiles(csv_profile=csv_profile_no_email, resume_profile=None)
    
    # Load config and validate that projection does not throw and passes JSON schema validation
    with open("config/custom_config.json", "r", encoding="utf-8") as f:
        custom_config = json.load(f)
        
    projected = project_candidate(merged, custom_config)
    # Check that primary_email is populated with safe default "" instead of raising validation error
    assert "primary_email" in projected
    assert projected["primary_email"] == ""
    
    # Should not raise any jsonschema validation errors
    validate_projected_output(projected, custom_config)
