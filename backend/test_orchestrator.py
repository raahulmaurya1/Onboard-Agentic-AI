import asyncio
import httpx
import json

async def test_chat():
    base_url = 'http://127.0.0.1:8000/api/v1/orchestrator/chat'
    payload = {
        "user_message": "Hi, I want to open a new savings account. My phone number is +919999999999.",
        "session_ulid": None,
        "current_state": {}
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Sending request to {base_url} with payload: {payload}")
        res = await client.post(base_url, json=payload)
        print(f"Status: {res.status_code}")
        try:
             print(json.dumps(res.json(), indent=2))
        except:
             print(res.text)

if __name__ == "__main__":
    asyncio.run(test_chat())
