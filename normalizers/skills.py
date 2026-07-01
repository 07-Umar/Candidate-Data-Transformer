import logging
from rapidfuzz import process, utils

logger = logging.getLogger(__name__)

# Predefined canonical list of software engineering, AI, and ML skills
CANONICAL_SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "C++",
    "SQL",
    "Machine Learning",
    "Deep Learning",
    "Natural Language Processing (NLP)",
    "Generative AI",
    "LLMs",
    "PyTorch",
    "TensorFlow",
    "Scikit-learn",
    "FastAPI",
    "React",
    "Git",
    "GitHub",
    "Linux",
    "HTML",
    "CSS",
    "Data Structures and Algorithms",
    "Operating Systems",
    "Computer Networks",
    "Database Management Systems (DBMS)",
    "Software Engineering",
    "Docker",
    "Kubernetes",
    "AWS",
    "Pandas",
    "NumPy",
    "Matplotlib",
    "Seaborn",
    "Tailwind CSS",
    "NLP",
    "GenAI",
    "LLM",
    "Node.js"
]

def normalize_skill(skill_str: str, threshold: float = 80.0) -> str:
    """
    Standardize a skill name using rapidfuzz string matching.
    Supports strict canonical mapping overrides for key abbreviations.
    If similarity with any canonical skill is >= threshold, returns the canonical name.
    Otherwise, returns the trimmed, title-cased original.
    """
    if not skill_str:
        return ""
    
    cleaned = skill_str.strip()
    
    # Strict abbreviation mappings
    strict_mappings = {
        "nlp": "NLP",
        "genai": "GenAI",
        "llm": "LLM",
        "github": "GitHub",
        "tensor flow": "TensorFlow",
        "scikit learn": "Scikit-learn",
        "py torch": "PyTorch",
        "nodejs": "Node.js",
        "node.js": "Node.js"
    }
    
    cleaned_lower = cleaned.lower()
    if cleaned_lower in strict_mappings:
        return strict_mappings[cleaned_lower]
        
    comp_cleaned = utils.default_process(cleaned)
    if not comp_cleaned:
        return cleaned
    
    # Use extractOne to find the best match in our canonical list
    result = process.extractOne(cleaned, CANONICAL_SKILLS, processor=utils.default_process)
    if result:
        matched_skill, score, _ = result
        if score >= threshold:
            # Check if matching skill maps to a strict canonical form
            matched_lower = matched_skill.lower()
            if matched_lower in strict_mappings:
                return strict_mappings[matched_lower]
            return matched_skill
            
    title_val = cleaned.title()
    if title_val.lower() in strict_mappings:
        return strict_mappings[title_val.lower()]
    return title_val
