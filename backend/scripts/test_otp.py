import asyncio
import httpx
import time

async def main():
    start = time.time()
    print("Testing standard phone onboarding OTP trigger...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8000/api/v1/orchestrator/chat",
                json={
                    "user_message": "",
                    "session_ulid": "TESTSESSION123",
                    "source": "phone_send_otp",
                    "current_state": {"phone": "+917991881238"}
                },
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error making request: {e}")
            
    end = time.time()
    print(f"Test took {end - start:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
