from fastapi import FastAPI, HTTPException
from common.app.schemas import StudentQuery, Platform, QueryStatus
from datetime import datetime
import pika
import json
import os

app = FastAPI(title="TB SmartConnect - Ingestion Service")

# CONFIG (Load from Env, with defaults just in case)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = "student_queries"

def get_rabbitmq_channel():
    """Establishes connection to RabbitMQ with AUTHENTICATION"""
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        return channel, connection
    except Exception as e:
        print(f"❌ RabbitMQ Connection Failed: {e}")
        return None, None

@app.get("/")
def health_check():
    return {"status": "Ingestion Service is ALIVE"}

@app.post("/ingest/")
def ingest_query(query: StudentQuery):
    """
    Receives a query and pushes to Queue.
    """
    query.status = QueryStatus.RECEIVED
    
    channel, connection = get_rabbitmq_channel()
    if not channel:
        raise HTTPException(status_code=500, detail="Messaging System Unavailable")
    
    message_body = query.model_dump_json()
    
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=message_body,
        properties=pika.BasicProperties(
            delivery_mode=2,
        )
    )
    
    connection.close()
    
    return {"status": "Queued", "message_id": query.sender_id, "timestamp": query.timestamp}