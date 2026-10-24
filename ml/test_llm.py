import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

response = client.models.generate_content(
    model=model, contents="Reply with the single word: ready"
)
print(response.text)