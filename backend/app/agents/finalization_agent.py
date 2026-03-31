from typing import Dict, Any
import re
from datetime import datetime
from app.db.models.user import UserInitial
import logging

logger = logging.getLogger(__name__)

def extract_combined_data(verified_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intelligently traverses the JSON regardless of how deeply nested the 
    Swagger UI or external payload wrapped the "combined_data" dictionary.
    """
    if not verified_data:
        return {}
        
    if "combined_data" in verified_data:
        return verified_data["combined_data"]
        
    # Standard extraction flow
    if "validation" in verified_data and "combined_data" in verified_data["validation"]:
        return verified_data["validation"]["combined_data"]
        
    # Deep extraction block
    if "extracted_data" in verified_data:
        ext = verified_data["extracted_data"]
        if "validation" in ext and "combined_data" in ext["validation"]:
            return ext["validation"]["combined_data"]
            
    # Fallback to flattening the root if the exact keys are mysteriously placed at the top
    return verified_data

def format_date(date_str: str) -> str:
    """
    Attempts to neatly format raw OCR strings into DD/MM/YYYY.
    If it fails parsing, returns the raw string safely so data isn't dropped.
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Already mapped clean
    if re.match(r"^\d{2}/\d{2}/\d{4}$", date_str):
        return date_str
        
    # Dash mapping
    if re.match(r"^\d{2}-\d{2}-\d{4}$", date_str):
        return date_str.replace("-", "/")
        
    return date_str

def clean_address(address: str) -> str:
    """
    Strips 'C/O: Name, ', 'S/O: Name, ', or 'W/O: Name, ' prefixes from Aadhaar addresses natively.
    """
    if not address:
        return ""
    
    address = address.strip()
    # Match C/O:, S/O:, D/O:, W/O: followed by anything until the first comma
    match = re.match(r"(?i)^[A-Z]/O:.*?,(.*)", address)
    if match:
        return match.group(1).strip()
    return address

def execute_hybrid_freeze(user: UserInitial) -> None:
    """
    Phase 2 Finalization Sequence:
    1. Extracts the "Active Truth" JSON dynamically.
    2. Runs deduplication (favoring PAN over Aadhaar for DOB etc.).
    3. Runs standardization (.upper(), date alignment, whitespace stripping).
    4. Commits data to explicit Relational SQL columns.
    5. Archives the raw JSON immutably.
    6. Severes the volatile session 'working memory'.
    """
    if not user.verified_data:
        logger.warning(f"Hybrid freeze called on User {user.id} but verified_data is empty!")
        return
        
    # 1. Flatten the true payload
    payload = extract_combined_data(user.verified_data)
    
    # 2. Extract and Deduplicate Core Nodes
    # The frontend now natively sends the exact cleaned schema
    raw_name = payload.get("name", "")
    raw_father = payload.get("father_name", "")
    
    # Address Logic
    raw_address = payload.get("address", "")
    
    # DOB Logic
    raw_dob = payload.get("dob", "")
    
    # ID Numbers
    raw_pan = payload.get("pan_id", "")
    raw_aadhaar = payload.get("aadhar_id", "")
    
    # 3. Standardization & Cleanup
    user.name = str(raw_name).strip().upper() if raw_name else None
    user.father_name = str(raw_father).strip().upper() if raw_father else None
    
    clean_addr = clean_address(str(raw_address))
    user.address = clean_addr.upper() if clean_addr else None
    
    user.dob = format_date(str(raw_dob)) if raw_dob else None
    
    # Strip spaces globally from explicit Federal identifiers
    user.pan_id = str(raw_pan).replace(" ", "").strip().upper() if raw_pan else None
    user.aadhar_id = str(raw_aadhaar).replace(" ", "").strip() if raw_aadhaar else None
    
    # 4. The Immutable Archive Freeze
    user.raw_archive = user.verified_data  # Commit to historical ReadOnly ledger
    user.verified_data = None              # Wipe volatile 'working memory'
    user.status = "FINALIZED"
