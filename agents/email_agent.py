# agents/email_agent.py
"""
Email agent: search emails, return suspicious messages and detect conspiracy.
Uses vectorstore/emails.
"""
from pathlib import Path
from core.embeddings import embed_text
from core.vectorstore import FaissIndex
from core.llm import chat_completion
import json

VSTORE_INDEX = Path("vectorstore/emails/emails.index")
VSTORE_META = Path("vectorstore/emails/emails.meta.pkl")
PARSED_JSONL = Path("data/emails_parsed.jsonl")

SUSPICIOUS_KEYWORDS = [
    "conta alternativa","não registrar","apagar recibo","mascarar","mascarar custos",
    "destruir as evidências","não conte","conta não corporativa","pagar em espécie",
    "usar o cartão corporativo","dividir a compra","smurf", "operacao", "operação",
    "mascarar", "mascaramento", "fazer desaparecer","walkie-talkies","câmeras","algemas","kit de ilusionismo"
]

class EmailAgent:
    def __init__(self, k=6):
        if not VSTORE_INDEX.exists():
            raise RuntimeError("Emails vectorstore not found. Run scripts/ingest_emails.py first.")
        # load index
        import pickle
        with open(VSTORE_META, "rb") as f:
            metas = pickle.load(f)
        dim = 1536
        self.store = FaissIndex(dim, VSTORE_INDEX, VSTORE_META)
        self.k = k
        # pre-load parsed file
        self.parsed = []
        if PARSED_JSONL.exists():
            with PARSED_JSONL.open("r", encoding="utf-8") as fo:
                for l in fo:
                    self.parsed.append(json.loads(l))

    def search_keyword(self, keywords=None):
        keywords = keywords or SUSPICIOUS_KEYWORDS
        matches = []
        for e in self.parsed:
            body = (e.get("body") or "").lower()
            hits = [kw for kw in keywords if kw.lower() in body]
            if hits:
                matches.append({"email":e,"hits":hits})
        return matches

    def semantic_search(self, query, top_k=None):
        top_k = top_k or self.k
        qvec = embed_text(query)
        hits = self.store.query(qvec, k=top_k)
        # group hits by email_id
        grouped = {}
        for h in hits:
            meta = h["meta"]
            eid = meta["email_id"]
            grouped.setdefault(eid, {"score":[], "chunks":[]})
            grouped[eid]["score"].append(h["score"])
            grouped[eid]["chunks"].append(meta)
        # format results
        results = []
        for eid, val in grouped.items():
            # find parsed email entry
            email = next((x for x in self.parsed if x["id"]==eid), None)
            results.append({"email":email, "chunks":val["chunks"], "avg_score": sum(val["score"])/len(val["score"])})
        results.sort(key=lambda x: x["avg_score"])
        return results

    def detect_conspiracy(self):
        """
        Returns True if conspiracy indicators present regarding Toby (explicit mentions / operation).
        """
        # naive: check for keywords and also semantic search for "operação fênix" / "Toby"
        kw_matches = self.search_keyword()
        sem = self.semantic_search("Toby Flenderson conspiração operação fênix", top_k=10)
        # consider conspiracy present if kw_matches non-empty OR sem results with chunks mentioning operation/toby
        evidence = []
        for m in kw_matches:
            evidence.append({"type":"keyword","email":m["email"],"hits":m["hits"]})
        for s in sem:
            # look at chunks
            for c in s["chunks"]:
                txt = c.get("text","").lower()
                if "toby" in txt or "fênix" in txt or "operação" in txt or "destroy" in txt or "destruir" in txt:
                    evidence.append({"type":"semantic","email":s["email"],"chunk":c})
        verdict = "Sim" if len(evidence)>0 else "Não"
        return {"verdict":verdict, "evidence":evidence}

if __name__ == "__main__":
    agent = EmailAgent()
    out = agent.detect_conspiracy()
    import pprint
    pprint.pprint(out)