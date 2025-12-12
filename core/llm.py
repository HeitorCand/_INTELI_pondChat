# core/llm.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_CHAT_MODEL","gemini-1.5-flash")

def chat_completion(messages, temperature=0.0, max_tokens=800):
    """
    messages: lista de dicts {role, content}
    """
    history = []
    for m in messages:
        history.append(m["content"])
    prompt = "\n".join(history)

    model = genai.GenerativeModel(MODEL_NAME)
    resp = model.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens
        }
    )
    return resp.text
