import re
import logging
import pdfplumber
from typing import Dict, Any, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

# Regular expressions for contact information
EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_REGEX = re.compile(r"\+?\d[\d\-\s\(\)\.]{8,}\d")

# Expanded Link Regex supporting GeeksforGeeks along with other popular platforms
LINK_REGEX = re.compile(
    r"\b(?:https?://)?(?:www\.)?(?:github\.com|linkedin\.com/in|leetcode\.com(?:/u)?|geeksforgeeks\.org(?:/user|/profile|/u)?|auth\.geeksforgeeks\.org/user|hackerrank\.com|behance\.net)\/[a-zA-Z0-9_\-\.\+]+",
    re.IGNORECASE
)

# Date range pattern for experience and education
# Captures formats like: "May 2024 – Aug 2024", "Oct. 2025", "2022–2026", "2019-2021", "2022 - 2026 (Expected)"
DATE_RANGE_REGEX = re.compile(
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})\s*[\-–—\u2013\u2014]\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Expected|Current)\b",
    re.IGNORECASE
)

# Common education keywords ordered to prioritize specific matches first
DEGREE_KEYWORDS = [
    "B.Tech", "B.E.", "M.Tech", "M.E.", "B.S.", "M.S.", "Ph.D.", "Bachelor", "Master",
    "Intermediate", "SSC", "HSC", "High School", "Matriculation", "Secondary"
]

# Institute/Organization keywords to filter out of locations
INSTITUTE_KEYWORDS = [
    "institute", "university", "college", "school", "board", "academy", "engineering", "technology", 
    "llc", "corp", "inc", "co", "ltd", "corporation", "limited", "departments", "faculty"
]

class ResumeDict(dict):
    """
    Custom dictionary subclass that returns an empty list for 'links'
    during merge operations to prevent TypeErrors, but retains None 
    for serialization and representation.
    """
    def get(self, key, default=None):
        val = super().get(key, default)
        if key == "links" and val is None:
            return []
        return val
        
    def __getitem__(self, key):
        val = super().__getitem__(key)
        if key == "links" and val is None:
            return []
        return val

def extract_raw_text(pdf_path: str) -> str:
    """Extracts raw text from a PDF file using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.error(f"Failed to read PDF '{pdf_path}': {e}")
    return text

def parse_sections(text: str) -> Dict[str, str]:
    """
    Partitions resume text into sections based on header keywords.
    Appends duplicate headers (e.g. Technical Skills and Soft Skills) under the same section key.
    """
    sections = {}
    lines = text.split("\n")
    
    # Standard headers we look for
    headers = {
        "education": ["education", "academic background", "qualification", "academic profile"],
        "experience": ["experience", "work experience", "professional experience", "internship", "project experience", "employment history", "work history", "experiences"],
        "projects": ["projects", "key projects", "academic projects", "personal projects"],
        "skills": ["technical skills", "skills summary", "technical & communication skills", "core skills", "skills", "skills & tools", "competencies", "soft skills", "key skills", "professional skills"],
        "certifications": ["certifications", "licenses"],
        "publications": ["publications", "research papers", "patents"],
        "achievements": ["achievements", "honors & awards", "awards", "honors and awards"]
    }
    
    current_section = "header"
    sections[current_section] = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        # Check if line is a header
        is_header = False
        for sec_name, keywords in headers.items():
            for kw in keywords:
                # Match keyword at start of line with a word boundary
                if len(line_stripped) < 50 and re.match(rf"^{re.escape(kw)}\b", line_stripped, re.IGNORECASE):
                    current_section = sec_name
                    is_header = True
                    break
            if is_header:
                break
                
        if is_header:
            if current_section not in sections:
                sections[current_section] = []
        else:
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(line)
            
    # Join list of lines into section texts
    return {k: "\n".join(v) for k, v in sections.items()}

def calculate_years_from_range(start_str: str, end_str: str) -> float:
    """Calculates duration in years between two date strings (approximate)."""
    import dateparser
    from datetime import datetime
    
    try:
        start_dt = dateparser.parse(start_str)
        # Handle 'Present' or 'Current' or 'Expected'
        if not end_str or end_str.lower() in ["present", "current", "ongoing", "now", "expected"]:
            end_dt = datetime.now()
        else:
            end_dt = dateparser.parse(end_str)
            
        if start_dt and end_dt:
            delta = end_dt - start_dt
            return max(0.0, round(delta.days / 365.25, 1))
    except Exception:
        pass
    return 0.0

def validate_username(username: str) -> bool:
    """
    Validates a parsed social handle username.
    Excludes network protocol descriptors and ensures it matches valid format limits.
    """
    if not username:
        return False
    u_lower = username.lower().strip()
    invalid_tokens = ["https", "http", "www", "linkedin", "github", "com", "org", "user", "in", "u"]
    if u_lower in invalid_tokens:
        return False
    # Only accept letters, numbers, underscores, hyphens
    if not re.match(r"^[a-zA-Z0-9_\-]+$", username):
        return False
    return True

def clean_location_string(loc_str: str) -> Optional[str]:
    """
    Cleans up a raw location string by stripping out institute/company names and noise words.
    Prevents academic organizations and dates from leaking into candidate city/country elements.
    """
    if not loc_str:
        return None
        
    # Strip specified noise keywords
    noise_words = [
        "expected", "present", "current", "cgpa", "gpa", "year", "institute", 
        "college", "university", "school", "board", "academy", "engineering", "technology"
    ]
    cleaned = loc_str
    for word in noise_words:
        cleaned = re.sub(rf"\b{word}\b", "", cleaned, flags=re.IGNORECASE)
        
    # Remove dates, years, grades and extra numbers
    cleaned = re.sub(r"\b(19\d{2}|20\d{2})\b", "", cleaned)
    cleaned = re.sub(r"\b\d+[\.\d]*\s*/?\s*\d*\b", "", cleaned)
    cleaned = re.sub(r"[\d•\*;\(\)\–\-–\u2013\u2014%/]", "", cleaned)
    
    # Normalize spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # Split by comma
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    cleaned_parts = []
    
    for part in parts:
        if any(kw in part.lower() for kw in INSTITUTE_KEYWORDS):
            continue
        if len(part) > 2:
            cleaned_parts.append(part)
            
    if cleaned_parts:
        return ", ".join(cleaned_parts)
    return None

def extract_location(raw_text: str) -> Optional[str]:
    """
    Extracts location details by scanning text for known cities, states, and countries.
    Resolves formatting issues to keep city=None if not confidently determined.
    """
    known_cities = {
        "hyderabad": "Hyderabad", "secunderabad": "Secunderabad", "bangalore": "Bangalore", 
        "bengaluru": "Bangalore", "pune": "Pune", "mumbai": "Mumbai", "delhi": "Delhi", 
        "chennai": "Chennai", "kolkata": "Kolkata", "san francisco": "San Francisco", "london": "London",
        "jaipur": "Jaipur", "ahmedabad": "Ahmedabad", "nagpur": "Nagpur", "gurgaon": "Gurgaon", "noida": "Noida"
    }
    known_states = {
        "telangana": "Telangana", "tg": "Telangana", "ts": "Telangana", "ap": "Andhra Pradesh", 
        "andhra pradesh": "Andhra Pradesh", "california": "California", "ca": "California", 
        "new york": "New York", "ny": "New York", "karnataka": "Karnataka", "maharashtra": "Maharashtra"
    }
    known_countries = {
        "india": "India", "ind": "India", "usa": "USA", "us": "USA", 
        "united states": "USA", "uk": "UK", "united kingdom": "UK", "canada": "Canada"
    }
    
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    header_text = "\n".join(lines[:15])
    
    city = None
    state = None
    country = None
    
    def scan_text(text_block: str):
        found_city = None
        found_state = None
        found_country = None
        
        # Scan for city
        for k, v in known_cities.items():
            if re.search(rf"\b{re.escape(k)}\b", text_block, re.IGNORECASE):
                found_city = v
                break
                
        # Scan for state
        for k, v in known_states.items():
            if re.search(rf"\b{re.escape(k)}\b", text_block, re.IGNORECASE):
                found_state = v
                break
                
        # Scan for country
        for k, v in known_countries.items():
            if re.search(rf"\b{re.escape(k)}\b", text_block, re.IGNORECASE):
                found_country = v
                break
                
        return found_city, found_state, found_country

    # Scan header first
    city, state, country = scan_text(header_text)
    
    # Fallback to scan full text if no city found
    if not city:
        city_f, state_f, country_f = scan_text(raw_text)
        if city_f:
            city = city_f
        if not state:
            state = state_f
        if not country:
            country = country_f
            
    # Fallback: scan for "City, Known State" or "City, Known Country" patterns
    if not city:
        for line in lines[:20]:
            line_clean = re.sub(r"[\d•\*;\(\)\–\-–\u2013\u2014%/]", "", line).strip()
            parts = [p.strip() for p in line_clean.split(",") if p.strip()]
            if len(parts) >= 2:
                for idx, part in enumerate(parts):
                    p_lower = part.lower()
                    if p_lower in known_states or p_lower in known_countries:
                        if idx > 0:
                            potential_city = parts[idx-1]
                            if len(potential_city.split()) <= 2:
                                if not any(ik in potential_city.lower() for ik in INSTITUTE_KEYWORDS):
                                    city = potential_city.title()
                                    break
                if city:
                    break
            
    # Auto-fill country if city/state implies it
    if not country:
        if state in ["Telangana", "Andhra Pradesh", "Karnataka", "Maharashtra"] or city in ["Hyderabad", "Secunderabad", "Bangalore", "Pune", "Mumbai", "Delhi", "Chennai"]:
            country = "India"
        elif state in ["California", "New York"] or city in ["San Francisco"]:
            country = "USA"
            
    if city:
        if state and country:
            return f"{city}, {state}, {country}"
        elif state:
            return f"{city}, {state}"
        elif country:
            return f"{city}, {country}"
        return city
    else:
        if country:
            return country
        return None

def normalize_degree(degree_str: str, school_str: Optional[str] = None) -> Optional[str]:
    """Standardizes academic degree and secondary/intermediate labels."""
    if not degree_str:
        return None
    d_clean = degree_str.strip()
    d_lower = d_clean.lower()
    
    is_junior_college = False
    is_engineering_college = False
    
    if school_str:
        s_lower = school_str.lower()
        if any(x in s_lower for x in ["junior college", "jr college", "intermediate college", "junior", "board of intermediate"]):
            is_junior_college = True
        if any(x in s_lower for x in ["engineering", "technology", "iare", "aeronautical", "tech"]):
            is_engineering_college = True
            
    # Junior College with Secondary/Degree label -> Intermediate
    if is_junior_college:
        if d_lower in ["secondary school", "secondary", "ssc", "hsc", "degree", "intermediate"]:
            return "Intermediate"
            
    # Context-aware normalization for generic degrees
    if d_lower in ["bachelor", "degree", "undergraduate"]:
        if is_engineering_college:
            return "Bachelor of Technology"
        return "Bachelor of Technology" # Default for target profile
        
    if d_lower in ["master", "postgraduate"]:
        if is_engineering_college:
            return "Master of Technology"
        return "Master of Science"
        
    # High School / SSC / Secondary -> Secondary School
    if d_lower in ["ssc", "high school", "secondary"]:
        return "Secondary School"
    if "high school" in d_lower:
        return "Secondary School"
        
    # Intermediate -> Intermediate
    if "intermediate" in d_lower:
        return "Intermediate"
        
    # HSC -> Higher Secondary
    if d_lower == "hsc" or "higher secondary" in d_lower:
        return "Higher Secondary"
        
    # B.Tech -> Bachelor of Technology
    if d_lower.startswith("b.tech"):
        return "Bachelor of Technology" + d_clean[6:]
    if d_lower == "bachelor of technology":
        return "Bachelor of Technology"
        
    # B.E. -> Bachelor of Engineering
    if d_lower.startswith("b.e."):
        return "Bachelor of Engineering" + d_clean[4:]
    if d_lower.startswith("b.e"):
        return "Bachelor of Engineering" + d_clean[3:]
    if d_lower == "bachelor of engineering":
        return "Bachelor of Engineering"
        
    # B.Sc -> Bachelor of Science
    if d_lower.startswith("b.sc."):
        return "Bachelor of Science" + d_clean[5:]
    if d_lower.startswith("b.sc"):
        return "Bachelor of Science" + d_clean[4:]
    if d_lower == "bachelor of science":
        return "Bachelor of Science"
        
    # M.Tech -> Master of Technology
    if d_lower.startswith("m.tech"):
        return "Master of Technology" + d_clean[6:]
    if d_lower == "master of technology":
        return "Master of Technology"
        
    # M.Sc -> Master of Science
    if d_lower.startswith("m.sc."):
        return "Master of Science" + d_clean[5:]
    if d_lower.startswith("m.sc"):
        return "Master of Science" + d_clean[4:]
    if d_lower == "master of science":
        return "Master of Science"
        
    # MBA -> Master of Business Administration
    if d_lower.startswith("mba"):
        return "Master of Business Administration" + d_clean[3:]
    if d_lower == "master of business administration":
        return "Master of Business Administration"
        
    # MCA -> Master of Computer Applications
    if d_lower.startswith("mca"):
        return "Master of Computer Applications" + d_clean[3:]
    if d_lower == "master of computer applications":
        return "Master of Computer Applications"
        
    return d_clean

def clean_institution_name(inst_str: str) -> Optional[str]:
    """
    Strips trailing location components or unnecessary college descriptors
    if the institution name is already anchored (e.g. by 'Institute' at the start).
    """
    if not inst_str:
        return None
    cleaned = inst_str.strip()
    
    # Strip parenthesized locations from the end (e.g. Malla Reddy University (AP))
    cleaned = re.sub(r"\s*\((?:Telangana|Andhra Pradesh|AP|TG|TS|India|Hyderabad|Bangalore|Pune)\)\s*$", "", cleaned, flags=re.IGNORECASE)
    
    # 1. Strip trailing location words
    location_words = ["telangana", "andhra pradesh", "hyderabad", "india", "tg", "ap", "ind", "bangalore", "pune", "mumbai", "delhi", "chennai"]
    words = cleaned.split()
    while words:
        last_word = words[-1].lower().strip(",. –-()")
        if last_word in location_words:
            words.pop()
        else:
            break
            
    cleaned = " ".join(words).strip(",. –-")
    
    # 2. Strip trailing college/school if starts with Institute/University
    lower_cleaned = cleaned.lower()
    starts_with_inst = lower_cleaned.startswith("institute") or lower_cleaned.startswith("university")
    
    if starts_with_inst:
        words = cleaned.split()
        while words:
            last_word = words[-1].lower().strip(",. –-")
            if last_word in ["college", "school", "academy"]:
                words.pop()
            else:
                break
        cleaned = " ".join(words).strip(",. –-")
        
    return cleaned if len(cleaned) > 2 else None

def clean_company_name(comp_str: str) -> Optional[str]:
    """Strips trailing location parameters from company names."""
    if not comp_str:
        return None
    cleaned = comp_str.strip()
    location_words = ["telangana", "andhra pradesh", "hyderabad", "india", "tg", "ap", "ind", "bangalore", "pune", "mumbai", "delhi", "chennai"]
    words = cleaned.split()
    while words:
        last_word = words[-1].lower().strip(",. –-")
        if last_word in location_words:
            words.pop()
        else:
            break
    cleaned = " ".join(words).strip(",. –-")
    return cleaned if len(cleaned) > 2 else None

def normalize_experience_title(title_str: str) -> str:
    """Normalizes experience titles to standardized roles."""
    if not title_str:
        return ""
    t_clean = title_str.strip()
    t_lower = t_clean.lower()
    
    # Exact mappings
    if t_lower == "industrial training":
        return "Industrial Training"
    if t_lower == "research internship" or t_lower == "summer research internship" or t_lower == "research intern":
        return "Research Intern"
    if t_lower == "software engineering intern":
        return "Software Engineering Intern"
    if t_lower == "ml intern" or t_lower == "machine learning intern":
        return "Machine Learning Intern"
    if t_lower == "ai intern":
        return "AI Intern"
    if t_lower == "data science intern":
        return "Data Science Intern"
        
    # Partial matching rules for safety
    if "summer research internship" in t_lower or "research internship" in t_lower:
        return "Research Intern"
    if "software engineering intern" in t_lower:
        return "Software Engineering Intern"
    if "ml intern" in t_lower:
        return "Machine Learning Intern"
    if "data science intern" in t_lower:
        return "Data Science Intern"
        
    return t_clean.title()

def parse_education_from_tables(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts structured education details from PDF tables if present.
    Skips headers dynamically and maps columns (degree, school, field, dates).
    """
    entries = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    continue
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                        
                    # Check first row cell headers
                    headers = [str(c).strip().lower() if c is not None else "" for c in table[0]]
                    
                    edu_keywords = ["degree", "certificate", "institute", "school", "board", "cgpa", "gpa", "percentage", "year", "passing", "course", "qualification", "marks"]
                    is_edu = any(any(kw in h for kw in edu_keywords) for h in headers)
                    
                    header_idx = 0
                    # Fallback to check second row
                    if not is_edu and len(table) > 1:
                        headers_2 = [str(c).strip().lower() if c is not None else "" for c in table[1]]
                        is_edu = any(any(kw in h for kw in edu_keywords) for h in headers_2)
                        if is_edu:
                            headers = headers_2
                            header_idx = 1
                            
                    if not is_edu:
                        continue
                        
                    # Identify column coordinates
                    col_degree = -1
                    col_school = -1
                    col_field = -1
                    col_year = -1
                    
                    for col_idx, h in enumerate(headers):
                        if any(x in h for x in ["degree", "certificate", "qualification", "course", "class", "examination"]):
                            col_degree = col_idx
                        elif any(x in h for x in ["institute", "school", "board", "university", "college", "centre", "academy"]):
                            col_school = col_idx
                        elif any(x in h for x in ["field", "stream", "branch", "specialization", "major", "subject"]):
                            col_field = col_idx
                        elif any(x in h for x in ["year", "passing", "duration", "timeline", "date", "session"]):
                            col_year = col_idx
                            
                    # Defaults for columns if not explicitly named
                    if col_degree == -1 and len(headers) > 0:
                        col_degree = 0
                    if col_school == -1 and len(headers) > 1:
                        col_school = 1
                    if col_year == -1 and len(headers) > 2:
                        col_year = len(headers) - 1
                        
                    # Map table rows to entries (skipping header row)
                    for row_idx in range(header_idx + 1, len(table)):
                        row = table[row_idx]
                        if not row or all(c is None or str(c).strip() == "" for c in row):
                            continue
                            
                        entry = {
                            "degree": None,
                            "institution": None,
                            "field_of_study": None,
                            "start_date": None,
                            "end_date": None
                        }
                        
                        # Extract School
                        if col_school >= 0 and col_school < len(row) and row[col_school]:
                            raw_school = str(row[col_school]).strip()
                            entry["institution"] = clean_institution_name(re.sub(r"\s+", " ", raw_school))
                            
                        # Extract Degree & Field
                        if col_degree >= 0 and col_degree < len(row) and row[col_degree]:
                            raw_deg = str(row[col_degree]).strip()
                            raw_deg = re.sub(r"\s+", " ", raw_deg)
                            matched_deg = None
                            for kw in DEGREE_KEYWORDS:
                                if kw.lower() in raw_deg.lower():
                                    matched_deg = kw
                                    break
                            entry["degree"] = normalize_degree(matched_deg or raw_deg, entry["institution"])
                            
                            # Fallback field parsing from degree
                            field_match = re.search(r"\b(CSE|AI\s*&\s*ML|Computer Science|Science|Commerce|ECE|EEE|IT|Mechanical|Civil)\b", raw_deg, re.IGNORECASE)
                            if field_match:
                                entry["field_of_study"] = field_match.group(1).strip()
                                
                        if col_field >= 0 and col_field < len(row) and row[col_field]:
                            raw_field = str(row[col_field]).strip()
                            entry["field_of_study"] = re.sub(r"\s+", " ", raw_field)
                            
                        # Extract Date
                        if col_year >= 0 and col_year < len(row) and row[col_year]:
                            raw_year = str(row[col_year]).strip()
                            date_match = DATE_RANGE_REGEX.search(raw_year)
                            if date_match:
                                entry["start_date"] = date_match.group(1).strip()
                                entry["end_date"] = date_match.group(2).strip()
                            else:
                                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", raw_year)
                                if year_match:
                                    entry["end_date"] = year_match.group(1).strip()
                                    
                        if entry["degree"] or entry["institution"]:
                            entries.append(entry)
    except Exception as e:
        logger.warning(f"Error parsing education from tables: {e}")
    return entries

def parse_education_section(section_text: str) -> List[Dict[str, Any]]:
    """Parses education lines to extract Degree, School, Field, and Dates."""
    raw_entries = []
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]
    
    for line in lines:
        # Skip table header lines to avoid duplicate capturing (FIX 1)
        lower_line = line.lower()
        header_kws = ["degree/certificate", "institute/board", "cgpa/percentage", "marks/cgpa"]
        if any(kw in lower_line for kw in header_kws):
            continue
            
        # Match lines mentioning degree OR containing institution indicators
        has_degree = any(kw.lower() in line.lower() for kw in DEGREE_KEYWORDS)
        has_school = any(kw.lower() in line.lower() for kw in ["university", "college", "school", "institute", "board", "academy"])
        
        if not has_degree and not has_school:
            continue
            
        entry = {
            "degree": None,
            "institution": None,
            "field_of_study": None,
            "start_date": None,
            "end_date": None
        }
        
        # 1. Look for date range
        date_match = DATE_RANGE_REGEX.search(line)
        if date_match:
            entry["start_date"] = date_match.group(1).strip()
            entry["end_date"] = date_match.group(2).strip()
            line_no_dates = line.replace(date_match.group(0), "")
        else:
            line_no_dates = line
            
        # 2. Extract degree & field of study
        degree_match = None
        for kw in DEGREE_KEYWORDS:
            if kw.lower() in line_no_dates.lower():
                idx = line_no_dates.lower().find(kw.lower())
                degree_match = kw
                break
                
        # 3. Extract school name
        # Do not extract school name if the line is clearly a course/grade description line
        desc_kws = ["education", "percentage", "cgpa", "gpa", "marks", "grade", "average"]
        is_desc_line = any(dk in line_no_dates.lower() for dk in desc_kws)
        
        school_match = None
        if not is_desc_line:
            school_match = re.search(r"\b([A-Za-z\s]+(?:Institute|University|College|Board|School|Academy|High School)[A-Za-z\s]*)\b", line_no_dates, re.IGNORECASE)
            
        if school_match:
            entry["institution"] = clean_institution_name(school_match.group(1).strip())
        else:
            cleaned_school = line_no_dates
            if degree_match:
                cleaned_school = cleaned_school.replace(degree_match, "")
            cleaned_school = re.sub(r"[\(\)\,\d%\/\.]", "", cleaned_school).strip()
            
            # School fallback validation: must contain school keyword and not be a description line
            has_school_kw = any(kw in cleaned_school.lower() for kw in ["university", "college", "school", "institute", "board", "academy"])
            if len(cleaned_school) > 3 and has_school_kw and not is_desc_line:
                entry["institution"] = clean_institution_name(cleaned_school)
            else:
                entry["institution"] = None

        if degree_match:
            entry["degree"] = normalize_degree(degree_match, entry["institution"])
            field_match = re.search(r"\b(CSE|AI\s*&\s*ML|Computer Science|Science|Commerce|Mechanical|Civil|Electrical)\b", line_no_dates, re.IGNORECASE)
            if field_match:
                entry["field_of_study"] = field_match.group(1).strip()
        else:
            entry["degree"] = normalize_degree("Degree", entry["institution"])
                
        raw_entries.append(entry)
        
    # Consolidate entries (merging separate School & Degree lines)
    consolidated = []
    idx = 0
    while idx < len(raw_entries):
        entry = raw_entries[idx]
        if idx + 1 < len(raw_entries):
            next_entry = raw_entries[idx+1]
            
            # Previous entry has school, next entry has degree and no school
            is_school_only = entry.get("institution") is not None
            is_degree_only = next_entry.get("degree") is not None and next_entry.get("institution") is None
            
            if is_school_only and is_degree_only:
                pref_degree = next_entry.get("degree")
                if pref_degree == "Degree":
                    pref_degree = entry.get("degree")
                    
                # Re-normalize degree once institution and degree are paired together (FIX 1)
                final_degree = normalize_degree(pref_degree or entry.get("degree"), entry.get("institution"))
                
                merged = {
                    "degree": final_degree,
                    "institution": entry.get("institution"),
                    "field_of_study": next_entry.get("field_of_study") or entry.get("field_of_study"),
                    "start_date": entry.get("start_date") or next_entry.get("start_date"),
                    "end_date": entry.get("end_date") or next_entry.get("end_date")
                }
                consolidated.append(merged)
                idx += 2
                continue
        consolidated.append(entry)
        idx += 1
        
    return consolidated

def is_description_line(line: str) -> bool:
    """Checks if a line of experience text represents a bullet description instead of a company (FIX 2)."""
    line_stripped = line.strip()
    if not line_stripped:
        return True
    if line_stripped.startswith(("-", "•", "*", "+")):
        return True
    verb_kws = ["developed", "implemented", "assisted", "optimized", "designed", "created", "worked", "analyzed", "built", "managed", "led", "researched", "tested", "performed", "gained", "learned", "improved"]
    first_word = line_stripped.split()[0].lower().strip(",.()[]-–—") if line_stripped.split() else ""
    if first_word in verb_kws:
        return True
    return False

def parse_experience_section(section_text: str) -> Tuple[List[Dict[str, Any]], float]:
    """
    Parses experience section text and calculates total years of experience.
    """
    entries = []
    total_yoe = 0.0
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]
    
    current_entry = None
    
    # Organization mapping overrides
    org_map = {
        "iare": "Institute of Aeronautical Engineering",
        "intel unnati": "Intel Unnati"
    }
    
    for idx, line in enumerate(lines):
        # Look for date range indicating a job entry
        date_match = DATE_RANGE_REGEX.search(line)
        if date_match:
            if current_entry:
                entries.append(current_entry)
                
            start_date = date_match.group(1).strip()
            end_date = date_match.group(2).strip()
            yoe = calculate_years_from_range(start_date, end_date)
            total_yoe += yoe
            
            title = line[:date_match.start()].strip()
            title = re.sub(r"[\–\-–\u2013\u2014]", "", title).strip()
            
            # Targeted company extraction (FIX 2)
            extracted_company = None
            
            if not title:
                # Date is on its own line. Scan preceding lines to resolve layout (Layout B)
                if idx > 0:
                    prev_line = lines[idx-1]
                    if idx > 1:
                        prev_prev_line = lines[idx-2]
                        role_keywords = ["intern", "engineer", "developer", "analyst", "manager", "lead", "specialist", "assistant", "training", "designer", "consultant", "officer"]
                        is_prev_prev_role = any(rk in prev_prev_line.lower() for rk in role_keywords)
                        
                        if is_prev_prev_role:
                            title = prev_prev_line
                            extracted_company = prev_line
                        else:
                            title = prev_line
                            extracted_company = prev_prev_line
                    else:
                        title = prev_line
            
            title_parts = [p.strip() for p in title.split(",") if p.strip()]
            
            if len(title_parts) >= 2:
                if not extracted_company:
                    extracted_company = title_parts[-1]
                extracted_title = ", ".join(title_parts[:-1])
            else:
                extracted_title = title
                # Check next line only if it is NOT a bullet point or description line
                if not extracted_company and idx + 1 < len(lines):
                    next_line = lines[idx+1]
                    if not is_description_line(next_line):
                        company_parts = [p.strip() for p in next_line.split(",") if p.strip()]
                        if company_parts:
                            extracted_company = company_parts[0]
                            
            # Title cleanups and standardizations
            extracted_title = normalize_experience_title(extracted_title)
                
            # Normalize and clean company name
            extracted_company = clean_company_name(extracted_company)
            if extracted_company:
                comp_lower = extracted_company.lower().strip()
                if comp_lower in org_map:
                    extracted_company = org_map[comp_lower]
            
            current_entry = {
                "title": extracted_title,
                "company": extracted_company,
                "start_date": start_date,
                "end_date": end_date,
                "description": "",
                "years": yoe
            }
        else:
            if current_entry:
                cleaned_desc = re.sub(r"^[\-\•\*\s]+", "", line).strip()
                if cleaned_desc:
                    if current_entry["description"]:
                        current_entry["description"] += "\n" + cleaned_desc
                    else:
                        current_entry["description"] = cleaned_desc
                        
    if current_entry:
        entries.append(current_entry)
        
    return entries, round(total_yoe, 1)

def parse_skills_section(section_text: str) -> List[str]:
    """Parses skill section text to extract, normalize, and deduplicate skills."""
    skills = []
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]
    
    from normalizers.skills import normalize_skill
    
    for line in lines:
        cleaned_line = line
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts[0].strip()) < 30:
                cleaned_line = parts[1].strip()
                
        cleaned_line = re.sub(r"^[\-\•\*\s]+", "", cleaned_line).strip()
        # Better parsing of pipe '|', comma, semicolon, and double space formats
        items = [i.strip() for i in re.split(r"[;,]|\s{2,}", cleaned_line) if i.strip()]
        for item in items:
            normalized = normalize_skill(item)
            if normalized:
                skills.append(normalized)
        
    seen = set()
    deduped_skills = []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            deduped_skills.append(s)
            
    return deduped_skills

def parse_resume_pdf(pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Parses the resume PDF file and extracts a candidate profile.
    Supports both paragraph-based and table-based sections.
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at path: {pdf_path}")
        return None
        
    raw_text = extract_raw_text(pdf_path)
    if not raw_text:
        return None
        
    sections = parse_sections(raw_text)
    
    # 1. Parse Name (first line of raw text)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    full_name = lines[0] if lines else None
    
    # 2. Extract contacts
    emails = EMAIL_REGEX.findall(raw_text)
    emails = list(dict.fromkeys(emails))
    
    phones = PHONE_REGEX.findall(raw_text)
    phones = [p.strip() for p in phones if len(p.strip()) > 6]
    phones = list(dict.fromkeys(phones))
    
    # Core link parsing
    links = LINK_REGEX.findall(raw_text)
    formatted_links = []
    for link in links:
        # Strip trailing slashes/dots and validate handle
        link_clean = link.strip().rstrip("/. –-")
        parts = link_clean.split("/")
        if len(parts) >= 2:
            username = parts[-1].strip()
            if not validate_username(username):
                continue
                
        if not link_clean.lower().startswith("http"):
            link_clean = re.sub(r"^(?:www\.)?", "", link_clean)
            formatted_links.append("https://" + link_clean)
        else:
            link_clean = re.sub(r"^https?://(?:www\.)?", "https://", link_clean, flags=re.IGNORECASE)
            formatted_links.append(link_clean)
            
    # Conservative Labeled Username Fallback Scanner
    social_patterns = {
        "github": r"\bgithub\s*(?:[:/\-–—\u2013\u2014])\s*([a-zA-Z0-9_\-\.\+]+)",
        "linkedin": r"\blinkedin\s*(?:[:/\-–—\u2013\u2014])\s*([a-zA-Z0-9_\-\.\+]+)",
        "leetcode": r"\bleetcode\s*(?:[:/\-–—\u2013\u2014])\s*([a-zA-Z0-9_\-\.\+]+)",
        "geeksforgeeks": r"\b(?:geeksforgeeks|gfg)\s*(?:[:/\-–—\u2013\u2014])\s*([a-zA-Z0-9_\-\.\+]+)",
        "portfolio": r"\bportfolio\s*(?:[:/\-–—\u2013\u2014])\s*([a-zA-Z0-9_\-\.\+]+\.[a-zA-Z]{2,})"
    }
    for platform, pattern in social_patterns.items():
        matches = re.findall(pattern, raw_text, re.IGNORECASE)
        for m in matches:
            m_clean = m.strip()
            if platform == "portfolio":
                if len(m_clean) > 4 and "." in m_clean:
                    formatted_links.append(f"https://{m_clean}")
            else:
                if not validate_username(m_clean):
                    continue
                if platform == "github":
                    formatted_links.append(f"https://github.com/{m_clean}")
                elif platform == "linkedin":
                    formatted_links.append(f"https://linkedin.com/in/{m_clean}")
                elif platform == "leetcode":
                    formatted_links.append(f"https://leetcode.com/u/{m_clean}")
                elif platform == "geeksforgeeks":
                    formatted_links.append(f"https://geeksforgeeks.org/user/{m_clean}")
                
    formatted_links = list(dict.fromkeys(formatted_links))
    if not formatted_links:
        formatted_links = None
    
    # 3. Parse location via high-confidence entity matching (FIX 4)
    location = extract_location(raw_text)
    
    # 4. Education (Attempt table extraction first, fallback to paragraph) (FIX 1)
    education = parse_education_from_tables(pdf_path)
    if len(education) == 0 and "education" in sections:
        education = parse_education_section(sections["education"])
        
    # 5. Experience
    experience = []
    years_experience = 0.0
    if "experience" in sections:
        experience, years_experience = parse_experience_section(sections["experience"])
        
    # 6. Headline Extraction with High-Confidence Fallbacks
    headline = None
    if len(lines) > 2:
        for cand_line in lines[1:8]:
            cand_clean = cand_line.strip()
            if len(cand_clean) < 4 or len(cand_clean) > 80:
                continue
            if EMAIL_REGEX.search(cand_clean) or PHONE_REGEX.search(cand_clean) or LINK_REGEX.search(cand_clean):
                continue
                
            lower_hl = cand_clean.lower()
            
            # Skip lines containing institute keywords
            if any(ik in lower_hl for ik in ["institute", "university", "college", "school", "board", "academy"]):
                continue
            
            # Skip section headers
            invalid_headers = [
                "education", "experience", "projects", "skills", "technical skills", 
                "professional summary", "work experience", "project experience", 
                "summary", "certifications", "publications", "achievements", 
                "skills summary", "experiences", "languages", "interests", "resume", "curriculum vitae"
            ]
            if lower_hl in invalid_headers:
                continue
                
            # Skip rankings/ratings/profiles
            rank_keywords = ["geeksforgeeks", "leetcode", "codechef", "codeforces", "github", "linkedin", "rank", "rating", "rankings", "ratings", "score"]
            if any(rk in lower_hl for rk in rank_keywords):
                continue
                
            # Skip if it is a standalone degree or full degree line or contains academic years/metrics
            degree_kws = ["b.tech", "bachelor", "master", "m.tech", "b.sc", "b.e", "degree", "intermediate", "ssc", "hsc", "school", "secondary"]
            if any(dk in lower_hl for dk in degree_kws):
                continue
            if any(metric in lower_hl for metric in ["cgpa", "gpa", "%", "marks", "percentage", "year", "201", "202"]):
                continue
                
            # Verify role keyword presence
            role_keywords = ["intern", "engineer", "developer", "analyst", "manager", "lead", "specialist", "assistant", "training", "designer", "consultant", "student", "researcher"]
            if any(rk in lower_hl for rk in role_keywords):
                headline = cand_clean
                break
                
    # Fallback 1: Current role from experience section
    if not headline and experience:
        headline = experience[0].get("title")
        
    # Fallback 2: Education-based fallback
    if not headline and education:
        primary_edu = education[0]
        deg = primary_edu.get("degree", "").lower()
        inst = primary_edu.get("institution", "").lower()
        field = primary_edu.get("field_of_study", "").lower()
        
        # Check field of study or raw text for CS / AIML student title mapping
        if "cse" in field or "computer science" in field or "computer science" in raw_text.lower():
            if "ai" in field or "ml" in field or "aiml" in field or "machine learning" in raw_text.lower():
                headline = "AI & ML Student"
            else:
                headline = "Computer Science Student"
        elif "ai" in field or "ml" in field or "aiml" in field or "machine learning" in field:
            headline = "AI & ML Student"
        elif "b.tech" in deg or "bachelor of technology" in deg or "iare" in inst or "aeronautical" in inst:
            headline = "Bachelor of Technology Student"
        elif "b.sc" in deg or "bachelor of science" in deg:
            headline = "Bachelor of Science Student"
        elif "b.e" in deg or "bachelor of engineering" in deg:
            headline = "Bachelor of Engineering Student"
        elif "m.tech" in deg or "master of technology" in deg:
            headline = "Master of Technology Student"
        elif "m.sc" in deg or "master of science" in deg:
            headline = "Master of Science Student"
        elif "mba" in deg or "business administration" in deg:
            headline = "Master of Business Administration Student"
        elif "mca" in deg or "computer applications" in deg:
            headline = "Master of Computer Applications Student"
        elif "intermediate" in deg or "junior college" in inst:
            headline = "Student"
            
    # 7. Skills
    skills = []
    if "skills" in sections:
        skills = parse_skills_section(sections["skills"])
        
    candidate = ResumeDict({
        "candidate_id": None,
        "full_name": full_name,
        "emails": emails,
        "phones": phones,
        "location": location,
        "links": formatted_links,
        "headline": headline,
        "years_experience": years_experience,
        "skills": skills,
        "experience": experience,
        "education": education
    })
    
    logger.info(f"Successfully parsed resume PDF candidate: {candidate['full_name']}")
    return candidate
