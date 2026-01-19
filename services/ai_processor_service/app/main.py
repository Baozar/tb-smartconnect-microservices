import pika
import json
import os
import time
import redis
import requests # <--- NEW IMPORT
import google.generativeai as genai
from common.app.schemas import StudentQuery, QueryStatus

# CONFIG
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = "student_queries"
NOTIFICATION_QUEUE = "outgoing_emails"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# URL of the Knowledge Service (Internal Docker Network)
KNOWLEDGE_SERVICE_URL = "http://tb_knowledge:8002/history/"

MAX_QUESTIONS = 5
RATE_LIMIT_WINDOW = 86400 

redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-lite-latest')

def check_rate_limit(user_id):
    key = f"rate_limit:{user_id}"
    current_count = redis_client.incr(key)
    if current_count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW)
    return current_count <= MAX_QUESTIONS

def analyze_query(content: str):
    prompt = f"""
    You are an admissions assistant for Turkiye Burslari.
    Analyze this student query: "{content}"
    Return ONLY a JSON object with:
    1. "category": (choose strictly from: "eligibility", "dates", "documents", "technical_issue", "spam")
    2. "sentiment_score": (0.0 to 1.0)
    3. "ai_response": (A polite, accurate answer)
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
    query_data = json.loads(body)
    query = StudentQuery(**query_data)
    
    # 1. RATE LIMIT
    if not check_rate_limit(query.sender_id):
        print(f"⛔ Rate Limit Exceeded for {query.sender_id}")
        ai_result = {"category": "spam", "sentiment_score": 0.0, "ai_response": "Limit Reached."}
    else:
        # 2. AI PROCESSING
        print(f"🧠 Thinking...")
        ai_result = analyze_query(query.content)

    # 3. SAVE TO REDIS (For UI)
    redis_key = f"query:{query.sender_id}"
    redis_client.set(redis_key, json.dumps(ai_result), ex=3600)
    
    # 4. LOG TO POSTGRES (For Analytics) <--- NEW PART
    # 4. LOG TO POSTGRES (For Analytics)
    try:
        log_payload = {
            "platform": query.platform,
            "sender_id": query.sender_id,
            "question": query.content,
            "category": ai_result.get("category", "unknown"),
            "sentiment_score": ai_result.get("sentiment_score", 0.0),
            # Extract influencer from the query object (we will add this to the schema next)
            "attributed_influencer": getattr(query, "attributed_influencer", None) 
        }
        requests.post(KNOWLEDGE_SERVICE_URL, json=log_payload)
        print("💾 History logged to Knowledge Service")
    except Exception as e:
        print(f"⚠️ Failed to log history: {e}")


    # 5. NOTIFICATION
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
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    for _ in range(5):
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            print("🚀 AI Processor (v4 - Analytics Enabled) is Running...")
            channel.start_consuming()
            break
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    start_consuming()