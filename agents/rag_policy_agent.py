# agents/rag_policy_agent.py
"""
RAG agent to answer questions about politica_compliance.txt using vectorstore/policy
"""
from pathlib import Path
from core.embeddings import embed_text
from core.vectorstore import FaissIndex
from core.llm import chat_completion
import json, os

VSTORE_INDEX = Path("vectorstore/policy/policy.index")
VSTORE_META = Path("vectorstore/policy/policy.meta.pkl")

class RAGPolicyAgent:
    def __init__(self, k=4):
        if not VSTORE_INDEX.exists():
            raise RuntimeError("Policy vectorstore not found. Run scripts/ingest_policy.py first.")
        # infer dim by reading index file? We'll load meta to get one chunk and embed to get dim
        import pickle
        with open(VSTORE_META, "rb") as f:
            metas = pickle.load(f)
        self.dim = 1536 if len(metas)==0 else 1536  # placeholder (embedding dim dynamic in production)
        self.store = FaissIndex(self.dim, VSTORE_INDEX, VSTORE_META)
        self.k = k

    def retrieve(self, question):
        qvec = embed_text(question)
        hits = self.store.query(qvec, k=self.k)
        return hits

    def answer(self, question):
        hits = self.retrieve(question)
        if not hits:
            return "Não há evidência indexada da política."
        evidence = "\n\n---\n".join([f"Chunk {h['meta']['chunk_id']} (score={h['score']}):\n{h['meta']['text']}" for h in hits])
        prompt = [
            {"role":"system","content":"Você é um auditor especialista em política de compliance da Dunder Mifflin. Responda em Português."},
            {"role":"user","content":f"""Pergunta: {question}

Use apenas as evidências abaixo para responder. Se não puder responder com certeza, diga 'Não consta na política'.

EVIDÊNCIAS:
{evidence}

Formate a resposta com: RESPOSTA:, RAZÃO:, EVIDÊNCIAS (lista de chunk_id com trechos)."""}
        ]
        resp = chat_completion(prompt, temperature=0.1)
        return resp

if __name__ == "__main__":
    import os
    agent = RAGPolicyAgent()
    q = input("Pergunta sobre a política: ")
    print(agent.answer(q))
