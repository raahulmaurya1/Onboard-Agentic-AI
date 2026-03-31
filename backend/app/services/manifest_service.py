from typing import List, Dict

# Mock database mapping of Onboarding Intents to required Document manifests
DOCUMENT_MANIFEST_DB: Dict[str, List[str]] = {
    "Retail": ["Aadhaar", "PAN"],
    "Digital-Only": ["Aadhaar", "Selfie_Video"],
    "SME": ["Aadhaar", "PAN", "GST_Certificate", "Business_Registration"],
    "Re-KYC": ["Aadhaar", "Recent_Utility_Bill"]
}

def get_checklist_for_intent(intent: str) -> List[str]:
    """
    Retrieves the required document checklist for a given classified intent.
    Returns a default list if the intent is not found.
    """
    # Default to Retail if unknown
    return DOCUMENT_MANIFEST_DB.get(intent, ["Aadhaar", "PAN"])
