from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy import text
from app.db.base import Base

class OnboardingSession(Base):
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, index=True) # Exclusively tracks ULID
    user_id = Column(String, ForeignKey("user_initial.id"), index=True, nullable=False)
    
    # Mathematical TTL: Hard-locked exactly 30 minutes forward across PostgreSQL.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), server_default=text("NOW() + INTERVAL '30 minutes'"), nullable=False)
