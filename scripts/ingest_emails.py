# scripts/ingest_emails.py
"""
Parse data/emails.txt into JSONL and index email bodies into vectorstore/emails.
Assumes emails in emails.txt are separated by lines starting with '----' or "De:" blocks.
"""
import sys, os
# Add the workspace root to Python path
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_root)

from pathlib import Path
import re, json
from core.embeddings import embed_text
from core.vectorstore import FaissIndex
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path("data")
RAW = DATA_DIR / "emails.txt"  # uploaded as emails.txt. :contentReference[oaicite:2]{index=2}
PARSED = DATA_DIR / "emails_parsed.jsonl"
VSTORE_DIR = Path("vectorstore/emails")
VSTORE_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = VSTORE_DIR / "emails.index"
META_PATH = VSTORE_DIR / "emails.meta.pkl"

def parse_raw_emails(raw_text):
    # Split by pattern: De: (Portuguese dataset). We'll create sections by 'De:' occurrences.
    parts = re.split(r"\n-{3,}\n", raw_text)
    emails = []
    fallback_id = 0
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Extract headers: De:, Para:, Data:, Assunto:
        m_from = re.search(r"De:\s*(.*)", part)
        m_to = re.search(r"Para:\s*(.*)", part)
        m_date = re.search(r"Data:\s*(.*)", part)
        m_subject = re.search(r"Assunto:\s*(.*)", part)
        # body is everything after the first blank line following Subject line
        # naive body extraction:
        body = part
        # remove header lines
        body = re.sub(r"De:.*\n", "", body)
        body = re.sub(r"Para:.*\n", "", body)
        body = re.sub(r"Data:.*\n", "", body)
        body = re.sub(r"Assunto:.*\n", "", body)
        body = body.strip()
        email = {
            "id": fallback_id,
            "from": m_from.group(1).strip() if m_from else None,
            "to": m_to.group(1).strip() if m_to else None,
            "date": m_date.group(1).strip() if m_date else None,
            "subject": m_subject.group(1).strip() if m_subject else None,
            "body": body
        }
        emails.append(email)
        fallback_id += 1
    return emails

def ingest_emails():
    raw = RAW.read_text(encoding="utf-8")
    emails = parse_raw_emails(raw)
    # write jsonl
    with PARSED.open("w", encoding="utf-8") as fo:
        for e in emails:
            fo.write(json.dumps(e, ensure_ascii=False) + "\n")
    # create embeddings per body chunk (split long bodies)
    vectors = []
    metas = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    for e in emails:
        chunks = splitter.split_text(e["body"] or "")
        for i, chunk in enumerate(chunks):
            vec = embed_text(chunk)
            vectors.append(vec)
            metas.append({"source":"emails.txt","email_id":e["id"],"chunk_id":i,"text":chunk,"subject":e.get("subject"),"from":e.get("from"),"date":e.get("date")})
    if len(vectors)==0:
        print("No email text found to index.")
        return
    dim = len(vectors[0])
    fi = FaissIndex(dim, INDEX_PATH, META_PATH)
    fi.build(vectors, metas)
    print(f"Ingested {len(vectors)} email chunks into {INDEX_PATH}, parsed JSONL at {PARSED}")

if __name__ == "__main__":
    ingest_emails()
