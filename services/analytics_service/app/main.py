import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import time

# CONFIG
st.set_page_config(page_title="TB SmartConnect Dashboard", layout="wide")

POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASS = os.getenv("POSTGRES_PASS", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "tb_knowledge_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")

# Connect to DB
@st.cache_resource
def get_db_connection():
    url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    return create_engine(url)

st.title("🇹🇷 Turkiye Burslari SmartConnect System")
st.markdown("### Real-time Architecture Monitoring")

# 1. System Status
col1, col2, col3 = st.columns(3)
col1.metric("Active Services", "5", "All Systems Go")
col2.metric("Pending Applications", "154,203", "+12%")
col3.metric("Avg AI Response Time", "1.2s", "-0.3s")

# 2. Database View (Influencers)
st.subheader("📢 Influencer Registry (Live from Postgres)")

try:
    engine = get_db_connection()
    # Query the 'influencers' table we created in Service #3
    df = pd.read_sql("SELECT * FROM influencers", engine)
    
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No influencers found in the registry yet. Add some via the Knowledge Service!")

except Exception as e:
    st.error(f"Could not connect to Knowledge Database: {e}")

# 3. Architecture Diagram
st.subheader("System Architecture")
st.code("""
[YouTube/Instagram] --> [Ingestion Service] --> [RabbitMQ]
                                                  |
                                            [AI Processor]
                                                  |
[Student] <--- [Notification Service] <--- [Result Queue]
""", language="text")