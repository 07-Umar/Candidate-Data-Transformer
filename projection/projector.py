import re
import logging
from typing import Dict, Any, List, Optional
from models.canonical import CanonicalProfile
from normalizers.phone import normalize_phone
from normalizers.email import normalize_email
from normalizers.skills import normalize_skill
from normalizers.location import normalize_country

logger = logging.getLogger(__name__)

def evaluate_json_path(data: Any, path: str) -> Any:
    """
    Evaluates a simple json path expression against a dictionary or list.
    Supports index access (e.g. 'emails[0]') and list mappings (e.g. 'skills[].name').
    """
    if not path or data is None:
        return None
        
    parts = path.split(".")
    current = data
    
    for idx, part in enumerate(parts):
        if current is None:
            return None
            
        # Check for list projection like 'skills[].name'
        if "[]" in part:
            field = part.replace("[]", "")
            # Get the list
            list_val = current.get(field) if isinstance(current, dict) else getattr(current, field, None)
            if not isinstance(list_val, list):
                return None
                
            # If there are remaining path parts, map them over the list items
            remaining_path = ".".join(parts[idx+1:])
            if remaining_path:
                projected = []
                for item in list_val:
                    # Convert Pydantic model to dict if needed
                    item_data = item.model_dump() if hasattr(item, "model_dump") else item
                    val = evaluate_json_path(item_data, remaining_path)
                    if val is not None:
                        projected.append(val)
                return projected
            else:
                return list_val
                
        # Check for indexed access like 'emails[0]'
        index_match = re.match(r"(\w+)\[(\d+)\]", part)
        if index_match:
            field = index_match.group(1)
            array_idx = int(index_match.group(2))
            # Retrieve field value
            list_val = current.get(field) if isinstance(current, dict) else getattr(current, field, None)
            if isinstance(list_val, list) and array_idx < len(list_val):
                current = list_val[array_idx]
            else:
                return None
        else:
            # Regular field access
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
                
    # Convert Pydantic models to dict/list if they are returned at the end
    if hasattr(current, "model_dump"):
        return current.model_dump()
    if isinstance(current, list):
        return [item.model_dump() if hasattr(item, "model_dump") else item for item in current]
        
    return current

def get_base_canonical_field(path: str) -> str:
    """Extracts the base canonical field name from a path expression (e.g. 'emails[0]' -> 'emails')."""
    if not path:
        return ""
    # Split by dot and take the first part
    first_part = path.split(".")[0]
    # Remove array indexing brackets
    return re.sub(r"\[\d*\]", "", first_part)

def project_candidate(profile: CanonicalProfile, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Projects a CanonicalProfile into a dictionary according to a runtime config.
    Handles field selection, remapping, normalization, missing values, confidence, and provenance.
    """
    output = {}
    confidences = {}
    provenance = {}
    
    # 1. Parse configuration options
    fields_config = config.get("fields", [])
    include_confidence = config.get("include_confidence", True)
    include_provenance = config.get("include_provenance", True)
    on_missing = config.get("on_missing", "null")  # Options: null, omit, error
    
    profile_dict = profile.model_dump()
    
    # 2. Project each field
    for field_cfg in fields_config:
        target_path = field_cfg.get("path")
        source_path = field_cfg.get("from", target_path)
        field_type = field_cfg.get("type", "string")
        required = field_cfg.get("required", False)
        normalize_opt = field_cfg.get("normalize")
        
        # Evaluate value from canonical profile
        val = evaluate_json_path(profile_dict, source_path)
        
        # Apply normalization if specified
        if val is not None:
            if normalize_opt == "E164":
                if isinstance(val, list):
                    val = [normalize_phone(v) for v in val]
                else:
                    val = normalize_phone(val)
            elif normalize_opt == "canonical":
                # Check if it's skills or country
                if "skills" in source_path:
                    if isinstance(val, list):
                        val = [normalize_skill(v) for v in val]
                    else:
                        val = normalize_skill(val)
                elif "country" in source_path or "location" in source_path:
                    if isinstance(val, list):
                        val = [normalize_country(v) for v in val]
                    else:
                        val = normalize_country(val)
            elif normalize_opt == "lowercase":
                if isinstance(val, list):
                    val = [str(v).lower() for v in val]
                else:
                    val = str(val).lower()
            elif normalize_opt == "uppercase":
                if isinstance(val, list):
                    val = [str(v).upper() for v in val]
                else:
                    val = str(val).upper()
                    
        # Handle missing value
        if val is None or val == [] or val == "":
            is_email_field = "email" in target_path.lower() or "email" in source_path.lower()
            if is_email_field and required:
                val = ""
            else:
                if required:
                    if on_missing == "error":
                        raise ValueError(f"Required field '{target_path}' (source path: '{source_path}') is missing and on_missing policy is 'error'.")
                    elif on_missing == "omit":
                        continue
                    else:  # default to null
                        val = None
                else:
                    if on_missing == "omit":
                        continue
                    else:
                        val = None
                    
        output[target_path] = val
        
        # 3. Handle confidence and provenance for this projected field
        base_field = get_base_canonical_field(source_path)
        
        # Get source confidence
        conf_val = profile.field_confidences.get(base_field, 0.0)
        confidences[target_path] = conf_val
        
        # Get source provenance
        prov_entry = profile.provenance.get(base_field)
        if prov_entry:
            provenance[target_path] = {
                "source": prov_entry.source,
                "method": prov_entry.method
            }
        else:
            provenance[target_path] = {
                "source": "unknown",
                "method": "unknown"
            }
            
    # Include overall confidence
    if include_confidence:
        output["_confidence"] = confidences
        output["_overall_confidence"] = profile.overall_confidence
        
    # Include provenance
    if include_provenance:
        output["_provenance"] = provenance
        
    return output
