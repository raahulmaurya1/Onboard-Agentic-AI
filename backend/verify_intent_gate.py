import asyncio
import os
import json
from unittest.mock import MagicMock, AsyncMock, patch

# Mock settings and dependencies before importing orchestrate_session
os.environ["GEMINI_API_KEY"] = "test_key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Mock redis_client and other services
import app.storage.redis as redis_mod
redis_mod.redis_client = AsyncMock()
redis_mod.redis_client.get = AsyncMock(return_value=None) # No intent in Redis

from app.agents.decision_agent import orchestrate_session

async def test_intent_gate():
    print("Testing Intent Gate Enforcement...")
    
    # Mock DB session
    db = AsyncMock()
    
    # Mock scalar_one_or_none for user query
    db.execute = AsyncMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None) # User not in DB yet
    
    # Mock Gemini call
    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_instance = MockModel.return_value
        mock_chat = mock_instance.start_chat.return_value
        
        # Simulate LLM trying to hallucinate RENDER_KYC_UPLOAD
        mock_response = MagicMock()
        mock_response.parts = [MagicMock(function_call=None)]
        mock_response.text = json.dumps({
            "ui_action": "RENDER_KYC_UPLOAD",
            "agent_message": "Email verified! Let's upload your documents.",
            "data_required": ["kyc_docs"],
            "session_ulid": "01KKTEST"
        })
        mock_chat.send_message.return_value = mock_response
        
        # Run orchestrator
        result = await orchestrate_session(
            message="123456",
            session_ulid="01KKTEST",
            current_state={"email": "test@example.com"},
            source="email_verify_otp",
            db=db
        )
        
        print(f"Orchestrator Result: {json.dumps(result, indent=2)}")
        
        if result["ui_action"] == "RENDER_CHAT" and "intent" in result["data_required"]:
            print("SUCCESS: Intent gate enforced correctly.")
        else:
            print("FAILURE: Orchestrator failed to enforce intent gate.")

if __name__ == "__main__":
    asyncio.run(test_intent_gate())
