# core/embeddings.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL","text-embedding-004")

def embed_text(text:str):
    """
    Retorna embedding vetorial usando Gemini.
    """
    resp = genai.embed_content(
        model=EMBED_MODEL,
        content=text
    )
    return resp["embedding"]
