# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# 1. Install Dependencies first (Caching layer)
COPY services/ingestion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the Shared Library (Crucial Step)
COPY services/common /app/common
# We set PYTHONPATH so Python knows where to find 'common'
ENV PYTHONPATH="${PYTHONPATH}:/app"

# 3. Copy the Application Code
COPY services/ingestion_service/app /app/app

# 4. Command to run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]