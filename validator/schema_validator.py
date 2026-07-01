import logging
import jsonschema
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SchemaValidationError(Exception):
    """Custom exception representing validation errors with readable messages."""
    pass

def map_type_to_json_schema(type_str: str) -> Dict[str, Any]:
    """Maps custom config types to standard JSON Schema types."""
    t_clean = type_str.strip().lower()
    
    if t_clean == "string":
        return {"type": ["string", "null"]}
    elif t_clean in ["string[]", "array[string]", "list[string]"]:
        return {
            "type": ["array", "null"],
            "items": {"type": "string"}
        }
    elif t_clean in ["float", "double", "number"]:
        return {"type": ["number", "null"]}
    elif t_clean in ["integer", "int"]:
        return {"type": ["integer", "null"]}
    elif t_clean == "boolean":
        return {"type": ["boolean", "null"]}
    elif t_clean == "object":
        return {"type": ["object", "null"]}
    elif t_clean == "object[]":
        return {
            "type": ["array", "null"],
            "items": {"type": "object"}
        }
    return {"type": ["string", "number", "boolean", "object", "array", "null"]} # Fallback type

def generate_json_schema(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dynamically constructs a JSON Schema from a runtime projection configuration.
    """
    properties = {}
    required_fields = []
    
    fields_config = config.get("fields", [])
    include_confidence = config.get("include_confidence", True)
    include_provenance = config.get("include_provenance", True)
    
    for field_cfg in fields_config:
        path = field_cfg.get("path")
        field_type = field_cfg.get("type", "string")
        required = field_cfg.get("required", False)
        
        properties[path] = map_type_to_json_schema(field_type)
        if required:
            required_fields.append(path)
            
    # Add metadata properties to schema if enabled
    if include_confidence:
        properties["_confidence"] = {
            "type": "object",
            "additionalProperties": {"type": "number"}
        }
        properties["_overall_confidence"] = {"type": "number"}
        
    if include_provenance:
        properties["_provenance"] = {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "method": {"type": "string"}
                },
                "required": ["source", "method"]
            }
        }
        
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "CandidateProjectedSchema",
        "type": "object",
        "properties": properties,
        "required": required_fields,
        "additionalProperties": False
    }
    
    return schema

def validate_projected_output(output_dict: Dict[str, Any], config: Dict[str, Any]) -> None:
    """
    Validates a projected candidate output dictionary against the dynamically generated schema.
    Raises SchemaValidationError with descriptive details on failure.
    """
    schema = generate_json_schema(config)
    try:
        jsonschema.validate(instance=output_dict, schema=schema)
        logger.info("Projected candidate output validation succeeded.")
    except jsonschema.ValidationError as e:
        # Construct a highly readable and actionable error message
        path = " -> ".join(str(p) for p in e.path) if e.path else "root"
        err_msg = (
            f"JSON Schema Validation Error at path '{path}': {e.message}\n"
            f"Failed Value: {e.instance}\n"
            f"Failed Validator: {e.validator} with rule {e.validator_value}"
        )
        logger.error(err_msg)
        raise SchemaValidationError(err_msg) from e
