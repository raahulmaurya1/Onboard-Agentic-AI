import asyncio
import httpx
import json

async def test_full_auth_flow():
    base_url = 'http://127.0.0.1:8000/api/v1/orchestrator/chat'
    # Use a mock phone and email
    phone = "+919999999990"
    email = "test@example.com"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n--- 1. Send Phone OTP ---")
        payload = {
            "user_message": "SYSTEM: TRIGGER_OTP_SEND",
            "session_ulid": None,
            "source": "phone_send_otp",
            "current_state": {"source": "phone_send_otp", "contact": phone, "phone": phone}
        }
        res = await client.post(base_url, json=payload)
        data = res.json()
        print(data)
        session_ulid = data["session_ulid"]
        assert data["ui_action"] == "RENDER_PHONE_AUTH"
        
        # We must get the OTP directly from Redis to proceed
        # Let's just grab it from Redis using a quick subprocess
        print("\n--- 2. Fetch Phone OTP from Redis ---")
        import subprocess
        proc = subprocess.run(["docker", "exec", "bank_redis", "redis-cli", "GET", f"phone_otp:{phone}"], 
                              capture_output=True, text=True)
        phone_otp = proc.stdout.strip()
        print(f"Phone OTP: {phone_otp}")
        
        print("\n--- 3. Submit Phone OTP ---")
        payload = {
            "user_message": f"Phone OTP: {phone_otp}",
            "session_ulid": session_ulid,
            "source": "phone_verify_otp",
            "current_state": {"source": "phone_verify_otp", "otp": phone_otp}
        }
        res = await client.post(base_url, json=payload)
        data = res.json()
        print(data)
        session_ulid = data["session_ulid"]
        assert data["ui_action"] == "RENDER_EMAIL_AUTH"
        
        print("\n--- 4. Send Email OTP ---")
        payload = {
            "user_message": "SYSTEM: TRIGGER_OTP_SEND",
            "session_ulid": session_ulid,
            "source": "email_send_otp",
            "current_state": {"source": "email_send_otp", "contact": email, "email": email}
        }
        res = await client.post(base_url, json=payload)
        data = res.json()
        print(data)
        assert data["ui_action"] == "RENDER_EMAIL_AUTH"
        
        print("\n--- 5. Fetch Email OTP from Redis ---")
        proc = subprocess.run(["docker", "exec", "bank_redis", "redis-cli", "GET", f"email_otp:{email}"], 
                              capture_output=True, text=True)
        email_otp = proc.stdout.strip()
        print(f"Email OTP: {email_otp}")
        
        print("\n--- 6. Submit Email OTP ---")
        payload = {
            "user_message": f"Email OTP: {email_otp}",
            "session_ulid": session_ulid,
            "source": "email_verify_otp",
            "current_state": {"source": "email_verify_otp", "otp": email_otp}
        }
        res = await client.post(base_url, json=payload)
        data = res.json()
        print(data)
        assert data["ui_action"] == "RENDER_CHAT"
        
        print("\n✅ Verification SUCCESS: Full E2E Auth completed!")

if __name__ == "__main__":
    asyncio.run(test_full_auth_flow())
