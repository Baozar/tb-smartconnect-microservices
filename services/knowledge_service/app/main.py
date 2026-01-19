from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from datetime import datetime
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

# --- MODELS (SQL Tables) ---
class Influencer(Base):
    __tablename__ = "influencers"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    platform = Column(String)
    follower_count = Column(Integer)
    is_tb_scholar = Column(Boolean, default=True)

class QueryLog(Base):
    """Stores every interaction for Analytics"""
    __tablename__ = "query_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    platform = Column(String) # YouTube / Instagram
    sender_id = Column(String)
    question = Column(String)
    category = Column(String)
    sentiment_score = Column(Float)

# Pydantic Model for Input
class LogCreate(BaseModel):
    platform: str
    sender_id: str
    question: str
    category: str
    sentiment_score: float

# Create tables
Base.metadata.create_all(bind=engine)

# DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---
@app.get("/")
def health_check():
    return {"status": "Knowledge Service Connected to Postgres"}

# Influencer Routes
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

# History Routes (New)
@app.post("/history/")
def log_query(log: LogCreate, db: Session = Depends(get_db)):
    db_log = QueryLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    return {"status": "Logged"}

@app.get("/history/")
def get_history(db: Session = Depends(get_db)):
    return db.query(QueryLog).all()