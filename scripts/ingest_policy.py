# scripts/ingest_policy.py
"""
Ingest politica_compliance.txt into vectorstore/policy using embeddings.
"""
import sys, os
# Add the workspace root to Python path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

from pathlib import Path
from core.embeddings import embed_text
from core.vectorstore import FaissIndex
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os, pickle

DATA_DIR = Path("data")
POLICY = DATA_DIR / "politica_compliance.txt"
VSTORE_DIR = Path("vectorstore/policy")
VSTORE_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = VSTORE_DIR / "policy.index"
META_PATH = VSTORE_DIR / "policy.meta.pkl"

def ingest_policy():
    text = POLICY.read_text(encoding="utf-8")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = splitter.split_text(text)
    vectors = []
    metas = []
    for i, chunk in enumerate(chunks):
        vec = embed_text(chunk)
        vectors.append(vec)
        metas.append({"source":"politica_compliance.txt","chunk_id":i,"text":chunk})
    dim = len(vectors[0])
    fi = FaissIndex(dim, INDEX_PATH, META_PATH)
    fi.build(vectors, metas)
    print(f"Ingested {len(chunks)} chunks into {INDEX_PATH}")

if __name__ == "__main__":
    ingest_policy()
