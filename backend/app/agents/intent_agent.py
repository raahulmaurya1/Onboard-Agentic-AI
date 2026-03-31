import json
from enum import Enum
from pydantic import BaseModel, Field
import google.generativeai as genai

from app.services.gemini_client import gemini_client
import logging

logger = logging.getLogger(__name__)

class IntentCategory(str, Enum):
    RETAIL_SAVINGS = "retail_savings"
    DIGITAL_ONLY   = "digital_only"
    SME_CURRENT    = "sme_current"
    RE_KYC         = "re_kyc"
    REACTIVATION   = "reactivation"
    UNKNOWN        = "unknown"

# Lifecycle intents — these trigger the LifecycleOrchestrator strategy
LIFECYCLE_INTENTS = {IntentCategory.RE_KYC, IntentCategory.REACTIVATION}

class IntentClassificationResult(BaseModel):
    intent: IntentCategory = Field(description="The determined category of onboarding scenario.")
    confidence: float = Field(description="The AI's confidence in this classification from 0 to 1.")
    reasoning: str = Field(description="Short rationale for why this classification was chosen.")


async def classify_intent(user_input: str) -> IntentClassificationResult:
    """
    Passes the natural language user input to Gemini to determine
    the correct onboarding/lifecycle intent.
    """
    
    # ── LATENCY OPTIMIZATION: Keyword Heuristics ──
    user_input_lower = user_input.lower()
    if "re-kyc" in user_input_lower or "re kyc" in user_input_lower or "rekyc" in user_input_lower or "update kyc" in user_input_lower or "update my kyc" in user_input_lower:
        return IntentClassificationResult(intent=IntentCategory.RE_KYC, confidence=0.9, reasoning="Keyword match")
    elif "reactivat" in user_input_lower or "unfreeze" in user_input_lower or "dormant" in user_input_lower:
        return IntentClassificationResult(intent=IntentCategory.REACTIVATION, confidence=0.9, reasoning="Keyword match")
    elif "savings" in user_input_lower or "retail" in user_input_lower:
        return IntentClassificationResult(intent=IntentCategory.RETAIL_SAVINGS, confidence=0.9, reasoning="Keyword match")
    elif "digital" in user_input_lower or "zero balance" in user_input_lower:
        return IntentClassificationResult(intent=IntentCategory.DIGITAL_ONLY, confidence=0.9, reasoning="Keyword match")
    elif "sme" in user_input_lower or "business" in user_input_lower or "corporate" in user_input_lower:
        return IntentClassificationResult(intent=IntentCategory.SME_CURRENT, confidence=0.9, reasoning="Keyword match")
    elif "new account" in user_input_lower or "open account" in user_input_lower or "open new account" in user_input_lower:
        return IntentClassificationResult(intent=IntentCategory.RETAIL_SAVINGS, confidence=0.7, reasoning="Generic new account keyword")
    
    prompt = f"""
    You are an AI core agent for a bank account management system. Your task is to classify a user's
    natural language request into one of six specific categories:
    
    1. 'retail_savings': Standard personal savings accounts for individuals.
       (e.g., "I want to open a savings account", "I need a bank account")
    2. 'digital_only': Zero-balance, paperless, instant digital accounts.
       (e.g., "I want a quick digital account", "zero balance account", "instant online account")
    3. 'sme_current': Business current accounts for Small and Medium Enterprises.
       (e.g., "I want to open a business account", "SME account", "corporate account for my firm")
    4. 're_kyc': An EXISTING customer who needs to update or re-verify their KYC documents.
       (e.g., "I need to update my KYC", "bank asked me to re-verify", "update my documents")
    5. 'reactivation': An EXISTING customer whose account is dormant or suspended and needs reactivating.
       (e.g., "reactivate my account", "my account was deactivated", "unfreeze my bank account")
    6. 'unknown': Use this if the user hasn't specified a clear intent, or the input is a greeting/unclear.

    User Query: '{user_input}'
    
    Respond STRICTLY in JSON format with the following keys:
    - intent: (string, exactly one of "retail_savings", "digital_only", "sme_current", "re_kyc", "reactivation", "unknown")
    - confidence: (float, 0.0 to 1.0)
    - reasoning: (string, brief explanation of your choice)
    """
    
    logger.info(f"[OnboardAI][INTENT] Classifying input: {user_input[:100]}...")
    
    try:
        raw_response = await gemini_client.model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        
        data = json.loads(raw_response.text)
        intent_val = data.get("intent", "unknown")
        
        # Validate against enum
        try:
            intent_category = IntentCategory(intent_val)
        except ValueError:
            intent_category = IntentCategory.UNKNOWN

        logger.info(f"[OnboardAI][INTENT] LLM Result: {intent_category} (conf: {data.get('confidence', 0.0)})")
        
        return IntentClassificationResult(
            intent=intent_category,
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning", "No context provided")
        )
        
    except Exception as e:
        logger.error(f"[OnboardAI][INTENT] LLM Classification failed: {e}")
        return IntentClassificationResult(
             intent=IntentCategory.UNKNOWN,
             confidence=0.0,
             reasoning=f"Fallback due to model error: {str(e)}"
        )
