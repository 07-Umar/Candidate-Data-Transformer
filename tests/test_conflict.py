import pytest
from merge.merge_engine import merge_profiles

def test_provenance_conflict_resolution():
    # Inputs with conflicting values in list fields and single fields
    csv_profile = {
        "candidate_id": "CAND-001",
        "full_name": "Umar Mohmed",
        "emails": ["umarmd0507@gmail.com", "second_csv@gmail.com"],
        "phones": ["+91-9866473260"],
        "location": "Hyderabad, TG, India",
        "links": ["github.com/07-Umar"],
        "headline": "ML Engineer Intern",
        "years_experience": 1.0,
        "skills": ["Python", "SQL"]
    }
    
    resume_profile = {
        "full_name": "Umar Mohmed",
        "emails": ["umarmd0507@gmail.com", "second_resume@gmail.com"],
        "phones": ["+91-9392466218"],
        "location": "Secunderabad, India",
        "links": ["linkedin.com/in/umarmohmed"],
        "headline": "Resume Headline",
        "years_experience": 0.5,
        "skills": ["Java", "Python"]
    }
    
    merged = merge_profiles(csv_profile=csv_profile, resume_profile=resume_profile)
    
    # 1. Phone Conflict:
    assert merged.phones == ["+919866473260", "+919392466218"]
    assert merged.provenance["phones"].source == "recruiter.csv,resume.pdf"
    assert merged.provenance["phones"].method == "merge_and_phone_normalization"
    
    # 2. Email Conflict:
    assert merged.emails == ["umarmd0507@gmail.com", "second_csv@gmail.com", "second_resume@gmail.com"]
    assert merged.provenance["emails"].source == "recruiter.csv,resume.pdf"
    assert merged.provenance["emails"].method == "merge_and_email_normalization"
    
    # 3. Links Conflict:
    assert merged.links == ["github.com/07-Umar", "linkedin.com/in/umarmohmed"]
    assert merged.provenance["links"].source == "recruiter.csv,resume.pdf"
    assert merged.provenance["links"].method == "merge_links"
    
    # 4. Skills Conflict:
    skill_names = [s.name for s in merged.skills]
    assert "Python" in skill_names
    assert "SQL" in skill_names
    assert "Java" in skill_names
    assert merged.provenance["skills"].source == "recruiter.csv,resume.pdf"
    assert merged.provenance["skills"].method == "rapidfuzz_normalization_and_merge"
    
    # 5. Headline Conflict (single-value preferred):
    assert merged.headline == "Resume Headline"
    assert merged.provenance["headline"].source == "resume.pdf"
    
    # 6. Location Conflict (single-value preferred):
    assert merged.location.city == "Hyderabad"
    assert merged.provenance["location"].source == "recruiter.csv"
