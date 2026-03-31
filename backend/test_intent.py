import asyncio
import os
from app.agents.intent_agent import classify_intent, IntentCategory

async def test_intent():
    test_inputs = [
        "I want to reactivate my account",
        "reactivate account",
        "my account is dormant, please help",
        "I want to open a new savings account",
        "re-verify my KYC"
    ]
    
    for text in test_inputs:
        result = await classify_intent(text)
        print(f"Input: {text}")
        print(f"Intent: {result.intent}")
        print(f"Reasoning: {result.reasoning}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_intent())
