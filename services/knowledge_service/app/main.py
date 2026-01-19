from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os

app = FastAPI(title="TB SmartConnect - Knowledge Service")

# CONFIG
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASS = os.getenv("POSTGRES_PASS", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "tb_knowledge_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

# DATABASE SETUP
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MODELS (SQL Tables)
class Influencer(Base):
    """Stores data about Student Influencers"""
    __tablename__ = "influencers"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    platform = Column(String)
    follower_count = Column(Integer)
    is_tb_scholar = Column(Boolean, default=True)

class FAQ(Base):
    """Stores Official YTB Answers"""
    __tablename__ = "faqs"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String)
    answer = Column(String)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ROUTES
@app.get("/")
def health_check():
    return {"status": "Knowledge Service Connected to Postgres"}

@app.post("/influencers/")
def register_influencer(username: str, platform: str, followers: int, db: Session = Depends(get_db)):
    db_influencer = Influencer(username=username, platform=platform, follower_count=followers)
    db.add(db_influencer)
    db.commit()
    db.refresh(db_influencer)
    return {"status": "Success", "id": db_influencer.id}

@app.get("/influencers/{username}")
def get_influencer(username: str, db: Session = Depends(get_db)):
    influencer = db.query(Influencer).filter(Influencer.username == username).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return influencer