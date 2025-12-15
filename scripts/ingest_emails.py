# scripts/ingest_emails.py
"""
Faz o parsing de data/emails.txt para JSONL e indexa corpos de e-mail em vectorstore/emails.
Pressupõe que os e-mails em emails.txt estão separados por linhas começando com '----' ou blocos "De:".
"""
import sys, os
# Adiciona a raiz do workspace ao path do Python
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
    # Divide por padrão: De: (dataset em Português). Vamos criar seções por ocorrências de 'De:'.
    parts = re.split(r"\n-{3,}\n", raw_text)
    emails = []
    fallback_id = 0
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Extrai cabeçalhos: De:, Para:, Data:, Assunto:
        m_from = re.search(r"De:\s*(.*)", part)
        m_to = re.search(r"Para:\s*(.*)", part)
        m_date = re.search(r"Data:\s*(.*)", part)
        m_subject = re.search(r"Assunto:\s*(.*)", part)
        # corpo é tudo após a primeira linha em branco seguindo a linha de Assunto
        # extração simples do corpo:
        body = part
        # remove linhas de cabeçalho
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
    # escreve jsonl
    with PARSED.open("w", encoding="utf-8") as fo:
        for e in emails:
            fo.write(json.dumps(e, ensure_ascii=False) + "\n")
    # cria embeddings por chunk do corpo (divide corpos longos)
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
        print("Nenhum texto de e-mail encontrado para indexar.")
        return
    dim = len(vectors[0])
    fi = FaissIndex(dim, INDEX_PATH, META_PATH)
    fi.build(vectors, metas)
    print(f"Ingeridos {len(vectors)} chunks de e-mail em {INDEX_PATH}, JSONL parseado em {PARSED}")

if __name__ == "__main__":
    ingest_emails()
