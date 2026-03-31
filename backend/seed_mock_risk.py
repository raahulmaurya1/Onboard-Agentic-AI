import asyncio
import base64
import os
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.db.models.user import UserInitial, AdditionalInfo
from app.db.models.session import OnboardingSession
from app.db.models.document import UserDocument
from app.storage.minio import save_to_minio
from app.db.vector_store import store_risk_data

async def seed_risk_data():
    user_id = "01RISKREVIEW00000000000000"
    session_id = "sess_01RISKREVIEW0000000000"
    
    # 1. Create a fake tiny image to upload to MinIO
    red_pixel_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    image_bytes = base64.b64decode(red_pixel_b64)
    file_path = save_to_minio("documents", "risk_passport.png", image_bytes, "image/png")
    
    # 1b. Create a dummy video file for MinIO (just 1 byte of data to simulate file existence)
    video_bytes = b"\x00\x00\x00\x1cftypisom"
    video_path = save_to_minio("documents", "risk_liveness_check.mp4", video_bytes, "video/mp4")
    
    async with AsyncSessionLocal() as db:
        try:
            # Clean up old test data if it exists so we can re-run
            await db.execute(text(f"DELETE FROM user_documents WHERE session_id = '{session_id}'"))
            await db.execute(text(f"DELETE FROM additional_info WHERE session_ulid = '{user_id}'"))
            await db.execute(text(f"DELETE FROM sessions WHERE session_id = '{session_id}'"))
            await db.execute(text(f"DELETE FROM user_initial WHERE id = '{user_id}'"))
            
            # 2. Insert UserInitial (pending_review)
            user = UserInitial(
                id=user_id,
                phone="+1 555-8888",
                email="risk_flagged@example.com",
                name="Suspicious Sam",
                father_name="Unknown",
                address="High Risk Country Route 9",
                dob="1970-01-01",
                aadhar_id="1234-5678-9012",
                pan_id="ABCDE1234F",
                account_type="standard",
                status="pending_review",
                face_verified=False,
                verified_data={
                    "extracted_dob": "1970-01-01",
                    "extracted_name": "Samuel L Smith",
                    "ocr_confidence": 0.35,
                    "document_tampered": True
                },
                raw_archive={
                    "ip_address": "192.168.1.99",
                    "device_model": "Unknown Android"
                }
            )
            db.add(user)
            await db.flush()
            
            # 3. Insert OnboardingSession
            session = OnboardingSession(
                session_id=session_id,
                user_id=user_id,
            )
            db.add(session)
            await db.flush()
            
            # 4. Insert AdditionalInfo
            info = AdditionalInfo(
                id="addinfo_RISK_01",
                session_ulid=user_id,
                data={
                    "pep_status": "true",
                    "sanctions_hit": "true",
                    "source_of_funds": "Cash Deposits",
                    "estimated_annual_income": "$1,000,000"
                }
            )
            db.add(info)
            
            # 5. Insert UserDocument (Image)
            doc1 = UserDocument(
                session_id=session_id,
                file_type="image/png",
                file_url=file_path,
                status="failed_verification"
            )
            db.add(doc1)
            
            # 5b. Insert UserDocument (Video)
            doc2 = UserDocument(
                session_id=session_id,
                file_type="video/mp4",
                file_url=video_path,
                status="failed_liveness"
            )
            db.add(doc2)
            
            await db.commit()
            
            # 6. NOW STORE THE RISK FLAGS using the actual vector_store function!
            # The API will query risk_evaluations searching by request_id (user_id)
            await store_risk_data(
                request_id=user_id,
                merged={
                    "face_similarity": 30.0,
                    "blink_count": 0,
                    "otp_retries": 9,
                    "industry_nic": "9999",
                    "expected_turnover": "1000000000",
                    "ip_geolocation_country": "UNKNOWN",
                    "phone_country": "US",
                    "aadhaar_name": "Sam Smith",
                    "pan_name": "Samuel L Smith",
                },
                age=55,
                matrix_score=195,
                llm_additional_risk=35,
                total_score=230,
                category="MANUAL_REVIEW",
                risk_flags=[
                    "High Risk Jurisdiction Flags Triggered", 
                    "Face Verification Mismatch (> 50% deviation)",
                    "Sanctions Hit Watchlist Match"
                ],
                llm_flags=[
                    "LLM Alert: Severe AML Risk Detected",
                    "LLM Alert: Potential synthetic identity fraud"
                ]
            )
            
            print("==================================================")
            print(" SUCCESS: Risk Flagged Database Profile Seeded!")
            print(f" User ID for testing: {user_id}")
            print("==================================================")
            
        except Exception as e:
            await db.rollback()
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(seed_risk_data())
