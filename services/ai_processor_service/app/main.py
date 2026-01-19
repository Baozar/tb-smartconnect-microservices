import pika
import json
import os
import time
import google.generativeai as genai
from common.app.schemas import StudentQuery, QueryStatus

# CONFIG
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = "student_queries"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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
        # Parse the JSON string from Gemini (handling potential markdown formatting)
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
    
    # 3. Update the Query Object
    query.category = ai_result.get("category")
    query.sentiment_score = ai_result.get("sentiment_score")
    query.ai_response = ai_result.get("ai_response")
    query.status = QueryStatus.ANSWERED
    
    print(f"✅ AI Response: {query.ai_response}")
    print(f"📊 Fit Score: {query.sentiment_score}")
    
    # (Future Step: Push to 'processed_queries' queue or Database)
    
    # 4. Acknowledge message so RabbitMQ deletes it from queue
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    
    # Wait for RabbitMQ to be ready
    for _ in range(5):
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            print("🚀 AI Processor is waiting for messages...")
            channel.start_consuming()
            break
        except pika.exceptions.AMQPConnectionError:
            print("⏳ RabbitMQ not ready, retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    start_consuming()