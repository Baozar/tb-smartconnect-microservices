import pika
import json
import os
import time
import redis
import google.generativeai as genai
from common.app.schemas import StudentQuery, QueryStatus

# CONFIG
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = "student_queries"
NOTIFICATION_QUEUE = "outgoing_emails"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# REDIS CONNECTION (The Short-term Memory)
# We use the hostname 'redis' because that is the service name in docker-compose
redis_client = redis.Redis(host='redis', port=6379, db=0)

# GEMINI SETUP
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def analyze_query(content: str):
    """Uses LLM to analyze the student query."""
    prompt = f"""
    You are an admissions assistant for Turkiye Burslari.
    Analyze this student query: "{content}"
    
    Return ONLY a JSON object with:
    1. "category": (faq, application_issue, high_value, spam)
    2. "sentiment_score": (0.0 to 1.0, where 1.0 is highly polite and socially adaptable)
    3. "ai_response": (A polite, accurate answer to the question)
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {"category": "error", "sentiment_score": 0.5, "ai_response": "System busy."}

def callback(ch, method, properties, body):
    print(f"📥 Received message: {body}")
    
    # 1. Parse Message
    query_data = json.loads(body)
    query = StudentQuery(**query_data)
    
    # 2. Process with AI
    print(f"🧠 Thinking about query from {query.sender_id}...")
    ai_result = analyze_query(query.content)
    
    # 3. SAVE TO REDIS (New Step)
    # We save the answer using the sender_id as the key so the dashboard can find it.
    redis_key = f"query:{query.sender_id}"
    redis_client.set(redis_key, json.dumps(ai_result), ex=3600) # Expire in 1 hour
    print(f"💾 Saved answer to Redis: {redis_key}")
    
    # 4. Forward to Notification Service
    notification_payload = {
        "email": f"{query.sender_id}@std.yildiz.edu.tr",
        "message": ai_result.get("ai_response")
    }
    ch.basic_publish(
        exchange='',
        routing_key=NOTIFICATION_QUEUE,
        body=json.dumps(notification_payload),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(f"📨 Forwarded to Notification Service")
    
    # 5. Acknowledge
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    
    # Retry loop to wait for RabbitMQ to start
    for _ in range(5):
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            # Declare BOTH queues to be safe
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True)
            
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            print("🚀 AI Processor (v2 - Redis Enabled) is waiting for messages...")
            channel.start_consuming()
            break
        except Exception as e:
            print("⏳ RabbitMQ not ready, retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    start_consuming()