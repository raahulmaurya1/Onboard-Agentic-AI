import asyncio
import base64
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Import your database and models
from app.db.base import AsyncSessionLocal
from app.db.models.user import UserInitial, AdditionalInfo
from app.db.models.session import OnboardingSession
from app.db.models.document import UserDocument
from app.storage.minio import save_to_minio

async def seed_data():
    user_id = "01TESTREVIEW00000000000001"
    session_id = "sess_01TESTREVIEW0000000001"
    
    # 1. Create a fake tiny red image (1x1 pixel base64) to upload to MinIO
    red_pixel_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    image_bytes = base64.b64decode(red_pixel_b64)
    file_path = save_to_minio("documents", "test_passport_front.png", image_bytes, "image/png")
    
    print(f"Uploaded test image to MinIO: {file_path}")

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
                phone="+1 555-0999",
                email="test.reviewer@example.com",
                name="Alex Test Review",
                father_name="Senior Test",
                address="404 Mockingbird Lane",
                dob="1990-05-20",  # String since dob is Column(String)
                account_type="standard",
                status="pending_review",
                face_verified=False
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
                id="addinfo_01TESTREVIEW01",
                session_ulid=user_id,
                data={
                    "pep_status": "true",
                    "sanctions_hit": "false",
                    "source_of_funds": "Business Income",
                    "estimated_annual_income": "$150,000"
                }
            )
            db.add(info)
            
            # 5. Insert UserDocument
            doc1 = UserDocument(
                session_id=session_id,
                file_type="image/png",
                file_url=file_path,
                status="verified"
            )
            db.add(doc1)
            
            await db.commit()
            print("==================================================")
            print(" SUCCESS: Database Seeded!")
            print(f" User ID for testing: {user_id}")
            print("==================================================")
            
            # Note: Risk evaluation flags are normally saved in the vector store, 
            # but since get_review_data accepts risk_flags from the kwargs or empty,
            # we will just see empty flags if we don't mock the vector entry.
            # But the UI will still render perfectly!
            
        except Exception as e:
            await db.rollback()
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(seed_data())
