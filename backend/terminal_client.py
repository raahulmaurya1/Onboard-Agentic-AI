import httpx
import time
import sys

API_BASE = "http://127.0.0.1:8000/api/auth"

def main():
    print("="*60)
    print(" 🏦 AGENTIC BANK - TERMINAL ONBOARDING CLIENT ")
    print("="*60)
    
    # 1. Idempotent Data Acquisition
    phone = input("\nEnter Phone Number (e.g., +917991881238) : ").strip()
    email = input("Enter Email Address                     : ").strip()
    
    if not phone or not email:
        print("❌ Error: Phone and Email are required.")
        return

    print("\n[Client] Generating Dual-Channel OTPs via Server...")
    payload = {"phone": phone, "email": email}
    
    try:
        with httpx.Client() as client:
            res = client.post(f"{API_BASE}/send-otp", json=payload, timeout=10.0)
            
            if res.status_code != 200:
                print(f"❌ Server Error: {res.text}")
                return
                
            data = res.json()
            
            # --- The "Lookup-First" Idempotency Check ---
            if data.get("status") == "resumed":
                print("\n✅ MATCH FOUND! Session Resumed.")
                print(f"   ULID Generated/Found: {data['user_id']}")
                print(f"   Current Status      : {data['session_status']}")
                print("   (Skipping OTP MFA because you are already verified & saved!)")
                return
                
            # --- Dual-Channel Verification Triggered ---
            print(f"\n✅ {data['message']}")
            print(f"   (OTPs expire in {data['expires_in']} seconds)")
            print("\n" + "-"*60)
            print(" PLEASE CHECK YOUR PHONE AND EMAIL FOR THE 6-DIGIT CODES")
            print("-" * 60)
            
            # ASK THE USER NATIVELY IN THE TERMINAL
            phone_code = input("\n📱 Enter the SMS OTP   : ")
            email_code = input("📧 Enter the Email OTP : ")
            
            print("\n[Client] Validating MFA Gatekeeper...")
            verify_payload = {
                "phone": phone,
                "phone_code": phone_code,
                "email": email,
                "email_code": email_code
            }
            
            verify_res = client.post(f"{API_BASE}/verify-otp", json=verify_payload, timeout=10.0)
            
            if verify_res.status_code != 200:
                print(f"\n❌ Verification Failed! Server Response: {verify_res.text}")
                return
                
            verify_data = verify_res.json()
            
            # --- Persistence & Schema Architecture Verified ---
            print("\n" + "="*60)
            print(" ✅ SUCCESS: BANKING IDENTITY CREATED & VERIFIED!")
            print("="*60)
            print(f" 🔑 Secure Session ULID : {verify_data['user_id']}")
            print(f" 📞 Registered Phone    : {verify_data['phone']}")
            print(f" ✉️ Registered Email    : {verify_data['email']}")
            print(f" 💾 Saved as Active 'Draft' in PostgreSQL!")
            print("="*60 + "\n")
            
    except httpx.ConnectError:
        print("\n❌ Connection Error: Is Uvicorn running on 127.0.0.1:8000?")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")

if __name__ == "__main__":
    main()
