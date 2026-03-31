import asyncio
import os
import json
from unittest.mock import MagicMock, AsyncMock, patch

# Mock settings and dependencies
os.environ["GEMINI_API_KEY"] = "test_key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import app.storage.redis as redis_mod
redis_mod.redis_client = AsyncMock()

# Setup Redis mock values
redis_db = {}
async def mock_redis_get(key):
    return redis_db.get(key)
async def mock_redis_setex(key, time, val):
    redis_db[key] = val

redis_mod.redis_client.get.side_effect = mock_redis_get
redis_mod.redis_client.setex.side_effect = mock_redis_setex

# Mock sync redis for the safety gate
with patch("app.db.redis_client.redis_client") as mock_sync_redis:
    def sync_get(key):
        return redis_db.get(key)
    mock_sync_redis.get.side_effect = sync_get

    from app.agents.decision_agent import orchestrate_session

    async def test_intent_extraction_flow():
        print("Testing Intent Extraction Flow...")
        
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
        
        # 1. Simulate user providing intent "Retail account"
        # The LLM should call 'classify_user_intent'
        
        with patch("google.generativeai.GenerativeModel") as MockModel:
            mock_instance = MockModel.return_value
            mock_chat = mock_instance.start_chat.return_value
            
            # First response: LLM calls classify_user_intent
            fc_response = MagicMock()
            fc_part = MagicMock()
            fc_part.function_call.name = "classify_user_intent"
            fc_part.function_call.args = {"user_message": "Retail account"}
            fc_response.parts = [fc_part]
            
            # Second response: LLM sees tool result and returns RENDER_KYC_UPLOAD
            final_response = MagicMock()
            final_response.parts = [MagicMock(function_call=None)]
            final_response.text = json.dumps({
                "ui_action": "RENDER_KYC_UPLOAD",
                "agent_message": "Account set to Retail. Please upload documents.",
                "data_required": [],
                "session_ulid": "01KKTEST"
            })
            
            mock_chat.send_message.side_effect = [fc_response, final_response]
            
            # Run orchestrator
            # Note: We patch classify_intent here because it's called inside handle_tool_call
            with patch("app.agents.decision_agent.classify_intent", new_callable=AsyncMock) as mock_classify:
                mock_classify.return_value = MagicMock(intent=MagicMock(value="RETAIL"), checklist=["PAN"])
                
                result = await orchestrate_session(
                    message="Retail account",
                    session_ulid="01KKTEST",
                    current_state={"email": "test@example.com"},
                    db=db
                )
            
            print(f"Orchestrator Result: {json.dumps(result, indent=2)}")
            print(f"Redis State: {redis_db}")
            
            # Verification
            if result["ui_action"] == "RENDER_KYC_UPLOAD":
                print("SUCCESS: Orchestrator correctly advanced to KYC Upload after intent extraction.")
            else:
                print("FAILURE: Orchestrator still stuck in intent loop.")

    if __name__ == "__main__":
        asyncio.run(test_intent_extraction_flow())
