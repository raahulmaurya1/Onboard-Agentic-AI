from typing import Dict, Any
import logging

import logging
import json
import os

logger = logging.getLogger(__name__)

# Load Rulebook natively
RULEBOOK_PATH = os.path.join(os.path.dirname(__file__), 'rule_book.json')
with open(RULEBOOK_PATH, 'r') as f:
    RULEBOOK = json.load(f)

def revalidate_corrections(merged_data: Dict[str, Any]) -> dict:
    """
    Re-evaluates the entire rulebook dynamically against the user's manual corrections.
    Instead of array ingestion, it parses the flattened 'Aadhaar_name', 'PAN_name' payload natively.
    """
    flags = []
    
    # Apply Rulebook cross_checks directly mapping against the flattened keys statically
    checks = RULEBOOK.get("cross_checks", {})
    for check in checks.get("PAN_vs_Aadhaar", {}).get("match_fields", []):
        field = check.get("field")
        
        # Pull from the flattened combined_data dictionary
        pan_val = str(merged_data.get(f"PAN_{field}", "")).strip().lower()
        aad_val = str(merged_data.get(f"Aadhaar_{field}", "")).strip().lower()
        
        if pan_val and aad_val:
            if check.get("tolerance") == "exact":
                if pan_val != aad_val:
                    flags.append(check.get("flag"))
                    
    return {
        "valid": len(flags) == 0,
        "flags": flags,
        "combined_data": merged_data
    }

def cross_check_documents(extracted_data: list) -> dict:
    """
    Parses an entire session's uploaded document data against the JSON rulebook natively.
    Specifically isolates PAN and Aadhaar and mathematically checks differences like Name or DOB Mismatches.
    Returns:
    {
       "valid": boolean,
       "flags": ["NAME_MISMATCH", "MISSING_PAN_FIELD", etc],
       "combined_data": {} // Unified clean representation of the user
    }
    """
    flags = []
    combined_data = {}
    
    pan_data = {}
    aadhaar_data = {}
    
    for doc in extracted_data:
        doc_type = doc.get("document_type")
        fields = doc.get("extracted_fields", {})
        
        # Map directly to expected unified schema
        for k, v in fields.items():
            if v and v != "null":
                if k == "id_number" and doc_type == "PAN":
                    combined_data["pan_id"] = v
                elif k == "id_number" and doc_type in ["Aadhaar", "Aadhar", "aadhar"]:
                    combined_data["aadhar_id"] = v
                else:
                    # Prefer Aadhaar overwrites for master records if existing
                    combined_data[k] = v
                
        if doc_type == "PAN":
            pan_data = fields
        elif doc_type in ["Aadhaar", "Aadhar", "aadhar"]:
            aadhaar_data = fields
            
    # Apply Rulebook cross_checks
    checks = RULEBOOK.get("cross_checks", {})
    if pan_data and aadhaar_data:
        for check in checks.get("PAN_vs_Aadhaar", {}).get("match_fields", []):
            field = check.get("field")
            pan_val = str(pan_data.get(field, "")).strip().lower()
            aad_val = str(aadhaar_data.get(field, "")).strip().lower()
            
            if pan_val and aad_val:
                if check.get("tolerance") == "exact":
                    if pan_val != aad_val:
                        flags.append(check.get("flag"))
                        
    return {
        "valid": len(flags) == 0,
        "flags": flags,
        "combined_data": combined_data
    }
