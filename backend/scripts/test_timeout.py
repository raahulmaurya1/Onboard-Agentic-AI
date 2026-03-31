import asyncio
import time
import httpx

async def main():
    start = time.time()
    print("Sending request to Orchestrator...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8000/api/v1/orchestrator/chat",
                json={
                    "user_message": "i want to open new account",
                    "session_ulid": None,
                    "source": "chat_send",
                    "current_state": {}
                },
                timeout=30.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error making request: {e}")
            
    end = time.time()
    print(f"Request took {end - start:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
