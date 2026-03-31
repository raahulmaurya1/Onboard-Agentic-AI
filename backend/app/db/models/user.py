from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class UserInitial(Base):
    __tablename__ = "user_initial"

    id = Column(String, primary_key=True, index=True) # Will store the ULID
    phone = Column(String, index=True, nullable=False)
    email = Column(String, index=True, nullable=True) # Scoped uniqueness managed by table_args
    status = Column(String, default="draft", nullable=False) # Long-lived TTL draft status for Idempotent lookups
    
    __table_args__ = (
        UniqueConstraint('phone', 'account_type', name='uq_phone_account_type'),
        UniqueConstraint('email', 'account_type', name='uq_email_account_type'),
    )
    
    # Store permanent verified document extraction data directly mapped to Identity
    verified_data = Column(JSON, nullable=True) # Volatile "Working Memory"
    
    # --- PHASE 2: FINALIZATION HYBRID COLUMNS (Active Truth) ---
    name = Column(String, nullable=True)
    father_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    aadhar_id = Column(String, nullable=True)
    pan_id = Column(String, nullable=True)
    
    # ReadOnly Immutable JSON Ledger
    raw_archive = Column(JSON, nullable=True)
    
    # ── PHASE 3: BIOMETRICS & PRODUCT SELECTION ──
    account_type = Column(String, nullable=True) # Retail, SME, etc.
    face_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    additional_info = relationship("AdditionalInfo", back_populates="user", uselist=False)

class AdditionalInfo(Base):
    __tablename__ = "additional_info"
    
    id = Column(String, primary_key=True, index=True) # Usually a ULID or UUID
    session_ulid = Column(String, ForeignKey("user_initial.id"), unique=True)
    data = Column(JSON, nullable=False) # Nested regulatory data
    
    # Relationships
    user = relationship("UserInitial", back_populates="additional_info")
