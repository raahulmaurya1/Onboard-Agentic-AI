from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class AgentContext(Base):
    __tablename__ = "agent_context"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True) # ULID or internal UUID
    session_id: Mapped[str] = mapped_column(String, ForeignKey("user_initial.id"), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    
    # Gemini text-embedding models natively return 768 dimensions
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
