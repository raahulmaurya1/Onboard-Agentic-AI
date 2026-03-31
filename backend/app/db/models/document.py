from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base

class UserDocument(Base):
    __tablename__ = "user_documents"

    # Crash-Proofing: Independent auto-incrementing ID to prevent IntegrityError on multiple uploads
    document_id = Column(Integer, primary_key=True, autoincrement=True, index=True) 
    
    # Strict cascading session tie 
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), index=True, nullable=False)
    
    # Store standard MinIO references natively!
    file_type = Column(String, nullable=False) 
    file_url = Column(String, nullable=False)   
    status = Column(String, default="PENDING")
    
    # Restored JSON Extraction blob for manual review UI
    extracted_data = Column(JSON, nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
