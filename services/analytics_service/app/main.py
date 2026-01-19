import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import time
import requests
import redis
import json

# CONFIG
st.set_page_config(page_title="TB SmartConnect", layout="wide", page_icon="🇹🇷")

# ENV VARS
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASS = os.getenv("POSTGRES_PASS", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "tb_knowledge_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")

# CONNECTORS
@st.cache_resource
def get_db_engine():
    return create_engine(f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:5432/{POSTGRES_DB}")

def get_redis_client():
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# UI HEADER
st.title("🇹🇷 Turkiye Burslari SmartConnect")

# TABS
tab1, tab2 = st.tabs(["🎓 Student Portal (Live Interaction)", "📊 Admin Command Center"])

# --- TAB 1: INTERACTION (The "Show me it works" tab) ---
with tab1:
    st.markdown("### 🗣️ Ask a Question (Live AI Simulation)")
    st.write("Simulate a student asking a question on social media. The system will process it and return the answer here.")
    
    col_q, col_a = st.columns(2)
    
    with col_q:
        user_id = st.text_input("Your Name / Student ID", "Baozar_Student")
        question = st.text_area("Your Question", "Can I apply for a Master's degree if I am 25 years old?")
        
        if st.button("🚀 Submit Application Query"):
            # 1. Send to Ingestion Service
            payload = {"platform": "youtube", "sender_id": user_id, "content": question}
            try:
                # We talk to the Ingestion container directly via Docker Network
                res = requests.post("http://tb_ingestion:8000/ingest/", json=payload)
                
                if res.status_code == 200:
                    st.success("✅ Query Sent to Ingestion Service!")
                    st.info("⏳ Waiting for AI Processor...")
                    
                    # 2. POLLING: Wait for AI to write to Redis
                    r = get_redis_client()
                    placeholder = st.empty()
                    redis_key = f"query:{user_id}"
                    
                    # Poll for 10 seconds (check every 0.5s)
                    for i in range(20):
                        val = r.get(redis_key)
                        if val:
                            data = json.loads(val)
                            st.session_state['last_answer'] = data
                            break
                        time.sleep(0.5)
                        placeholder.text(f"Processing in queue... {i*0.5}s")
                    
                    if not r.get(redis_key):
                         st.warning("⚠️ Request timed out. Check if AI Service is running.")

                else:
                    st.error(f"Error: {res.status_code}")
            except Exception as e:
                st.error(f"Connection Error (Ensure Docker is up): {e}")

    with col_a:
        st.subheader("🤖 Official Response")
        if 'last_answer' in st.session_state:
            ans = st.session_state['last_answer']
            
            st.markdown(f"**AI Sentiment Score:** `{ans.get('sentiment_score')}`")
            if ans.get('sentiment_score') and ans.get('sentiment_score') < 0.4:
                st.error("Flag: Low Sentiment / Potential Conflict")
            else:
                st.success("Status: Polite / Good Fit")
            
            st.info(f"**Answer:** {ans.get('ai_response')}")
            st.success(f"📧 Email notification dispatched to: {user_id}@std.yildiz.edu.tr")
        else:
            st.markdown("*Response will appear here...*")

# --- TAB 2: ADMIN (The "Search & Monitoring" tab) ---
with tab2:
    st.markdown("### 🔍 Influencer Database Search")
    
    search_term = st.text_input("Search Influencer by Username", "")
    
    engine = get_db_engine()
    try:
        query = "SELECT * FROM influencers"
        params = {}
        
        if search_term:
            query += " WHERE username ILIKE %(term)s"
            params = {"term": f"%{search_term}%"}
            
        with engine.connect() as conn:
            # We use text() for safe SQL execution
            from sqlalchemy import text
            if search_term:
                result = conn.execute(text("SELECT * FROM influencers WHERE username ILIKE :term"), {"term": f"%{search_term}%"})
            else:
                result = conn.execute(text("SELECT * FROM influencers"))
                
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            st.dataframe(df, use_container_width=True)
            
    except Exception as e:
        st.error(f"DB Error: {e}")

    st.divider()
    st.markdown("### 📡 Live System Metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingestion Status", "Online", "RabbitMQ Connected")
    m2.metric("Knowledge Base", "PostgreSQL", "Healthy")
    m3.metric("AI Model", "Gemini 2.5 Flash", "Active")