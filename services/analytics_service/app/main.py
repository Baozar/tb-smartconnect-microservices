import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import time
import requests
import redis
import json

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

st.title("🇹🇷 Turkiye Burslari SmartConnect")

tab1, tab2 = st.tabs(["🎓 Student Portal", "📊 Admin Analytics"])

# --- TAB 1: STUDENT PORTAL ---
with tab1:
    col_q, col_a = st.columns(2)
    with col_q:
        st.subheader("Ask a Question")
        # NEW: Platform Selection
        platform_choice = st.radio("Select Source:", ["YouTube", "Instagram"], horizontal=True)
        user_id = st.text_input("Your Name / ID", "Baozar_Student")
        
        # Rate Limit Logic
        r = get_redis_client()
        rate_key = f"rate_limit:{user_id}"
        current = r.get(rate_key)
        count = int(current) if current else 0
        
        if count >= 5:
            st.error(f"🚫 Limit Reached ({count}/5).")
            disable_submit = True
        else:
            st.info(f"⚡ Daily Quota: {count} / 5 used")
            st.progress(count / 5)
            disable_submit = False

        question = st.text_area("Question", "Is the scholarship open for PhD?")
        
        if st.button("Submit", disabled=disable_submit):
            payload = {"platform": platform_choice.lower(), "sender_id": user_id, "content": question}
            try:
                requests.post("http://tb_ingestion:8000/ingest/", json=payload)
                st.success("✅ Sent!")
                
                # Poll Redis for Answer
                placeholder = st.empty()
                for i in range(20):
                    val = r.get(f"query:{user_id}")
                    if val:
                        st.session_state['last_answer'] = json.loads(val)
                        st.rerun()
                        break
                    time.sleep(0.5)
                    placeholder.text(f"Thinking... {i*0.5}s")
            except Exception as e:
                st.error(f"Error: {e}")

    with col_a:
        st.subheader("Response")
        if 'last_answer' in st.session_state:
            ans = st.session_state['last_answer']
            
            # 1. Handle Spam/Blocked
            if ans.get("category") == "spam":
                st.error("⛔ Request Blocked")
                st.write(ans.get("ai_response"))
            
            # 2. Handle Success
            else:
                # Display Sentiment
                score = ans.get("sentiment_score", 0.5)
                if score and score > 0.7:
                    st.caption(f"✨ Positive Sentiment ({score})")
                
                # The Answer
                st.info(f"**AI Answer:** {ans.get('ai_response')}")
                
                # --- THE MISSING LINE RESTORED ---
                st.success(f"📨 Email notification dispatched to: {user_id}@std.yildiz.edu.tr")

# --- TAB 2: ADMIN ANALYTICS ---
with tab2:
    st.markdown("### 📈 Live Data Insights")
    
    engine = get_db_engine()
    
    # 1. LIVE METRICS (From Postgres History)
    try:
        with engine.connect() as conn:
            # Platform Stats
            df_logs = pd.read_sql("SELECT * FROM query_logs", conn)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Queries Processed", len(df_logs))
            
            # Pie Chart: Instagram vs YouTube
            if not df_logs.empty:
                st.subheader("Platform Distribution (YouTube vs Instagram)")
                # Count values in 'platform' column
                platform_counts = df_logs['platform'].value_counts()
                st.bar_chart(platform_counts)
            else:
                st.info("No data yet. Submit some questions!")

            st.divider()
            
            # 2. INFLUENCER MANAGEMENT (Add New)
            st.subheader("📢 Influencer Management")
            col_add, col_list = st.columns([1, 2])
            
            with col_add:
                st.markdown("**Add New Influencer**")
                new_user = st.text_input("Username")
                new_plat = st.selectbox("Platform", ["YouTube", "Instagram", "TikTok"])
                new_foll = st.number_input("Followers", min_value=0, step=100)
                
                if st.button("➕ Add to Registry"):
                    try:
                        # Call Knowledge Service API
                        res = requests.post(
                            "http://tb_knowledge:8002/influencers/", 
                            params={"username": new_user, "platform": new_plat, "followers": new_foll}
                        )
                        if res.status_code == 200:
                            st.success("Added!")
                            st.rerun()
                        else:
                            st.error("Failed.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            with col_list:
                st.markdown("**Current Registry**")
                df_inf = pd.read_sql("SELECT * FROM influencers", conn)
                st.dataframe(df_inf, use_container_width=True)

    except Exception as e:
        st.error(f"DB Error: {e}")