from pydantic import BaseModel, Field
from typing import Optional

class OnboardingState(BaseModel):
    session_ulid: Optional[str] = Field(None, description="Unique ID for the onboarding session")
    current_step: str = Field("intent_classification", description="Current node in the graph")
    intent: Optional[str] = Field(None, description="The user's categorized intent")
    documents_uploaded: bool = Field(False, description="Whether KYC docs have been provided")
    risk_score: float = Field(0.0, description="Evaluated risk score (0-100)")
    status: str = Field("pending", description="Overall session status: pending, approved, escalate, retry")
