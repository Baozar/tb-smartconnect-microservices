FROM python:3.11-slim
WORKDIR /app
COPY services/analytics_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/analytics_service/app /app/app
# Streamlit runs on port 8501
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]