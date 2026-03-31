import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.decision_agent import orchestrate_session
from app.agents.intent_agent import IntentCategory, IntentClassificationResult

async def test_lifecycle_full_flow():
    db = AsyncMock()
    session_ulid = "TEST_SESSION_123"
    
    # --- PHASE 1: Genesis - Detect Intent ---
    print("\n--- PHASE 1: Genesis ---")
    message = "I want to reactivate my account"
    mock_intent = IntentClassificationResult(intent=IntentCategory.REACTIVATION, confidence=1.0, reasoning="test")
    
    with patch("app.agents.intent_agent.classify_intent", return_value=mock_intent), \
         patch("app.agents.decision_agent.redis_client", new_callable=AsyncMock) as mock_redis, \
         patch("app.agents.decision_agent.get_dynamic_state", return_value={"phoneVerified": False}):
        
        mock_redis.exists.return_value = False
        
        result = await orchestrate_session(message, session_ulid, {}, db)
        print(f"Agent Message: {result['agent_message']}")
        assert "Account Number (ID)" in result["agent_message"]
        # Verify transient flag set
        mock_redis.setex.assert_called_with(f"lifecycle_awaiting_id:{session_ulid}", 600, "reactivation")

    # --- PHASE 2: ID Validation & Data Injection ---
    print("\n--- PHASE 2: ID Validation ---")
    message = "ACT_001"
    mock_user = MagicMock()
    mock_user.id = "ACT_001"
    mock_user.phone = "+919999999999"
    mock_user.email = "test@example.com"
    mock_user.account_type = "retail_savings"
    
    with patch("app.agents.decision_agent.redis_client", new_callable=AsyncMock) as mock_redis, \
         patch("app.agents.decision_agent.get_dynamic_state", return_value={"phoneVerified": False}), \
         patch("app.agents.lifecycle_agent.LifecycleOrchestrator.lookup_account", return_value=mock_user), \
         patch("app.services.otp_service.send_phone_otp", new_callable=AsyncMock) as mock_otp:
        
        # Mock Redis exists to return True for awaiting_id
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = b"reactivation"
        
        result = await orchestrate_session(message, session_ulid, {}, db)
        
        print(f"Action: {result['ui_action']}")
        print(f"Message: {result['agent_message']}")
        
        assert result["ui_action"] == "RENDER_PHONE_AUTH"
        assert "****" in result["agent_message"] # Verify masking
        
        # Verify Task 1, 2, 3: MANDATORY Schema for Lifecycle OTP
        ed = result["extracted_data"]
        assert ed["contact"] == "+919999999999"
        assert ed["masked_contact"] == "*********9999"
        assert ed["otp_expiry"] == 180              # Fixes 00:00 timer
        assert ed["is_otp_sent"] is True           # Enables Verify button
        assert ed["otp_status"] == "sent"
        
        assert result["data_required"] == ["otp"]
        
        # Verify Task 3: State Sync for Verify Button
        assert result["current_state"]["contact"] == "+919999999999"
        assert result["current_state"]["phone"] == "+919999999999"

        # Verify OTP triggered
        mock_otp.assert_called_once()
        # Verify session ID hijack (or injection)
        assert result["session_ulid"] == "ACT_001"

    # --- PHASE 2.1: Phone Verification -> Auto-Email ---
    print("\n--- PHASE 2.1: Phone Verification -> Auto-Email ---")
    message = "123456" # OTP
    mock_user = MagicMock()
    mock_user.id = "ACT_001"
    mock_user.phone = "+919999999999"
    mock_user.email = "test@example.com"
    mock_user.account_type = "retail_savings"
    
    with patch("app.agents.decision_agent.redis_client", new_callable=AsyncMock) as mock_redis, \
         patch("app.agents.decision_agent.verify_phone_otp", return_value={"pending_session_id": "ACT_001"}), \
         patch("app.services.otp_service.send_email_otp", new_callable=AsyncMock) as mock_email_otp:
        
        # Mock Redis lifecycle flags
        mock_redis.get.side_effect = lambda k: {
            f"lifecycle_flow:ACT_001": b"reactivation",
            f"pending_auth:ACT_001": json.dumps({"phone": "+919999999999"}).encode('utf-8')
        }.get(k)
        
        # Mock DB user retrieval
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = mock_result
        
        result = await orchestrate_session(message, "ACT_001", {"source": "phone_verify_otp"}, db)
        
        print(f"Action: {result['ui_action']}")
        print(f"Agent Message: {result['agent_message']}")
        
        assert result["ui_action"] == "RENDER_EMAIL_AUTH"
        assert result["data_required"] == ["otp"]
        assert "test@example.com" in result["agent_message"]
        
        # Verify Task 1: Initialization state for Email
        assert result["extracted_data"]["contact"] == "test@example.com"
        assert result["extracted_data"]["is_otp_sent"] is True
        assert result["extracted_data"]["otp_expiry"] == 180
        
        # Verify Email OTP triggered
        mock_email_otp.assert_called_once_with("test@example.com", pending_session_id="ACT_001")
    print("\n--- PHASE 3: Evaluator Reset & Bypass ---")
    session_ulid = "ACT_001"
    
    # Simulate being in Step 3 (Intent Selection) after Email OTP
    with patch("app.agents.decision_agent.redis_client", new_callable=AsyncMock) as mock_redis, \
         patch("app.agents.decision_agent.get_dynamic_state", return_value={"phoneVerified": True, "emailVerified": True, "kycUploaded": True, "faceVerified": True}):
        
        # Mock Redis lifecycle flags
        mock_redis.get.side_effect = lambda k: {
            f"lifecycle_flow:{session_ulid}": b"reactivation",
            f"lifecycle_account_type:{session_ulid}": b"retail_savings",
            f"lifecycle_awaiting_id:{session_ulid}": None
        }.get(k)
        mock_redis.exists.return_value = False
        
        # Mock DB user
        mock_user = MagicMock()
        mock_user.account_type = "retail_savings"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = mock_result
        
        result = await orchestrate_session("hi", session_ulid, {}, db)
        
        print(f"Action: {result['ui_action']}")
        print(f"Data Required: {result['data_required']}")
        
        # Should bypass Step 3 and go to Step 4 (KYC) because flags were reset to False
        assert result["ui_action"] == "RENDER_KYC_UPLOAD"
        assert "aadhaar" in result["data_required"]

    print("\nSUCCESS: All lifecycle flow requirements verified!")

if __name__ == "__main__":
    asyncio.run(test_lifecycle_full_flow())
