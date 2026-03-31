from typing import List, Dict, Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid


def get_form_schema(account_type: str) -> List[Dict[str, Any]]:
    """
    Returns a UI-ready array of field definitions for the 'Additional Information' stage.
    """
    if account_type == "retail_savings" or account_type == "digital_only":
        return [
            {"label": "Mother's Maiden Name", "key": "mothers_maiden_name", "type": "text", "required": True},
            {
                "label": "Marital Status", 
                "key": "marital_status", 
                "type": "dropdown", 
                "options": ["Single", "Married", "Divorced", "Widowed"], 
                "required": True
            },
            {
                "label": "Occupation Type", 
                "key": "occupation_type", 
                "type": "dropdown", 
                "options": ["Salaried", "Self-Employed", "Business", "Retired", "Student", "Homemaker"], 
                "required": True
            },
            {
                "label": "Annual Income Bracket", 
                "key": "annual_income", 
                "type": "dropdown", 
                "options": ["Below 1L", "1L-5L", "5L-10L", "10L-25L", "Above 25L"], 
                "required": True
            },
            {
                "label": "PEP (Politically Exposed Person) Status", 
                "key": "pep_status", 
                "type": "radio", 
                "options": ["Yes", "No"], 
                "required": True
            },
            {
                "label": "Are you a tax resident outside India (FATCA/CRS)?", 
                "key": "fatca_outside_india", 
                "type": "radio", 
                "options": ["Yes", "No"], 
                "required": True
            },
            {"label": "Foreign Tax ID", "key": "foreign_tax_id", "type": "text", "required": False, "conditional_on": "fatca_outside_india"},
            {
                "label": "Opt for Nominee?", 
                "key": "nominee_opted", 
                "type": "radio", 
                "options": ["Yes", "No"], 
                "required": True
            },
            {"label": "Nominee Name", "key": "nominee_name", "type": "text", "required": False, "conditional_on": "nominee_opted"},
            {
                "label": "Nominee Relationship", 
                "key": "nominee_relationship", 
                "type": "dropdown", 
                "options": ["Spouse", "Father", "Mother", "Son", "Daughter", "Sibling", "Other"],
                "required": False,
                "conditional_on": "nominee_opted"
            },
            {"label": "Nominee Date of Birth", "key": "nominee_dob", "type": "date", "required": False, "conditional_on": "nominee_opted"}
        ]
    
    elif account_type == "sme_current":
        return [
            {
                "label": "Industry NIC Code",
                "key": "business_profile.industry_nic_code",
                "type": "text",
                "required": True
            },
            {
                "label": "Expected Annual Turnover (INR)",
                "key": "business_profile.expected_annual_turnover",
                "type": "number",
                "required": True
            },
            {
                "label": "Are there additional stakeholders (Partners / Directors)?",
                "key": "stakeholders.is_applicable",
                "type": "radio",
                "options": ["Yes", "No"],
                "required": True
            },
            {
                "label": "Stakeholder Details",
                "key": "stakeholders.partners",
                "type": "array",
                "required": False,
                "conditional_on": "stakeholders.is_applicable",
                "item_schema": [
                    {"label": "Name",  "key": "name", "type": "text",   "required": True},
                    {"label": "PAN",   "key": "pan",  "type": "text",   "required": True},
                    {
                        "label": "Role",
                        "key": "role",
                        "type": "select",
                        "options": ["partner", "director", "authorized_signatory"],
                        "required": True
                    }
                ]
            }
        ]
    
    # Fallback for generic or unknown account types
    return [{"label": "Generic Info", "key": "generic_data", "type": "text", "required": True}]


async def update_additional_info(
    session_ulid: str,
    form_data: Dict[str, Any],
    db: AsyncSession,
) -> bool:
    """
    Persists additional info form data for a lifecycle (Re-KYC / Reactivation) session.

    Strategy:
    - If an AdditionalInfo row exists for session_ulid: merge incoming form_data into
      the existing JSONB blob (non-destructive — existing keys like gst_data are kept).
    - If no row exists: create a new one (e.g., first submission on this session).

    NEVER touches unrelated columns in user_initial.
    Returns True on success, raises on failure.
    """
    from app.db.models.user import AdditionalInfo
    from sqlalchemy.orm.attributes import flag_modified

    # 1. Check for existing row
    stmt = select(AdditionalInfo).where(AdditionalInfo.session_ulid == session_ulid)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        # Non-destructive merge: keep existing data, overlay with new form data
        existing_dict = existing.data if isinstance(existing.data, dict) else {}
        merged = {**existing_dict, **{k: v for k, v in form_data.items() if v is not None}}
        existing.data = merged
        flag_modified(existing, "data")  # Required for JSONB mutation detection
    else:
        # First submission for this lifecycle session
        db.add(AdditionalInfo(
            id=str(uuid.uuid4()),
            session_ulid=session_ulid,
            data={k: v for k, v in form_data.items() if v is not None}
        ))

    await db.commit()
    return True
