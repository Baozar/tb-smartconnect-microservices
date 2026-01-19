import google.generativeai as genai
import os

# Configure with the key from the environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY is missing.")
    exit()

genai.configure(api_key=api_key)

print(f"🔍 Checking available models for your API key...")
try:
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f" - Found: {m.name}")
            available_models.append(m.name)
    
    if not available_models:
        print("⚠️ No models found with 'generateContent' capability.")
except Exception as e:
    print(f"❌ Connection Error: {e}")