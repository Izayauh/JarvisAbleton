import os
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
for m in genai.list_models():
    if "generate" in str(m.supported_generation_methods):
        print(f"{m.name} -> {m.supported_generation_methods}")
