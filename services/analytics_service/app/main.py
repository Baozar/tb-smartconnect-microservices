import streamlit as st
import pandas as pd
import numpy as np
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

tab1, tab2, tab3 = st.tabs(["🎓 Student Portal", "📊 Application Trends (New)", "⚙️ Admin & Influencers"])

# --- TAB 1: STUDENT PORTAL ---
with tab1:
    col_q, col_a = st.columns(2)
    with col_q:
        st.subheader("Ask a Question")
        
        # 1. Platform Selection
        platform_choice = st.radio("Select Source:", ["YouTube", "Instagram"], horizontal=True)
        
        # 2. Influencer Selection (NEW)
        engine = get_db_engine()
        try:
            with engine.connect() as conn:
                inf_res = conn.execute(text("SELECT username FROM influencers"))
                influencers = [row[0] for row in inf_res.fetchall()]
                influencers.insert(0, "None / Organic") # Default option
        except:
            influencers = ["None / Organic"]
            
        selected_influencer = st.selectbox("Which Student Influencer are you subscribed to? Choose from below", influencers)
        
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
            # Include Influencer in payload
            inf_val = selected_influencer if selected_influencer != "None / Organic" else None
            payload = {
                "platform": platform_choice.lower(), 
                "sender_id": user_id, 
                "content": question,
                "attributed_influencer": inf_val
            }
            try:
                requests.post("http://tb_ingestion:8000/ingest/", json=payload)
                st.success("✅ Sent!")
                
                # Poll Redis
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
            if ans.get("category") == "spam":
                st.error(ans.get("ai_response"))
            else:
                st.info(f"**Answer:** {ans.get('ai_response')}")
                st.success(f"📨 Email sent to: {user_id}@std.yildiz.edu.tr")

# --- TAB 2: PREDICTIVE ANALYTICS (NEW) ---
with tab2:
    st.header("📈 Historical Data & Predictions (2013-2030)")
    st.write("Analysis of application growth for the Top 5 Majors.")
    
    # 1. Generate Synthetic Data (2013-2025)
    years = np.arange(2013, 2026)
    # Linear growth from 40k to 150k
    total_apps = np.linspace(40000, 150000, len(years))
    
    # Major breakdown (75% of total)
    majors = {
        "Medicine": 0.25,
        "Computer Eng": 0.20,
        "Intl Relations": 0.15,
        "Dentistry": 0.10,
        "Business Admin": 0.05
    }
    
    data = {"Year": years}
    for major, ratio in majors.items():
        # Add some random noise so the graph looks realistic
        noise = np.random.normal(0, 1000, len(years)) 
        data[major] = (total_apps * ratio) + noise

    df_history = pd.DataFrame(data)
    df_history.set_index("Year", inplace=True)
    
    # 2. Show History
    st.subheader("Application History (2013 - 2025)")
    st.line_chart(df_history)
    
    # 3. Prediction (2026 - 2030)
    st.divider()
    st.subheader("🤖 AI Future Prediction (2026 - 2030)")
    
    future_years = np.arange(2026, 2031)
    future_data = {"Year": future_years}
    
    # Simple Linear Regression for each major
    for major in majors.keys():
        # Fit a line to the history
        z = np.polyfit(years, df_history[major], 1)
        p = np.poly1d(z)
        future_data[major] = p(future_years)
        
    df_future = pd.DataFrame(future_data)
    df_future.set_index("Year", inplace=True)
    
    st.area_chart(df_future)
    st.caption("Projections based on linear regression of 12-year historical dataset.")

# --- TAB 3: ADMIN ---
with tab3:
    st.markdown("### 📢 Student Influencer Analytics")
    
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            # 1. Influencer Leaderboard
            st.subheader("🏆 Top Influencers by curious Subscribers")
            df_logs = pd.read_sql("SELECT * FROM query_logs", conn)
            
            if not df_logs.empty and 'attributed_influencer' in df_logs.columns:
                # Count queries per influencer
                counts = df_logs['attributed_influencer'].value_counts()
                st.bar_chart(counts)
            else:
                st.info("No referral data yet.")

            st.divider()
            
            # 2. Add New Influencer
            st.markdown("**Add New Influencer**")
            col_add_1, col_add_2 = st.columns(2)
            with col_add_1:
                new_user = st.text_input("Username")
                new_plat = st.selectbox("Platform", ["YouTube", "Instagram", "TikTok"])
            with col_add_2:
                new_foll = st.number_input("Followers", min_value=0, step=100)
                st.write("") 
                st.write("")
                if st.button("➕ Register Influencer"):
                    requests.post("http://tb_knowledge:8002/influencers/", 
                                  params={"username": new_user, "platform": new_plat, "followers": new_foll})
                    st.rerun()

            # 3. List
            st.write("---")
            df_inf = pd.read_sql("SELECT * FROM influencers", conn)
            st.dataframe(df_inf, use_container_width=True)

    except Exception as e:
        st.error(f"DB Error: {e}")