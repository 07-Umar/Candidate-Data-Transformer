import re
import logging

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def normalize_email(email_str: str) -> str:
    """
    Lowercase, trim, and validate an email address.
    Returns the normalized email or an empty string if invalid.
    """
    if not email_str:
        return ""
    
    cleaned = email_str.strip().lower()
    
    if EMAIL_REGEX.match(cleaned):
        return cleaned
    
    logger.warning(f"Email '{email_str}' did not match regex pattern.")
    return ""
