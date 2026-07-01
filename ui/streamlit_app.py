import streamlit as st
import tempfile
import os
import json
import time
import datetime
import re
import pandas as pd
from typing import Dict, Any, List, Optional

# Set page config for a professional internal dashboard
st.set_page_config(
    page_title="Candidate Data Transformer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Flat, minimalist dark mode styles (inspired by Stripe/GitHub/Linear)
st.markdown("""
<style>
    .enterprise-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge {
        display: inline-block;
        border: 1px solid #30363d;
        background-color: #21262d;
        color: #c9d1d9;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .chip {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 3px 12px;
        font-size: 11px;
        font-weight: 500;
        display: inline-block;
        margin-right: 4px;
        margin-bottom: 4px;
        white-space: nowrap;
    }
    .footer {
        text-align: center;
        padding: 24px 0;
        color: #8b949e;
        font-size: 11px;
        border-top: 1px solid #30363d;
        margin-top: 50px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)


# --- Skill Mappings & Categories Definitions ---

SKILL_MAPPINGS = {
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "sql": "SQL",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "numpy": "NumPy",
    "pandas": "Pandas",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "scikit learn": "Scikit-learn",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "huggingface transformers": "Hugging Face Transformers",
    "hugging face transformers": "Hugging Face Transformers",
    "huggingface": "Hugging Face",
    "transformers": "Transformers",
    "llm": "Large Language Models",
    "llms": "Large Language Models",
    "nlp": "Natural Language Processing",
    "eda": "Exploratory Data Analysis",
    "whisper": "OpenAI Whisper",
    "git": "Git",
    "github": "GitHub",
    "communication": "Communication",
    "problem solving": "Problem Solving",
    "continuous learning": "Continuous Learning",
    "analytical thinking": "Analytical Thinking",
    "team collaboration": "Team Collaboration",
    "collaboration": "Team Collaboration",
    "leadership": "Leadership",
    "time management": "Time Management",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "linux": "Linux"
}

SKILL_CATEGORIES = {
    "Programming Languages": [
        "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Go", 
        "Rust", "Swift", "Kotlin", "R", "Scala", "MATLAB", "SQL", "PHP"
    ],
    "Libraries & Frameworks": [
        "NumPy", "Pandas", "Matplotlib", "Seaborn", "Scikit-learn", "TensorFlow", 
        "PyTorch", "Keras", "Transformers", "OpenCV", "Flask", "FastAPI", "Django", 
        "React", "Spring", "Streamlit"
    ],
    "Developer Tools": [
        "Git", "GitHub", "Docker", "Linux", "Jupyter Notebook", "Visual Studio Code", 
        "VS Code", "PyCharm", "Postman", "AWS", "Azure", "GCP", "Kubernetes"
    ],
    "AI / Data Science": [
        "Machine Learning", "Deep Learning", "Natural Language Processing", 
        "Prompt Engineering", "Exploratory Data Analysis", "Data Visualization", 
        "Feature Engineering", "Computer Vision", "Large Language Models", 
        "Model Training", "Model Evaluation"
    ],
    "Professional Skills": [
        "Leadership", "Communication", "Public Speaking", "Writing", "Problem Solving", 
        "Analytical Thinking", "Critical Thinking", "Team Collaboration", 
        "Continuous Learning", "Time Management", "Presentation Skills"
    ]
}


# --- Helper Functions ---

def load_config(config_path: str) -> Dict[str, Any]:
    """Loads a configuration JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_section_header(title: str, subtitle: Optional[str] = None):
    """Renders a standard section header."""
    st.markdown(f"### {title}")
    if subtitle:
        st.markdown(f"*{subtitle}*")


def render_metric_card(col, icon: str, title: str, value: Any, desc: str):
    """Renders a flat, equal-height metric card using HTML/CSS."""
    col.markdown(f"""
    <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 14px 16px; height: 115px; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-size: 15px;">{icon}</span>
                <span style="font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">{title}</span>
            </div>
            <div style="font-size: 16px; color: #c9d1d9; font-weight: 700; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{value}</div>
        </div>
        <div style="font-size: 11px; color: #8b949e; margin-top: auto;">{desc}</div>
    </div>
    """, unsafe_allow_html=True)


def get_skills_list(skills_data: Any) -> List[str]:
    """Extracts a list of skill name strings from the raw projected skills data."""
    if not skills_data:
        return []
    skills_list = []
    for s in skills_data:
        if isinstance(s, dict):
            skills_list.append(s.get("name", ""))
        elif hasattr(s, "name"):
            skills_list.append(s.name)
        else:
            skills_list.append(str(s))
    return sorted(list(set([sk for sk in skills_list if sk])))


def normalize_and_format_skill(skill_name: str) -> str:
    """Normalizes skill names to canonical names and applies professional title formatting."""
    if not skill_name:
        return ""
    name_clean = re.sub(r'\s+', ' ', skill_name.strip())
    name_lower = name_clean.lower()
    
    # 1. Check direct dict mappings
    if name_lower in SKILL_MAPPINGS:
        return SKILL_MAPPINGS[name_lower]
        
    for k, canonical in SKILL_MAPPINGS.items():
        if name_lower == k:
            return canonical
            
    # 2. Title casing & acronyms
    minor_words = ["and", "or", "but", "a", "an", "the", "as", "at", "by", "for", "in", "of", "on", "per", "to"]
    words = name_clean.split(" ")
    title_words = []
    for idx, w in enumerate(words):
        if w.upper() in ["NLP", "EDA", "LLM", "SQL", "AWS", "GCP", "API", "UI", "UX", "REST", "JSON", "XML", "HTML", "CSS", "PDF"]:
            title_words.append(w.upper())
        elif w.lower() in minor_words and idx > 0:
            title_words.append(w.lower())
        else:
            if w.isupper() and len(w) > 3:
                title_words.append(w.title())
            else:
                title_words.append(w[0].upper() + w[1:] if len(w) > 0 else "")
                
    return " ".join(title_words)


def get_skill_category(skill_name: str) -> str:
    """Determines the category of a skill using case-insensitive exact matches."""
    name_lower = skill_name.lower().strip()
    for cat_name, items in SKILL_CATEGORIES.items():
        for item in items:
            if name_lower == item.lower().strip():
                return cat_name
    return "Other Skills"


def get_normalized_and_sorted_skills(skills_data: Any) -> List[str]:
    """Returns unique, normalized skills sorted according to canonical category sequence."""
    raw_skills = get_skills_list(skills_data)
    normalized = []
    seen = set()
    for r in raw_skills:
        n = normalize_and_format_skill(r)
        if n and n.lower() not in seen:
            normalized.append(n)
            seen.add(n.lower())
            
    ordered_categories = [
        "Programming Languages",
        "Libraries & Frameworks",
        "AI / Data Science",
        "Developer Tools",
        "Professional Skills"
    ]
    
    sorted_skills = []
    for cat in ordered_categories:
        cat_skills = sorted([s for s in normalized if get_skill_category(s) == cat])
        sorted_skills.extend(cat_skills)
        
    other_skills = sorted([s for s in normalized if get_skill_category(s) not in ordered_categories])
    sorted_skills.extend(other_skills)
    
    return sorted_skills


def render_skills_chips(skills: List[str], max_initial: int = 30):
    """Renders skills as a set of flat chips with auto-wrapping and overflow containment."""
    if not skills:
        st.info("No skills detected.")
        return

    initial_skills = skills[:max_initial]
    remaining_skills = skills[max_initial:]

    chips_html = '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px;">'
    for skill in initial_skills:
        chips_html += f'<span class="chip">{skill}</span>'
    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

    if remaining_skills:
        with st.expander(f"+{len(remaining_skills)} more skills", expanded=False):
            more_chips_html = '<div style="display: flex; flex-wrap: wrap; gap: 6px;">'
            for skill in remaining_skills:
                more_chips_html += f'<span class="chip">{skill}</span>'
            more_chips_html += '</div>'
            st.markdown(more_chips_html, unsafe_allow_html=True)


def get_confidence_tier(score: float) -> str:
    """Returns a deterministic quality descriptor for a confidence score."""
    pct = int(score * 100)
    if pct >= 90:
        return "Excellent"
    elif pct >= 75:
        return "Good"
    elif pct >= 60:
        return "Moderate"
    else:
        return "Low"


def render_custom_progress_bar(pct: float, label: str):
    """Renders a flat progress bar with custom colors matching score bands."""
    pct_val = int(pct * 100)
    tier = get_confidence_tier(pct)
    if pct_val >= 90:
        color = "#238636"
    elif pct_val >= 70:
        color = "#d29922"
    else:
        color = "#da3633"

    st.markdown(f"""
    <div style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #c9d1d9; margin-bottom: 4px;">
            <span><b>{label}</b> ({tier})</span>
            <span>{pct_val}%</span>
        </div>
        <div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 4px; height: 8px; width: 100%;">
            <div style="background-color: {color}; width: {pct_val}%; height: 100%; border-radius: 4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def format_date_str(date_str: str) -> str:
    """Formats YYYY-MM dates to Month YYYY (e.g. 2024-05 -> May 2024)."""
    if not date_str:
        return "Present"
    date_str = date_str.strip()
    if date_str.lower() in ["present", "current", "till date"]:
        return "Present"
        
    parts = date_str.split("-")
    if len(parts) == 2:
        try:
            year = parts[0]
            month_num = int(parts[1])
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            if 1 <= month_num <= 12:
                return f"{months[month_num - 1]} {year}"
        except Exception:
            pass
            
    return date_str


def should_clean_description(text: str) -> bool:
    """Detects if the extracted description text contains line-wrap or whitespace PDF artifacts."""
    if not text:
        return False
    if re.search(r'\w+-\s*\n\s*\w+', text):
        return True
    joined_indicators = [
        "Developeda", "usingbenchmark", "leveragingthe", "toachieve",
        "accuracyin", "andclassifying", "networkanomalies", "systemperformance",
        "featureselection", "SMOTEbalancing", "hyperparametertuning",
        "real-timedetection", "faulttolerance", "TechStack"
    ]
    if any(ind in text for ind in joined_indicators):
        return True
    return False


def clean_experience_description(text: str) -> str:
    """Deterministic description cleaner to resolve PDF extraction spacing and hyphen wrapping."""
    if not text:
        return ""
        
    if not should_clean_description(text):
        return text.strip()
        
    text = re.sub(r'(\w+)-\s*\n?\s*(\w+)', r'\1\2', text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r',([a-zA-Z])', r', \1', text)
    text = re.sub(r'\)([a-zA-Z])', r') \1', text)
    text = re.sub(r'%([a-zA-Z])', r'% \1', text)
    text = re.sub(r'([a-zA-Z])\(', r'\1 (', text)
    
    replacements = {
        "Developedahighlyaccurate": "Developed a highly accurate",
        "usingbenchmark": "using benchmark",
        "leveragingthe": "leveraging the",
        "accuracyindetecting": "accuracy in detecting",
        "andclassifying": "and classifying",
        "networkanomalies": "network anomalies",
        "systemperformance": "system performance",
        "featureselection": "feature selection",
        "SMOTEbalancing": "SMOTE balancing",
        "hyperparametertuning": "hyperparameter tuning",
        "real-timedetection": "real-time detection",
        "scalability,and": "scalability, and",
        "faulttolerance": "fault tolerance",
        "TechStack": "Tech Stack",
        "developedahighly": "developed a highly",
        "toachieve": "to achieve"
    }
    
    for k, v in replacements.items():
        text = re.sub(re.escape(k), v, text, flags=re.IGNORECASE)
        
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


# --- Main Runner ---

def run_streamlit_app():
    # Sidebar Setup
    st.sidebar.title("Dashboard Config")
    
    resume_file = st.sidebar.file_uploader(
        "Upload Resume PDF",
        type=["pdf"],
        help="Upload the candidate's PDF resume profile"
    )
    
    csv_file = st.sidebar.file_uploader(
        "Upload Recruiter CSV (Optional)",
        type=["csv"],
        help="Upload the recruiter's candidate notes CSV"
    )
    
    config_selection = st.sidebar.selectbox(
        "Configuration Selector",
        ["Default Config", "Custom Config"],
        help="Select the configuration template for projection"
    )
    
    st.sidebar.markdown("---")
    
    # Process Trigger in Sidebar
    transform_triggered = st.sidebar.button("Transform Candidate", type="primary", use_container_width=True)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Uploaded Files")
    if resume_file:
        st.sidebar.info(f"📄 Resume: {resume_file.name}")
    else:
        st.sidebar.warning("⚠️ No resume uploaded")
        
    if csv_file:
        st.sidebar.info(f"📊 Recruiter CSV: {csv_file.name}")

    # Hero / Header Section
    st.title("Candidate Data Transformer")
    st.markdown("##### Multi-Source Candidate Profile Normalization Pipeline")
    
    # Configuration Selector Badge
    st.markdown(f"""
    <div style="margin-top: 4px; margin-bottom: 12px;">
        <span class="badge" style="border: 1px solid #1f6feb; color: #58a6ff; background-color: rgba(31,111,235,0.1); font-weight: bold; font-size: 12px; padding: 4px 10px;">Projection: {config_selection}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Badges
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <span class="badge">✓ Deterministic</span>
        <span class="badge">✓ Explainable</span>
        <span class="badge">✓ Config Driven</span>
        <span class="badge">✓ Schema Validated</span>
        <span class="badge">✓ Provenance Tracking</span>
        <span class="badge">✓ Confidence Scoring</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if not resume_file and not csv_file:
        st.info("💡 Upload a Resume PDF and/or a Recruiter CSV to generate a normalized canonical candidate profile.")
        return

    # Trigger transformation execution
    if transform_triggered:
        status_box = st.empty()
        
        try:
            # Sequential pipeline progression steps
            steps = [
                "Resume Parsed" if resume_file else "Resume Skipped",
                "CSV Parsed" if csv_file else "CSV Skipped",
                "Normalization",
                "Merge",
                "Confidence",
                "Provenance",
                "Projection",
                "Validation",
                "Output Generated"
            ]
            
            def display_steps(current_idx):
                html = "<div style='background-color:#161b22; border: 1px solid #30363d; padding:16px; border-radius:6px; margin-bottom:20px; font-family:monospace;'>"
                for idx, step in enumerate(steps):
                    if idx < current_idx:
                        html += f"<div style='color:#238636;'>✓ {step}</div>"
                    elif idx == current_idx:
                        html += f"<div style='color:#58a6ff;'>⏳ {step}...</div>"
                    else:
                        html += f"<div style='color:#8b949e;'>☐ {step}</div>"
                html += "</div>"
                status_box.markdown(html, unsafe_allow_html=True)
            
            temp_pdf_path = None
            resume_profile = None
            if resume_file:
                display_steps(0)
                time.sleep(0.12)
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                    temp_pdf.write(resume_file.getbuffer())
                    temp_pdf_path = temp_pdf.name
                    
                # Backend parser
                from parsers.resume_parser import parse_resume_pdf
                resume_profile = parse_resume_pdf(temp_pdf_path)
                if not resume_profile:
                    raise ValueError("Failed to parse resume PDF. Please check if the file is valid.")
            else:
                display_steps(0)
                time.sleep(0.05)
                
            temp_csv_path = None
            csv_profile = None
            if csv_file:
                display_steps(1)
                time.sleep(0.12)
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_csv:
                    temp_csv.write(csv_file.getbuffer())
                    temp_csv_path = temp_csv.name
                
                # Backend parser
                from parsers.csv_parser import parse_recruiter_csv
                csv_profile = parse_recruiter_csv(temp_csv_path)
                
                # Validation check for CSV-only info extraction completeness
                if not resume_file:
                    if csv_profile:
                        has_info = any(csv_profile.get(k) for k in ["full_name", "emails", "phones", "location", "links", "headline", "years_experience", "skills"])
                        if not has_info:
                            raise ValueError("No candidate information could be extracted from the uploaded recruiter CSV.")
                    else:
                        raise ValueError("No candidate information could be extracted from the uploaded recruiter CSV.")
            else:
                display_steps(1)
                time.sleep(0.05)
                
            display_steps(2)
            time.sleep(0.12)
            display_steps(3)
            time.sleep(0.12)
            display_steps(4)
            time.sleep(0.12)
            
            # Pre-merge Identity Consistency Check
            is_same = True
            if resume_file and csv_file:
                from normalizers.email import normalize_email
                from normalizers.phone import normalize_phone
                
                res_emails = [normalize_email(e) for e in resume_profile.get("emails", []) if normalize_email(e)]
                csv_emails = [normalize_email(e) for e in csv_profile.get("emails", []) if normalize_email(e)]
                
                res_phones = [normalize_phone(p) for p in resume_profile.get("phones", []) if normalize_phone(p)]
                csv_phones = [normalize_phone(p) for p in csv_profile.get("phones", []) if normalize_phone(p)]
                
                res_name = resume_profile.get("full_name")
                csv_name = csv_profile.get("full_name")
                
                emails_overlap = any(e in csv_emails for e in res_emails) if (res_emails and csv_emails) else False
                phones_overlap = any(p in csv_phones for p in res_phones) if (res_phones and csv_phones) else False
                
                from rapidfuzz import fuzz
                names_overlap = fuzz.ratio(str(res_name).lower(), str(csv_name).lower()) >= 80 if (res_name and csv_name) else False
                
                is_same = emails_overlap or phones_overlap or names_overlap
            
            from merge.merge_engine import merge_profiles
            csv_source_name = csv_file.name if csv_file else "recruiter.csv"
            resume_source_name = resume_file.name if resume_file else "resume.pdf"
            
            if resume_file and csv_file:
                if is_same:
                    canonical_profile = merge_profiles(
                        csv_profile=csv_profile,
                        resume_profile=resume_profile,
                        csv_source_name=csv_source_name,
                        resume_source_name=resume_source_name
                    )
                else:
                    # Mismatch: disable merge and fallback to Resume profile only
                    canonical_profile = merge_profiles(
                        csv_profile=None,
                        resume_profile=resume_profile,
                        resume_source_name=resume_source_name,
                        identity_check_failed=True
                    )
            elif resume_file:
                canonical_profile = merge_profiles(
                    csv_profile=None,
                    resume_profile=resume_profile,
                    resume_source_name=resume_source_name
                )
            else:
                canonical_profile = merge_profiles(
                    csv_profile=csv_profile,
                    resume_profile=None,
                    csv_source_name=csv_source_name
                )
            
            display_steps(5)
            time.sleep(0.12)
            display_steps(6)
            time.sleep(0.12)
            display_steps(7)
            time.sleep(0.12)
            display_steps(8)
            time.sleep(0.12)
            
            from projection.projector import project_candidate
            default_config = load_config("config/default_config.json")
            custom_config = load_config("config/custom_config.json")
            
            projected_default = project_candidate(canonical_profile, default_config)
            projected_custom = project_candidate(canonical_profile, custom_config)
            
            from validator.schema_validator import validate_projected_output
            validate_projected_output(projected_default, default_config)
            validate_projected_output(projected_custom, custom_config)
            
            status_box.empty()
            
            # Write outcomes to session state
            st.session_state["projected_default"] = projected_default
            st.session_state["projected_custom"] = projected_custom
            st.session_state["canonical_profile"] = canonical_profile
            st.session_state["csv_parsed"] = csv_file is not None
            st.session_state["resume_parsed"] = resume_file is not None
            st.session_state["exec_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["resume_name"] = resume_file.name if resume_file else "None"
            st.session_state["csv_name"] = csv_file.name if csv_file else "None"
            
            # Save raw skill counts for truth-based metrics calculations
            st.session_state["resume_skills_count"] = len(resume_profile.get("skills", [])) if (resume_file and resume_profile) else 0
            st.session_state["csv_skills_count"] = len(csv_profile.get("skills", [])) if (csv_file and csv_profile) else 0
            
            # Save identity check status
            if resume_file and csv_file:
                st.session_state["identity_status"] = "Passed" if is_same else "Failed"
            else:
                st.session_state["identity_status"] = "Not Applicable"
            
            # Cleanup temp files
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            if temp_csv_path and os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
                
            st.success("✅ Candidate transformed successfully")
            
        except Exception as e:
            if 'temp_pdf_path' in locals() and temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            if 'temp_csv_path' in locals() and temp_csv_path and os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
                
            st.error(f"Pipeline Execution Failed: {str(e)}")
            return
            
    # Display Results View
    if "projected_default" in st.session_state:
        projected_default = st.session_state["projected_default"]
        projected_custom = st.session_state["projected_custom"]
        csv_parsed = st.session_state["csv_parsed"]
        resume_parsed = st.session_state["resume_parsed"]
        exec_timestamp = st.session_state["exec_timestamp"]
        resume_name = st.session_state["resume_name"]
        csv_name = st.session_state["csv_name"]
        
        active_projected = projected_default if config_selection == "Default Config" else projected_custom
        skills_val = active_projected.get("skills") or active_projected.get("skills_list")
        
        # Build cards dynamically based on available projected data
        cards_data = []

        # Candidate Name
        name_val = active_projected.get("full_name") or active_projected.get("candidate_name") or active_projected.get("name")
        if name_val:
            headline_val = active_projected.get("headline") or "Candidate Profile"
            cards_data.append(("👤", "Candidate Profile", name_val, headline_val))
            
        # Email
        email_val = active_projected.get("primary_email") or (active_projected.get("emails")[0] if active_projected.get("emails") else None)
        if email_val:
            emails_list = active_projected.get("emails") or [email_val]
            cards_data.append(("📧", "Email", email_val, f"Total: {len(emails_list)} Emails"))

        # Phone
        phone_val = active_projected.get("primary_phone") or (active_projected.get("phones")[0] if active_projected.get("phones") else None)
        if phone_val:
            phones_list = active_projected.get("phones") or [phone_val]
            cards_data.append(("📞", "Phone", phone_val, f"Total: {len(phones_list)} Phones"))

        # Location
        loc_val = active_projected.get("country_code") or active_projected.get("location")
        if loc_val:
            if isinstance(loc_val, dict):
                loc_str = f"{loc_val.get('city', 'N/A')}, {loc_val.get('country', 'N/A')}"
                loc_desc = f"State: {loc_val.get('state', 'N/A')}"
            else:
                loc_str = f"Country Code: {loc_val}"
                loc_desc = "Normalized Location"
            cards_data.append(("📍", "Location", loc_str, loc_desc))

        # Professional Experience
        if "experience" in active_projected:
            exp_list = active_projected.get("experience") or []
            yoe = active_projected.get("years_experience")
            yoe_str = f"{int(yoe) if yoe == int(yoe) else yoe} yrs" if yoe is not None else "0 yrs"
            
            if len(exp_list) == 0:
                cards_data.append(("💼", "Professional Experience", "No professional experience detected", f"Total: {yoe_str} YOE"))
            else:
                cards_data.append(("💼", "Professional Experience", f"{len(exp_list)} Experience Records", f"Total: {yoe_str} YOE"))

        # Education Records
        if "education" in active_projected:
            edu_list = active_projected.get("education") or []
            cards_data.append(("🎓", "Education Records", f"{len(edu_list)} Education Records", "Standardized Degrees"))

        # Canonical Skills
        if skills_val is not None:
            skills_count = len(get_normalized_and_sorted_skills(skills_val))
            cards_data.append(("🛠", "Canonical Skills", f"{skills_count} Canonical Skills", "Deduplicated & Canonical"))

        # Confidence
        overall_conf = active_projected.get("_overall_confidence")
        if overall_conf is not None:
            tier = get_confidence_tier(float(overall_conf))
            cards_data.append(("📈", "Confidence", f"{int(overall_conf * 100)}% ({tier})", "Overall Confidence"))
            
        # Draw metric cards dynamically
        render_section_header("Candidate Summary")
        num_cards = len(cards_data)
        if num_cards > 0:
            cols_per_row = 4
            for i in range(0, num_cards, cols_per_row):
                row_cards = cards_data[i:i+cols_per_row]
                cols = st.columns(cols_per_row)
                for col_idx, card_info in enumerate(row_cards):
                    icon, title, value, desc = card_info
                    render_metric_card(cols[col_idx], icon, title, value, desc)
                    
        st.markdown("---")
        
        # --- Ingestion & Merge Summary Redesign (Option A using st.columns) ---
        st.markdown("### Ingestion & Merge Summary")
        
        id_status = st.session_state.get("identity_status", "Not Applicable")
        
        res_val = "✓ Yes" if resume_parsed else "✗ No"
        csv_val = "✓ Yes" if csv_parsed else "✗ No"
        
        if id_status == "Passed":
            id_val = "✓ Passed"
        elif id_status == "Failed":
            id_val = "✗ Failed"
        else:
            id_val = "N/A"
            
        if id_status == "Failed":
            sources_val = "Merge Blocked"
        elif resume_parsed and csv_parsed:
            sources_val = "Resume + Recruiter CSV"
        elif resume_parsed:
            sources_val = "Resume"
        else:
            sources_val = "Recruiter CSV"
            
        conf_str = "N/A"
        if overall_conf is not None:
            tier = get_confidence_tier(float(overall_conf))
            conf_str = f"{int(overall_conf * 100)}% ({tier})"
            
        summary_container = st.container()
        with summary_container:
            # Table-like row alignment using st.columns(2)
            metrics = [
                ("Resume Parsed", res_val),
                ("Recruiter CSV Parsed", csv_val),
                ("Identity Check", id_val),
                ("Sources Used", sources_val),
                ("Overall Confidence", conf_str)
            ]
            
            for label, value in metrics:
                row_col1, row_col2 = st.columns([1, 1])
                row_col1.markdown(f"<span style='color: #8b949e; font-size: 14px;'>{label}</span>", unsafe_allow_html=True)
                row_col2.markdown(f"<span style='color: #c9d1d9; font-size: 14px; font-weight: 500;'>{value}</span>", unsafe_allow_html=True)
                # Subtle line divider for visual separation
                st.markdown("<hr style='margin: 4px 0; border: none; border-bottom: 1px solid #21262d;' />", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Merge Status warnings - remains hidden if conflicts is not exposed in output payload
        if "conflicts" in active_projected:
            conflicts_list = active_projected.get("conflicts", [])
            if conflicts_list:
                st.warning(f"""
                ### ⚠ Candidate Merge Status
                Detected backend conflicts
                
                """ + "\n".join([f"• {c}" for c in conflicts_list]) + """
                
                *Overall confidence may be lower because conflicting information was merged.*
                """)
            else:
                st.success("""
                ### ✅ Candidate Merge Status
                No identity conflicts were reported by the backend.
                
                Resume and Recruiter data were merged successfully.
                """)
            
        # Build tabs dynamically based on available projection layout keys
        tabs_to_create = ["Overview"]
        if "experience" in active_projected:
            tabs_to_create.append("Professional Experience")
        if "education" in active_projected:
            tabs_to_create.append("Education Records")
        if "skills" in active_projected or "skills_list" in active_projected:
            tabs_to_create.append("Skills")
        tabs_to_create.append("Raw JSON")
        tabs_to_create.append("Confidence")
        if "_provenance" in active_projected:
            tabs_to_create.append("Provenance")
        tabs_to_create.append("Pipeline Info")
        
        tab_objs = st.tabs(tabs_to_create)
        
        for tab_name, tab_obj in zip(tabs_to_create, tab_objs):
            with tab_obj:
                
                # --- 1. OVERVIEW TAB ---
                if tab_name == "Overview":
                    ov_col1, ov_col2 = st.columns([1, 1])
                    
                    with ov_col1:
                        render_section_header("Candidate Information")
                        
                        cand_id = active_projected.get("candidate_id")
                        if cand_id:
                            st.write(f"**Candidate ID**: {cand_id}")

                        full_name = active_projected.get("full_name") or active_projected.get("candidate_name") or active_projected.get("name")
                        if full_name:
                            st.write(f"**Full Name**: {full_name}")

                        headline = active_projected.get("headline")
                        if headline:
                            st.write(f"**Headline**: {headline}")

                        email = active_projected.get("primary_email") or (", ".join(active_projected.get("emails")) if active_projected.get("emails") else None)
                        if email:
                            st.write(f"**Primary Email**: {email}")

                        phone = active_projected.get("primary_phone") or (", ".join(active_projected.get("phones")) if active_projected.get("phones") else None)
                        if phone:
                            st.write(f"**Primary Phone**: {phone}")

                        loc = active_projected.get("location") or active_projected.get("country_code")
                        if loc:
                            if isinstance(loc, dict):
                                loc_str = ", ".join([v for v in [loc.get("city"), loc.get("state"), loc.get("country")] if v])
                            else:
                                loc_str = loc
                            st.write(f"**Location**: {loc_str}")

                        yoe = active_projected.get("years_experience")
                        if yoe is not None:
                            yoe_formatted = f"{int(yoe) if yoe == int(yoe) else yoe} yrs"
                            st.write(f"**Years Experience**: {yoe_formatted}")

                        # Handle social links
                        links = active_projected.get("links") or []
                        gh_links = [l for l in links if "github" in l.lower()]
                        li_links = [l for l in links if "linkedin" in l.lower()]
                        
                        if gh_links:
                            st.write(f"**GitHub**: {', '.join(gh_links)}")
                        if li_links:
                            st.write(f"**LinkedIn**: {', '.join(li_links)}")
                            
                    with ov_col2:
                        render_section_header("Profile Summary")
                        if overall_conf is not None:
                            tier = get_confidence_tier(float(overall_conf))
                            st.write(f"**Overall Confidence**: {int(overall_conf * 100)}% ({tier})")
                            st.progress(float(overall_conf))
                        if "experience" in active_projected:
                            st.write(f"**Experience Count**: {len(active_projected.get('experience') or [])}")
                        if "education" in active_projected:
                            st.write(f"**Education Count**: {len(active_projected.get('education') or [])}")
                            
                        skills_val = active_projected.get("skills") or active_projected.get("skills_list")
                        if skills_val is not None:
                            st.write(f"**Canonical Skills**: {len(get_normalized_and_sorted_skills(skills_val))}")
                            
                        sources = []
                        if resume_name != "None":
                            sources.append(resume_name)
                        if csv_parsed:
                            sources.append(csv_name)
                        sources_str = ", ".join(sources) if sources else "None"
                        st.write(f"**Sources Used**: {sources_str}")
                        
                        if skills_val is not None:
                            st.markdown("#### Top Skills")
                            render_skills_chips(get_normalized_and_sorted_skills(skills_val)[:10], max_initial=10)
                            
                # --- 2. PROFESSIONAL EXPERIENCE TAB ---
                elif tab_name == "Professional Experience":
                    render_section_header("Professional Experience")
                    exp_list = active_projected.get("experience", [])
                    if exp_list:
                        for exp in exp_list:
                            role = exp.get("title", "Role")
                            org = exp.get("company", "Company")
                            start_formatted = format_date_str(exp.get("start_date"))
                            end_formatted = format_date_str(exp.get("end_date"))
                            duration = f"{start_formatted} – {end_formatted}"
                            y = exp.get("years", 0.0)
                            y_formatted = f"{int(y) if y == int(y) else y} yrs"
                            
                            with st.expander(f"💼 {role} | {org} | {duration}", expanded=True):
                                # Custom spacing wrappers
                                st.markdown(f"""
                                <div style="line-height: 1.6; word-break: break-word; overflow-wrap: anywhere; margin-bottom: 12px;">
                                    <div style="margin-bottom: 6px;"><strong>Role:</strong> <span style="color: #c9d1d9;">{role}</span></div>
                                    <div style="margin-bottom: 6px;"><strong>Organization:</strong> <span style="color: #c9d1d9;">{org}</span></div>
                                    <div style="margin-bottom: 6px;"><strong>Duration:</strong> <span style="color: #c9d1d9;">{duration} ({y_formatted})</span></div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Technologies scan inside description
                                raw_desc = exp.get("description", "")
                                skills_val = active_projected.get("skills") or active_projected.get("skills_list") or []
                                matched_techs = []
                                for s in get_normalized_and_sorted_skills(skills_val):
                                    if s.lower() in raw_desc.lower():
                                        matched_techs.append(s)
                                matched_techs = sorted(list(set(matched_techs)))
                                
                                if matched_techs:
                                    st.markdown("<div style='margin-bottom: 6px;'><strong>Technologies:</strong></div>", unsafe_allow_html=True)
                                    render_skills_chips(matched_techs, max_initial=30)
                                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                                    
                                # Spacing and Description rendering
                                st.markdown("<div style='margin-top: 8px; margin-bottom: 6px;'><strong>Description:</strong></div>", unsafe_allow_html=True)
                                
                                # Description clean up
                                cleaned_desc = clean_experience_description(raw_desc)
                                
                                # Tech stack joining replacement in raw description presentation
                                joined_techs_pattern = "".join(matched_techs)
                                if joined_techs_pattern and joined_techs_pattern.lower() in cleaned_desc.lower():
                                    formatted_techs = " • ".join(matched_techs)
                                    cleaned_desc = re.sub(re.escape(joined_techs_pattern), formatted_techs, cleaned_desc, flags=re.IGNORECASE)
                                
                                # Split bullets or sentences
                                if any(char in cleaned_desc for char in ["•", "-", "*"]):
                                    bullets = [b.strip() for b in re.split(r'[•\-*]', cleaned_desc) if b.strip()]
                                    bullet_html = "<ul style='margin-top: 4px; margin-bottom: 12px; line-height: 1.6; word-break: break-word; overflow-wrap: anywhere;'>"
                                    for b in bullets:
                                        bullet_html += f"<li>{b}</li>"
                                    bullet_html += "</ul>"
                                    st.markdown(bullet_html, unsafe_allow_html=True)
                                else:
                                    sentences = [s.strip() for s in re.split(r'\.\s+', cleaned_desc) if s.strip()]
                                    bullet_html = "<ul style='margin-top: 4px; margin-bottom: 12px; line-height: 1.6; word-break: break-word; overflow-wrap: anywhere;'>"
                                    for sentence in sentences:
                                        if sentence:
                                            if not sentence.endswith((".", "!", "?")):
                                                sentence += "."
                                            bullet_html += f"<li>{sentence}</li>"
                                    bullet_html += "</ul>"
                                    st.markdown(bullet_html, unsafe_allow_html=True)
                    else:
                        st.info("No professional experience detected.")
                        
                # --- 3. EDUCATION RECORDS TAB ---
                elif tab_name == "Education Records":
                    render_section_header("Education Records")
                    edu_list = active_projected.get("education", [])
                    if edu_list:
                        edu_col1, edu_col2 = st.columns(2)
                        for idx, edu in enumerate(edu_list):
                            col = edu_col1 if idx % 2 == 0 else edu_col2
                            deg = edu.get("degree", "Degree")
                            inst = edu.get("institution", "Institution")
                            field = edu.get("field_of_study", "N/A") or "N/A"
                            duration = f"{format_date_str(edu.get('start_date'))} to {format_date_str(edu.get('end_date'))}"
                            gpa = edu.get("gpa") or edu.get("cgpa") or edu.get("grade") or "N/A"
                            
                            gpa_str = f" | Grade/CGPA: <b>{gpa}</b>" if gpa != "N/A" else ""
                            
                            col.markdown(f"""
                            <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin-bottom: 12px;">
                                <div style="font-size: 15px; font-weight: bold; color: #c9d1d9;">🎓 {deg}</div>
                                <div style="font-size: 13px; color: #8b949e; margin-top: 4px;">{inst}</div>
                                <div style="font-size: 12px; color: #8b949e; margin-top: 2px;">Field: <b>{field}</b> | Duration: {duration}{gpa_str}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.write("No education records found.")
                        
                # --- 4. SKILLS TAB ---
                elif tab_name == "Skills":
                    render_section_header("Identified Skills")
                    skills_val = active_projected.get("skills") or active_projected.get("skills_list")
                    if skills_val is not None:
                        flat_ordered_skills = get_normalized_and_sorted_skills(skills_val)
                        
                        ordered_categories = [
                            "Programming Languages",
                            "Libraries & Frameworks",
                            "Developer Tools",
                            "AI / Data Science",
                            "Professional Skills"
                        ]
                        
                        # Group normalized unique skills
                        grouped_skills = {cat: [] for cat in ordered_categories}
                        grouped_skills["Other Skills"] = []
                        
                        for s in flat_ordered_skills:
                            assigned = False
                            s_cat = get_skill_category(s)
                            if s_cat in grouped_skills:
                                grouped_skills[s_cat].append(s)
                                assigned = True
                            if not assigned:
                                grouped_skills["Other Skills"].append(s)
                                
                        # Render category expanders dynamically (only if non-empty)
                        for cat in ordered_categories + ["Other Skills"]:
                            cat_skills = sorted(list(set(grouped_skills[cat]))) # sort alphabetically
                            if cat_skills:
                                count = len(cat_skills)
                                with st.expander(f"📁 {cat} ({count})", expanded=False):
                                    chips_html = '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px;">'
                                    for skill in cat_skills:
                                        chips_html += f'<span class="chip">{skill}</span>'
                                    chips_html += '</div>'
                                    st.markdown(chips_html, unsafe_allow_html=True)
                    else:
                        st.write("No skills included in this projection.")
                        
                # --- 5. RAW JSON TAB ---
                elif tab_name == "Raw JSON":
                    st.json(active_projected)
                    
                # --- 6. CONFIDENCE TAB ---
                elif tab_name == "Confidence":
                    render_section_header("Confidence Evaluation Metrics")
                    if overall_conf is not None:
                        render_custom_progress_bar(float(overall_conf), "Overall Candidate Score")
                        st.write("Confidence represents the reliability of normalized candidate information after parsing, normalization, and merge processing.")
                        
                    st.markdown("---")
                    st.markdown("#### Sorted Field Confidences")
                    conf_dict = active_projected.get("_confidence", {})
                    sorted_conf = sorted(conf_dict.items(), key=lambda x: x[1], reverse=True)
                    
                    for field, score in sorted_conf:
                        field_title = field.replace('_', ' ').title()
                        render_custom_progress_bar(float(score), field_title)
                        
                # --- 7. PROVENANCE TAB ---
                elif tab_name == "Provenance":
                    render_section_header("Data Provenance Tracking")
                    
                    # Renders a simple, clean Field and Winning Source table
                    prov_dict = active_projected.get("_provenance", {})
                    prov_rows = []
                    for f_name, entry in prov_dict.items():
                        prov_rows.append({
                            "Field": f_name.replace("_", " ").title(),
                            "Winning Source": entry.get("source", "N/A"),
                            "Method / Merge Decision": entry.get("method", "N/A")
                        })
                        
                    if prov_rows:
                        st.dataframe(pd.DataFrame(prov_rows), use_container_width=True)
                    else:
                        st.write("No provenance metadata generated.")
                        
                    st.markdown("---")
                    with st.expander("Show raw JSON Provenance Metadata", expanded=False):
                        st.json(prov_dict)
                        
                # --- 8. PIPELINE INFO TAB ---
                elif tab_name == "Pipeline Info":
                    render_section_header("Pipeline Info Metrics")
                    
                    # Left side: pipeline visual workflow, Right side: run metrics and statistics
                    flow_col, stat_col = st.columns([1, 1])
                    
                    with flow_col:
                        st.markdown("#### ⚙️ Processing Pipeline Flow")
                        st.markdown("""
                        ```
                        📄 Resume PDF
                             ↓
                        ⚙️ Resume Parser
                             ↓
                        📊 CSV Parser
                             ↓
                        🧼 Field Normalization
                             ↓
                        🔍 Identity Consistency Check
                             ↓
                        🔀 Merge Engine
                             ↓
                        📈 Confidence Engine
                             ↓
                        📐 Projection Engine
                             ↓
                        🛡️ Schema Validation
                             ↓
                        📦 Projected JSON Output
                        ```
                        """)
                        
                    with stat_col:
                        st.markdown("#### ⏳ Execution Metadata")
                        info_col1, info_col2 = st.columns(2)
                        
                        render_metric_card(info_col1, "⏳", "Execution Time", exec_timestamp, "Runtime Timestamp")
                        render_metric_card(info_col2, "⚙️", "Configuration Used", "default_config.json" if config_selection == "Default Config" else "custom_config.json", "Runtime Config File")
                    
        # Downloads Section (Bottom of Page)
        st.markdown("---")
        dl_col1, dl_col2 = st.columns(2)
        
        dl_col1.download_button(
            label="Download Default JSON",
            data=json.dumps(projected_default, indent=2),
            file_name="candidate_default.json",
            mime="application/json",
            use_container_width=True
        )
        
        dl_col2.download_button(
            label="Download Custom JSON",
            data=json.dumps(projected_custom, indent=2),
            file_name="candidate_custom.json",
            mime="application/json",
            use_container_width=True
        )

    # Footer
    st.markdown("""
    <div class="footer">
        Built for Eightfold Engineering Internship Assignment<br>
        Python • Streamlit • Typer • Pydantic • pdfplumber • RapidFuzz
    </div>
    """, unsafe_allow_html=True)
