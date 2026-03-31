import asyncio
import httpx
from sqlalchemy.future import select
from app.db.base import AsyncSessionLocal
from app.db.models.user import UserInitial
from app.db.models.session import OnboardingSession
from sqlalchemy import text
import json

async def insert_test_data():
    async with AsyncSessionLocal() as db:
        uid = '01KK7KZWV8GKCPMQ6RF4EE55SR_TEST2'
        
        user = await db.execute(select(UserInitial).where(UserInitial.id == uid))
        if not user.scalars().first():
            
            # The User's exact requested JSON
            user_json = {
              "session_id": "01KK7KZWV8GKCPMQ6RF4EE55SR", 
              "status": "PENDING_REVIEW", 
              "extracted_data": {
                "files": [{"filename": "AADHAR.pdf", "url": "temp/01KK7KZWV8GKCPMQ6RF4EE55SR/AADHAR.pdf", "mime_type": "application/pdf"}, {"filename": "PAN.pdf", "url": "temp/01KK7KZWV8GKCPMQ6RF4EE55SR/PAN.pdf", "mime_type": "application/pdf"}], 
                "validation": {
                  "valid": False, 
                  "flags": ["DOB_MISMATCH"], 
                  "combined_data": {
                    "Aadhaar_name": "Rahul Maurya", 
                    "Aadhaar_father_name": "Radheshyam Maurya Koiri", 
                    "Aadhaar_dob": "2004", 
                    "Aadhaar_address": "C/O: Radheshyam Maurya Koiri, ROOM NO-123, NBH HOSTEL, C V RAMAN GLOBAL UNIVERSITY CAMPUS, BIDYANAGAR, PO-JANLA, Mahura, PO: Mahura, DIST: Khorda, Odisha - 752054", 
                    "Aadhaar_id_number": "404900000480", 
                    "PAN_name": "RAHUL MAURYA", 
                    "PAN_father_name": "RADHESHYAM MAURYA KOIRI", 
                    "PAN_dob": "17/01/2004", 
                    "PAN_id_number": "KIWPM0001J"
                  }
                }
              }
            }
            
            new_user = UserInitial(
                id=uid,
                phone='+915555555556',
                email='freeze2@example.com',
                status='VERIFIED',
                verified_data=user_json
            )
            db.add(new_user)
            await db.flush()
            db.add(OnboardingSession(session_id=uid, user_id=uid, expires_at=text("NOW() + INTERVAL '1 hour'")))
            await db.commit()
        return uid

async def test_freeze():
    uid = await insert_test_data()
    print(f'Test UID: {uid}')
    
    base_url = 'http://127.0.0.1:8000/api/finalize-documents'
    headers = {'Authorization': f'Bearer {uid}'}
    
    async with httpx.AsyncClient() as client:
        res = await client.post(base_url, headers=headers)
        print(f'Status: {res.status_code}')
        try:
             print(json.dumps(res.json(), indent=2))
        except:
             print(res.text)

asyncio.run(test_freeze())
