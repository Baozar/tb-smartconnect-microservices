from fastapi import FastAPI, HTTPException
from common.app.schemas import StudentQuery
import pika
import json
import os

app = FastAPI(title="TB SmartConnect - Ingestion Service")

# CONFIG
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = "student_queries"

@app.post("/ingest/")
def ingest_query(query: StudentQuery):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        
        # KEY FIX: verify we are dumping the 'attributed_influencer' field
        message_body = json.dumps(query.model_dump(mode='json'))
        
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
        
        connection.close()
        return {"status": "Queued", "data": query}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "Ingestion Service Running"}