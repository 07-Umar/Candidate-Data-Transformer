import logging
import phonenumbers

logger = logging.getLogger(__name__)

def normalize_phone(phone_str: str, default_region: str = "IN") -> str:
    """
    Standardize a phone number to E164 format using phonenumbers library.
    If parsing fails, returns the cleaned alphanumeric string.
    """
    if not phone_str:
        return ""
    
    # Remove leading/trailing whitespaces
    cleaned = phone_str.strip()
    
    try:
        # Check if the number starts with + or contains a country code
        # We can parse with a default region (e.g. IN for India)
        parsed_number = phonenumbers.parse(cleaned, default_region)
        if phonenumbers.is_valid_number(parsed_number):
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        else:
            # Try parsing without default region in case it is already international
            parsed_intl = phonenumbers.parse(cleaned, None)
            if phonenumbers.is_valid_number(parsed_intl):
                return phonenumbers.format_number(parsed_intl, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        logger.warning(f"Failed parsing phone number '{phone_str}': {e}")
    
    # Return cleaned string (only digits and plus) as fallback
    fallback = "".join(c for c in cleaned if c.isdigit() or c == "+")
    return fallback
