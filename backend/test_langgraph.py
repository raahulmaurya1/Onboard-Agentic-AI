from app.orchestration.onboarding_flow import run_agent
from app.db.schemas import OnboardingState

def test_routing():
    # Test low risk
    state = OnboardingState(session_ulid="123", current_step="start", risk_score=20.0)
    result = run_agent(state)
    assert result["status"] == "approved"
    print("Test 1 (Low Risk - Auto Approve): PASS")
    
    # Test medium risk
    state2 = OnboardingState(session_ulid="124", current_step="start", risk_score=50.0)
    result2 = run_agent(state2)
    assert result2["status"] == "retry"
    print("Test 2 (Medium Risk - Retry Upload): PASS")
    
    # Test high risk
    state3 = OnboardingState(session_ulid="125", current_step="start", risk_score=90.0)
    result3 = run_agent(state3)
    assert result3["status"] == "escalate"
    print("Test 3 (High Risk - Escalate): PASS")

if __name__ == "__main__":
    test_routing()
