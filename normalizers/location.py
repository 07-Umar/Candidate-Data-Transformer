import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Dictionary of common country name variants mapping to ISO 3166-1 alpha-2 codes
COUNTRY_MAP = {
    "india": "IN",
    "ind": "IN",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "us": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "canada": "CA",
    "can": "CA",
    "germany": "DE",
    "deutschland": "DE",
    "australia": "AU",
    "aus": "AU",
    "france": "FR",
    "singapore": "SG",
    "sg": "SG",
    "netherlands": "NL",
    "nl": "NL"
}

def normalize_country(country_str: str) -> str:
    """
    Standardize country name to ISO 3166-1 alpha-2 code.
    If no match, returns the capitalized original string.
    """
    if not country_str:
        return ""
    cleaned = country_str.strip().lower()
    
    # Try direct map lookup
    if cleaned in COUNTRY_MAP:
        return COUNTRY_MAP[cleaned]
        
    # Check if it already looks like an ISO code
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned.upper()
        
    return country_str.strip().title()

def parse_location(location_str: str) -> Dict[str, Optional[str]]:
    """
    Parse a raw location string (e.g. 'Hyderabad, Telangana, India') into city, state, country.
    Standardizes state abbreviations to their full names.
    """
    result = {"city": None, "state": None, "country": None}
    if not location_str:
        return result
        
    parts = [p.strip() for p in location_str.split(",") if p.strip()]
    
    # Consistent mapping for Indian states
    STATE_MAP = {
        "tg": "Telangana",
        "ts": "Telangana",
        "telangana": "Telangana",
        "ap": "Andhra Pradesh",
        "andhra pradesh": "Andhra Pradesh",
        "kar": "Karnataka",
        "karnataka": "Karnataka",
        "mh": "Maharashtra",
        "maharashtra": "Maharashtra",
        "dl": "Delhi",
        "delhi": "Delhi"
    }
    
    if len(parts) == 1:
        # Check if single part is a country
        country_norm = normalize_country(parts[0])
        if len(country_norm) == 2 and country_norm.isupper():
            result["country"] = country_norm
        else:
            # Check if it matches a known state
            p_lower = parts[0].lower()
            if p_lower in STATE_MAP:
                result["state"] = STATE_MAP[p_lower]
                result["country"] = "IN"
            else:
                result["city"] = parts[0].title()
    elif len(parts) == 2:
        p0_title = parts[0].title()
        p1_lower = parts[1].lower()
        
        # Check if second part is a state
        if p1_lower in STATE_MAP:
            result["city"] = p0_title
            result["state"] = STATE_MAP[p1_lower]
            result["country"] = "IN"
        else:
            # Treat as city, country
            country_norm = normalize_country(parts[1])
            result["city"] = p0_title
            result["country"] = country_norm
    elif len(parts) >= 3:
        result["city"] = parts[0].title()
        
        state_cleaned = parts[1].lower()
        if state_cleaned in STATE_MAP:
            result["state"] = STATE_MAP[state_cleaned]
        else:
            result["state"] = parts[1].title()
            
        result["country"] = normalize_country(parts[-1])
        
    return result
