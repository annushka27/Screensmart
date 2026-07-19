from google import genai
from dotenv import load_dotenv
import os
import json
from prompt import get_analysis_prompt

load_dotenv()

print("API KEY =", os.getenv("GEMINI_API_KEY"))

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def analyze_resume(resume_text, jd_text):
    prompt = get_analysis_prompt(resume_text, jd_text)
    
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    text = response.text.strip()

    # remove markdown if Gemini returns ```json
    text = text.replace("```json", "")
    text = text.replace("```", "")

    return json.loads(text)