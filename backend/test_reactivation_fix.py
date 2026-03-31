import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.decision_agent import orchestrate_session
from app.agents.intent_agent import IntentCategory, IntentClassificationResult

async def test_reactivation_fix():
    # Mock DB session
    db = AsyncMock()
    
    # Mock classify_intent to avoid rate limit/API call
    mock_classification = IntentClassificationResult(
        intent=IntentCategory.REACTIVATION,
        confidence=1.0,
        reasoning="User explicitly asked for reactivation"
    )
    
    with patch("app.agents.intent_agent.classify_intent", return_value=mock_classification), \
         patch("app.agents.decision_agent.redis_client", new_callable=AsyncMock) as mock_redis, \
         patch("app.agents.decision_agent.get_dynamic_state", return_value={"phoneVerified": True, "emailVerified": True}):
        
        mock_redis.get.return_value = None # No lifecycle flag initially
        
        # Mock current state - verified user
        session_ulid = "01JK..."
        current_state = {
            "phoneVerified": True,
            "emailVerified": True,
            "intent": None,
            "source": "account_selection"
        }
        
        # Message indicating reactivation
        message = "I want to reactivate my account"
        
        print(f"Testing message: '{message}' with source='account_selection'")
        
        # Call the orchestrator
        result = await orchestrate_session(
            message=message,
            session_ulid=session_ulid,
            current_state=current_state,
            db=db,
            source="account_selection"
        )
        
        print(f"Result UI Action: {result.get('ui_action')}")
        print(f"Result Message: {result.get('agent_message')}")
        print(f"Result Data Required: {result.get('data_required')}")
        
        assert result.get("ui_action") == "RENDER_CHAT"
        assert "account_id" in result.get("data_required", [])
        assert "Account Reactivation" in result.get("agent_message")
        
        print("\nSUCCESS: Reactivation intent correctly triggers Account ID request during account selection!")

if __name__ == "__main__":
    asyncio.run(test_reactivation_fix())
