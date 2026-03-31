from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection details should come from environment variables in production
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost:5432/bank_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
