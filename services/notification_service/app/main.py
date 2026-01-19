import pika
import time
import os
import json

# CONFIG
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = "outgoing_emails"

def send_email_simulation(recipient, subject, body):
    """Simulates sending an email (SMTP)"""
    print(f"📧 CONNECTING to SMTP Server...")
    time.sleep(1) # Simulate network delay
    print(f"📨 SENDING Email to [{recipient}]")
    print(f"   Subject: {subject}")
    print(f"   Body: {body[:50]}...") # Print first 50 chars
    print(f"✅ Email SENT successfully.")

def callback(ch, method, properties, body):
    print(f"📥 Notification Service received order: {body}")
    data = json.loads(body)
    
    # Simulate the work
    send_email_simulation(
        recipient=data.get("email", "student@example.com"),
        subject="Update on your Turkiye Burslari Application",
        body=data.get("message", "Your query has been processed.")
    )
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    print("🚀 Notification Service Starting...")
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    
    while True:
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            print("👂 Listening for email jobs...")
            channel.start_consuming()
        except Exception as e:
            print(f"❌ Connection failed, retrying in 5s: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_consuming()