import logging
from typing import Dict, Any, List, Optional
from models.canonical import (
    CanonicalProfile, Location, ExperienceEntry, EducationEntry, SkillEntry, ProvenanceEntry
)
from normalizers.phone import normalize_phone
from normalizers.email import normalize_email
from normalizers.dates import normalize_date
from normalizers.skills import normalize_skill
from normalizers.location import parse_location, normalize_country
from merge.confidence import (
    compute_merged_confidence, calculate_overall_confidence, get_base_confidence,
    RESUME_BASE_CONFIDENCE, CSV_BASE_CONFIDENCE, AGREEMENT_BOOST
)
from merge.provenance import create_provenance_entry
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

def check_identity_consistency(
    csv_profile: Optional[Dict[str, Any]],
    resume_profile: Optional[Dict[str, Any]]
) -> str:
    if not csv_profile or not resume_profile:
        return "Not Applicable"
        
    res_emails = [normalize_email(e) for e in resume_profile.get("emails", []) if normalize_email(e)]
    csv_emails = [normalize_email(e) for e in csv_profile.get("emails", []) if normalize_email(e)]
    
    res_phones = [normalize_phone(p) for p in resume_profile.get("phones", []) if normalize_phone(p)]
    csv_phones = [normalize_phone(p) for p in csv_profile.get("phones", []) if normalize_phone(p)]
    
    res_name = resume_profile.get("full_name")
    csv_name = csv_profile.get("full_name")
    
    emails_overlap = any(e in csv_emails for e in res_emails) if (res_emails and csv_emails) else False
    phones_overlap = any(p in csv_phones for p in res_phones) if (res_phones and csv_phones) else False
    names_overlap = fuzz.ratio(str(res_name).lower(), str(csv_name).lower()) >= 80 if (res_name and csv_name) else False
    
    if emails_overlap or phones_overlap or names_overlap:
        return "Passed"
    return "Failed"

def merge_profiles(
    csv_profile: Optional[Dict[str, Any]],
    resume_profile: Optional[Dict[str, Any]],
    csv_source_name: str = "recruiter.csv",
    resume_source_name: str = "resume.pdf",
    identity_check_failed: bool = False
) -> CanonicalProfile:
    """
    Merges intermediate CSV and PDF candidate profiles into a single CanonicalProfile.
    Applies normalizations, conflict resolution rules, confidence scoring, and provenance.
    """
    id_status = check_identity_consistency(csv_profile, resume_profile)
    if identity_check_failed or id_status == "Failed":
        # Mismatch: disable merge and fallback to Resume profile only
        profile = merge_profiles(
            csv_profile=None,
            resume_profile=resume_profile,
            csv_source_name=csv_source_name,
            resume_source_name=resume_source_name,
            identity_check_failed=False
        )
        # Apply the confidence penalty
        profile.overall_confidence = min(profile.overall_confidence, 0.65)
        return profile
    profile = CanonicalProfile()
    
    # Track sources presence
    has_csv = csv_profile is not None
    has_resume = resume_profile is not None
    
    if not has_csv and not has_resume:
        logger.warning("No candidate profile sources provided. Returning empty profile.")
        return profile
        
    # Helper to resolve field source preference
    # Default preferences:
    # - Resume preferred for skills, headline, experience, education, years_experience
    # - Recruiter preferred for contact info (emails, phones, location), candidate_id
    
    # 1. Candidate ID (Recruiter preferred)
    if has_csv and csv_profile.get("candidate_id"):
        profile.candidate_id = csv_profile["candidate_id"]
        profile.provenance["candidate_id"] = create_provenance_entry(csv_source_name, "csv_parsing")
        profile.field_confidences["candidate_id"] = get_base_confidence(csv_source_name)
    elif has_resume and resume_profile.get("candidate_id"):
        profile.candidate_id = resume_profile["candidate_id"]
        profile.provenance["candidate_id"] = create_provenance_entry(resume_source_name, "pdf_extraction")
        profile.field_confidences["candidate_id"] = get_base_confidence(resume_source_name)
        
    # 2. Full Name (Resume preferred for self-report, fallback to Recruiter)
    csv_name = csv_profile.get("full_name") if has_csv else None
    resume_name = resume_profile.get("full_name") if has_resume else None
    
    if csv_name and resume_name:
        profile.full_name = resume_name # Resume preferred
        profile.provenance["full_name"] = create_provenance_entry(resume_source_name, "pdf_extraction")
        profile.field_confidences["full_name"] = compute_merged_confidence(
            resume_name, csv_name, resume_source_name, csv_source_name, resume_source_name
        )
    elif resume_name:
        profile.full_name = resume_name
        profile.provenance["full_name"] = create_provenance_entry(resume_source_name, "pdf_extraction")
        profile.field_confidences["full_name"] = get_base_confidence(resume_source_name)
    elif csv_name:
        profile.full_name = csv_name
        profile.provenance["full_name"] = create_provenance_entry(csv_source_name, "csv_parsing")
        profile.field_confidences["full_name"] = get_base_confidence(csv_source_name)
        
    # 3. Emails (Recruiter preferred for contact info)
    csv_emails = [normalize_email(e) for e in csv_profile.get("emails", [])] if has_csv else []
    csv_emails = [e for e in csv_emails if e]
    resume_emails = [normalize_email(e) for e in resume_profile.get("emails", [])] if has_resume else []
    resume_emails = [e for e in resume_emails if e]
    
    merged_emails = []
    # Prioritize recruiter emails
    for e in csv_emails:
        if e not in merged_emails:
            merged_emails.append(e)
    for e in resume_emails:
        if e not in merged_emails:
            merged_emails.append(e)
            
    profile.emails = merged_emails
    
    if merged_emails:
        in_csv = len(csv_emails) > 0
        in_resume = len(resume_emails) > 0
        
        if in_csv and in_resume:
            profile.provenance["emails"] = create_provenance_entry(
                f"{csv_source_name},{resume_source_name}",
                "merge_and_email_normalization"
            )
            profile.field_confidences["emails"] = compute_merged_confidence(
                csv_emails[0], resume_emails[0], csv_source_name, resume_source_name, csv_source_name
            )
        elif in_csv:
            profile.provenance["emails"] = create_provenance_entry(csv_source_name, "csv_parsing")
            profile.field_confidences["emails"] = get_base_confidence(csv_source_name)
        else:
            profile.provenance["emails"] = create_provenance_entry(resume_source_name, "pdf_extraction")
            profile.field_confidences["emails"] = get_base_confidence(resume_source_name)
            
    # 4. Phones (Recruiter preferred)
    csv_phones = [normalize_phone(p) for p in csv_profile.get("phones", [])] if has_csv else []
    csv_phones = [p for p in csv_phones if p]
    resume_phones = [normalize_phone(p) for p in resume_profile.get("phones", [])] if has_resume else []
    resume_phones = [p for p in resume_phones if p]
    
    merged_phones = []
    for p in csv_phones:
        if p not in merged_phones:
            merged_phones.append(p)
    for p in resume_phones:
        if p not in merged_phones:
            merged_phones.append(p)
            
    profile.phones = merged_phones
    
    if merged_phones:
        in_csv = len(csv_phones) > 0
        in_resume = len(resume_phones) > 0
        
        if in_csv and in_resume:
            profile.provenance["phones"] = create_provenance_entry(
                f"{csv_source_name},{resume_source_name}",
                "merge_and_phone_normalization"
            )
            profile.field_confidences["phones"] = compute_merged_confidence(
                csv_phones[0], resume_phones[0], csv_source_name, resume_source_name, csv_source_name
            )
        elif in_csv:
            profile.provenance["phones"] = create_provenance_entry(csv_source_name, "csv_parsing")
            profile.field_confidences["phones"] = get_base_confidence(csv_source_name)
        else:
            profile.provenance["phones"] = create_provenance_entry(resume_source_name, "pdf_extraction")
            profile.field_confidences["phones"] = get_base_confidence(resume_source_name)
            
    # 5. Location (Recruiter preferred for structured data, fallback to Resume)
    csv_loc = csv_profile.get("location") if has_csv else None
    resume_loc = resume_profile.get("location") if has_resume else None
    
    chosen_loc_str = None
    loc_source = None
    loc_method = None
    loc_conf = 0.0
    
    if csv_loc and resume_loc:
        chosen_loc_str = csv_loc # Recruiter preferred
        loc_source = csv_source_name
        loc_method = "csv_parsing"
        loc_conf = compute_merged_confidence(csv_loc, resume_loc, csv_source_name, resume_source_name, csv_source_name)
    elif csv_loc:
        chosen_loc_str = csv_loc
        loc_source = csv_source_name
        loc_method = "csv_parsing"
        loc_conf = get_base_confidence(csv_source_name)
    elif resume_loc:
        chosen_loc_str = resume_loc
        loc_source = resume_source_name
        loc_method = "pdf_extraction"
        loc_conf = get_base_confidence(resume_source_name)
        
    if chosen_loc_str:
        parsed = parse_location(chosen_loc_str)
        profile.location = Location(
            city=parsed["city"],
            state=parsed["state"],
            country=parsed["country"]
        )
        profile.provenance["location"] = create_provenance_entry(loc_source, f"{loc_method}_and_normalization")
        profile.field_confidences["location"] = loc_conf
        
    # 6. Links (Merge both)
    csv_links = csv_profile.get("links", []) if has_csv else []
    resume_links = resume_profile.get("links", []) if has_resume else []
    
    merged_links = list(dict.fromkeys(csv_links + resume_links))
    profile.links = merged_links
    if merged_links:
        if csv_links and resume_links:
            profile.provenance["links"] = create_provenance_entry(
                f"{csv_source_name},{resume_source_name}",
                "merge_links"
            )
            profile.field_confidences["links"] = min(1.0, max(get_base_confidence(csv_source_name), get_base_confidence(resume_source_name)) + AGREEMENT_BOOST)
        elif csv_links:
            profile.provenance["links"] = create_provenance_entry(csv_source_name, "csv_parsing")
            profile.field_confidences["links"] = get_base_confidence(csv_source_name)
        else:
            profile.provenance["links"] = create_provenance_entry(resume_source_name, "pdf_extraction")
            profile.field_confidences["links"] = get_base_confidence(resume_source_name)
            
    # 7. Headline (Resume preferred)
    csv_hl = csv_profile.get("headline") if has_csv else None
    resume_hl = resume_profile.get("headline") if has_resume else None
    
    if csv_hl and resume_hl:
        profile.headline = resume_hl
        profile.provenance["headline"] = create_provenance_entry(resume_source_name, "pdf_extraction")
        profile.field_confidences["headline"] = compute_merged_confidence(resume_hl, csv_hl, resume_source_name, csv_source_name, resume_source_name)
    elif resume_hl:
        profile.headline = resume_hl
        profile.provenance["headline"] = create_provenance_entry(resume_source_name, "pdf_extraction")
        profile.field_confidences["headline"] = get_base_confidence(resume_source_name)
    elif csv_hl:
        profile.headline = csv_hl
        profile.provenance["headline"] = create_provenance_entry(csv_source_name, "csv_parsing")
        profile.field_confidences["headline"] = get_base_confidence(csv_source_name)
        
    # 8. Years of Experience (Resume preferred - calculated from dates)
    csv_yoe = csv_profile.get("years_experience") if has_csv else None
    resume_yoe = resume_profile.get("years_experience") if has_resume else None
    
    if csv_yoe is not None and resume_yoe is not None:
        profile.years_experience = resume_yoe
        profile.provenance["years_experience"] = create_provenance_entry(resume_source_name, "pdf_timeline_calculation")
        profile.field_confidences["years_experience"] = compute_merged_confidence(
            resume_yoe, csv_yoe, resume_source_name, csv_source_name, resume_source_name
        )
    elif resume_yoe is not None:
        profile.years_experience = resume_yoe
        profile.provenance["years_experience"] = create_provenance_entry(resume_source_name, "pdf_timeline_calculation")
        profile.field_confidences["years_experience"] = get_base_confidence(resume_source_name)
    elif csv_yoe is not None:
        profile.years_experience = csv_yoe
        profile.provenance["years_experience"] = create_provenance_entry(csv_source_name, "csv_parsing")
        profile.field_confidences["years_experience"] = get_base_confidence(csv_source_name)
        
    # 9. Skills (Resume preferred, normalization applied)
    csv_skills = csv_profile.get("skills", []) if has_csv else []
    resume_skills = resume_profile.get("skills", []) if has_resume else []
    
    # Normalize skills
    norm_csv_skills = [normalize_skill(s) for s in csv_skills if normalize_skill(s)]
    norm_resume_skills = [normalize_skill(s) for s in resume_skills if normalize_skill(s)]
    
    merged_skills_dict = {}
    
    # Process Resume skills (preferred)
    for s in norm_resume_skills:
        # If in both, agreement boost
        if s in norm_csv_skills:
            conf = min(1.0, RESUME_BASE_CONFIDENCE + AGREEMENT_BOOST)
        else:
            conf = RESUME_BASE_CONFIDENCE
        merged_skills_dict[s] = conf
        
    # Process CSV skills
    for s in norm_csv_skills:
        if s not in merged_skills_dict:
            # Skill only in CSV
            merged_skills_dict[s] = CSV_BASE_CONFIDENCE
            
    # Map to SkillEntry objects
    profile.skills = [SkillEntry(name=name, confidence=conf) for name, conf in merged_skills_dict.items()]
    
    if profile.skills:
        if norm_resume_skills and norm_csv_skills:
            profile.provenance["skills"] = create_provenance_entry(
                f"{csv_source_name},{resume_source_name}",
                "rapidfuzz_normalization_and_merge"
            )
            # Skills field confidence is the average skill-level confidence
            profile.field_confidences["skills"] = round(sum(merged_skills_dict.values()) / len(merged_skills_dict), 3)
        elif norm_resume_skills:
            profile.provenance["skills"] = create_provenance_entry(resume_source_name, "pdf_extraction_and_normalization")
            profile.field_confidences["skills"] = RESUME_BASE_CONFIDENCE
        else:
            profile.provenance["skills"] = create_provenance_entry(csv_source_name, "csv_parsing_and_normalization")
            profile.field_confidences["skills"] = CSV_BASE_CONFIDENCE
            
    # 10. Experience (Resume preferred - detailed timeline)
    # We map start/end dates using the date normalizer
    resume_exp = resume_profile.get("experience", []) if has_resume else []
    
    formatted_exp = []
    for exp in resume_exp:
        entry = ExperienceEntry(
            title=exp.get("title"),
            company=exp.get("company"),
            start_date=normalize_date(exp.get("start_date")),
            end_date=normalize_date(exp.get("end_date")),
            description=exp.get("description"),
            years=exp.get("years")
        )
        formatted_exp.append(entry)
        
    # Sort experience: newest end_date first
    def get_sort_key(exp_entry: ExperienceEntry):
        end = exp_entry.end_date or ""
        if end.lower() == "present":
            return "9999-12"  # Place Present at the top
        return end
        
    formatted_exp.sort(key=get_sort_key, reverse=True)
    profile.experience = formatted_exp
    
    if formatted_exp:
        profile.provenance["experience"] = create_provenance_entry(resume_source_name, "pdf_extraction_and_timeline_sorting")
        profile.field_confidences["experience"] = RESUME_BASE_CONFIDENCE
        
    # 11. Education (Resume preferred - detailed schooling)
    resume_edu = resume_profile.get("education", []) if has_resume else []
    
    formatted_edu = []
    for edu in resume_edu:
        entry = EducationEntry(
            degree=edu.get("degree"),
            institution=edu.get("institution"),
            field_of_study=edu.get("field_of_study"),
            start_date=normalize_date(edu.get("start_date")),
            end_date=normalize_date(edu.get("end_date"))
        )
        formatted_edu.append(entry)
        
    # Sort education by end_date newest first
    formatted_edu.sort(key=lambda x: x.end_date or "", reverse=True)
    profile.education = formatted_edu
    
    if formatted_edu:
        profile.provenance["education"] = create_provenance_entry(resume_source_name, "pdf_extraction_and_date_normalization")
        profile.field_confidences["education"] = RESUME_BASE_CONFIDENCE
        
    # Calculate overall profile confidence
    profile.overall_confidence = calculate_overall_confidence(profile.field_confidences, profile.provenance)
    
    logger.info("Successfully merged source profiles into canonical record.")
    return profile
