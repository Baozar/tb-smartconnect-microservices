FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/ai_processor_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/common /app/common
ENV PYTHONPATH="${PYTHONPATH}:/app"
COPY services/ai_processor_service/app /app/app
# Notice we run main.py directly, not uvicorn, because this is a background worker, not a web server.
CMD ["python", "app/main.py"]