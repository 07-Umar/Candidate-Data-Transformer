import pandas as pd
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

def parse_recruiter_csv(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Parses the recruiter CSV file and returns a raw candidate dictionary.
    Handles potential parsing, column mapping, and file errors gracefully.
    """
    if not os.path.exists(file_path):
        logger.error(f"CSV file not found at path: {file_path}")
        return None
        
    try:
        # Load CSV using pandas
        # Keep all values as strings initially to avoid auto-formatting issues
        df = pd.read_csv(file_path, dtype=str)
    except Exception as e:
        logger.error(f"Failed to load CSV file '{file_path}': {e}")
        return None
        
    if df.empty:
        logger.warning(f"CSV file '{file_path}' is empty.")
        return None
        
    # Standardize column headers (lowercase and strip spaces)
    df.columns = [col.strip().lower() for col in df.columns]
    
    # We take the first row as the candidate profile
    row = df.iloc[0].to_dict()
    
    # Clean string values (strip spaces and handle NaN/None)
    cleaned_row = {}
    for k, v in row.items():
        if pd.isna(v) or str(v).lower() in ["nan", "none", "null", ""]:
            cleaned_row[k] = None
        else:
            cleaned_row[k] = str(v).strip()
            
    # Extract fields from row and map to canonical names
    # Support variations in column headers
    candidate = {}
    
    # Candidate ID
    candidate["candidate_id"] = cleaned_row.get("candidate_id") or cleaned_row.get("id")
    
    # Full Name
    candidate["full_name"] = cleaned_row.get("full_name") or cleaned_row.get("name")
    
    # Emails (can be comma-separated)
    email_val = (
        cleaned_row.get("emails") or 
        cleaned_row.get("email") or 
        cleaned_row.get("email_address") or 
        cleaned_row.get("candidate_email") or
        cleaned_row.get("primary_email") or
        cleaned_row.get("contact_email")
    )
    candidate["emails"] = [e.strip() for e in email_val.split(",")] if email_val else []
    
    # Phones (can be comma-separated)
    phone_val = cleaned_row.get("phones") or cleaned_row.get("phone") or cleaned_row.get("mobile")
    candidate["phones"] = [p.strip() for p in phone_val.split(",")] if phone_val else []
    
    # Location
    candidate["location"] = cleaned_row.get("location") or cleaned_row.get("address")
    
    # Links
    links_val = cleaned_row.get("links") or cleaned_row.get("linkedin") or cleaned_row.get("github") or cleaned_row.get("urls")
    candidate["links"] = [l.strip() for l in links_val.split(",")] if links_val else []
    
    # Headline
    candidate["headline"] = cleaned_row.get("headline") or cleaned_row.get("title")
    
    # Years of Experience
    yoe_val = cleaned_row.get("years_experience") or cleaned_row.get("experience_years") or cleaned_row.get("yoe")
    if yoe_val:
        try:
            candidate["years_experience"] = float(yoe_val)
        except ValueError:
            logger.warning(f"Could not parse years of experience '{yoe_val}' as float. Setting to None.")
            candidate["years_experience"] = None
    else:
        candidate["years_experience"] = None
        
    # Skills
    skills_val = cleaned_row.get("skills")
    candidate["skills"] = [s.strip() for s in skills_val.split(",")] if skills_val else []
    
    # Initialize list fields to empty lists for safety
    candidate["experience"] = []
    candidate["education"] = []
    
    logger.info(f"Successfully parsed recruiter CSV candidate: {candidate['full_name']}")
    return candidate
