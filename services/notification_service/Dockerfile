FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/notification_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/notification_service/app /app/app
CMD ["python", "app/main.py"]